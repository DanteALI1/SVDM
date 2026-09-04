from django.db import models
from apps.core.models import TenantScopedModel, TimeStampedModel


class Vulnerability(TenantScopedModel):
    """Unified vulnerability card matching CVE ↔ BDU ↔ KEV."""

    cve_id = models.CharField(max_length=32, blank=True, default="", db_index=True)
    bdu_id = models.CharField(max_length=64, blank=True, default="", db_index=True)
    is_kev = models.BooleanField(default=False, db_index=True)
    kev_date_added = models.DateField(null=True, blank=True)
    kev_due_date = models.DateField(null=True, blank=True)
    kev_ransomware = models.CharField(max_length=64, blank=True, default="")

    title = models.CharField(max_length=512, blank=True, default="")
    description_ru = models.TextField(blank=True, default="")
    description_en = models.TextField(blank=True, default="")

    # CVSS versions — store all; max_cvss is the priority score
    cvss_v2_score = models.FloatField(null=True, blank=True)
    cvss_v2_vector = models.CharField(max_length=128, blank=True, default="")
    cvss_v3_score = models.FloatField(null=True, blank=True)
    cvss_v3_vector = models.CharField(max_length=128, blank=True, default="")
    cvss_v31_score = models.FloatField(null=True, blank=True)
    cvss_v31_vector = models.CharField(max_length=128, blank=True, default="")
    cvss_v4_score = models.FloatField(null=True, blank=True)
    cvss_v4_vector = models.CharField(max_length=128, blank=True, default="")
    max_cvss = models.FloatField(null=True, blank=True, db_index=True)

    severity = models.CharField(max_length=32, blank=True, default="", db_index=True)
    published_at = models.DateTimeField(null=True, blank=True)
    modified_at = models.DateTimeField(null=True, blank=True)
    cwe_ids = models.JSONField(default=list, blank=True)
    cpe_list = models.JSONField(default=list, blank=True)
    references = models.JSONField(default=list, blank=True)
    nvd_raw = models.JSONField(default=dict, blank=True)
    bdu_raw = models.JSONField(default=dict, blank=True)
    sources = models.JSONField(default=list, blank=True)  # ["nvd","bdu","kev"]
    status = models.CharField(max_length=32, default="active")

    class Meta:
        indexes = [
            models.Index(fields=["tenant", "max_cvss"]),
            models.Index(fields=["tenant", "is_kev"]),
            models.Index(fields=["tenant", "cve_id"]),
            models.Index(fields=["tenant", "bdu_id"]),
        ]
        ordering = ["-max_cvss", "-published_at"]

    def recompute_max_cvss(self):
        scores = [
            s
            for s in (
                self.cvss_v2_score,
                self.cvss_v3_score,
                self.cvss_v31_score,
                self.cvss_v4_score,
            )
            if s is not None
        ]
        self.max_cvss = max(scores) if scores else None
        if self.max_cvss is not None:
            if self.max_cvss >= 9.0:
                self.severity = "Critical"
            elif self.max_cvss >= 7.0:
                self.severity = "High"
            elif self.max_cvss >= 4.0:
                self.severity = "Medium"
            elif self.max_cvss > 0:
                self.severity = "Low"
            else:
                self.severity = "Info"
        return self.max_cvss

    def save(self, *args, **kwargs):
        self.recompute_max_cvss()
        super().save(*args, **kwargs)


class SyncJournal(TenantScopedModel):
    class Source(models.TextChoices):
        NVD = "nvd", "NVD"
        KEV = "kev", "CISA KEV"
        BDU = "bdu", "BDU FSTEC"

    source = models.CharField(max_length=16, choices=Source.choices)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    records_processed = models.PositiveIntegerField(default=0)
    records_created = models.PositiveIntegerField(default=0)
    records_updated = models.PositiveIntegerField(default=0)
    success = models.BooleanField(default=False)
    error_message = models.TextField(blank=True, default="")
    triggered_by = models.CharField(max_length=64, blank=True, default="manual")
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-started_at"]


class SyncSchedule(TenantScopedModel):
    source = models.CharField(max_length=16, choices=SyncJournal.Source.choices)
    enabled = models.BooleanField(default=True)
    interval_hours = models.PositiveIntegerField(null=True, blank=True, default=24)
    days_of_week = models.JSONField(default=list, blank=True)  # 0-6
    run_dates = models.JSONField(default=list, blank=True)
    last_run_at = models.DateTimeField(null=True, blank=True)
    next_run_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("tenant", "source")
