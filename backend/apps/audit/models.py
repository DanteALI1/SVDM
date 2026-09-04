from django.conf import settings
from django.db import models
from apps.core.models import TimeStampedModel


class AuditLog(TimeStampedModel):
    tenant = models.ForeignKey(
        "tenants.Tenant", null=True, blank=True, on_delete=models.CASCADE, related_name="audit_logs"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    action = models.CharField(max_length=64)
    method = models.CharField(max_length=16, blank=True, default="")
    path = models.CharField(max_length=512, blank=True, default="")
    status_code = models.PositiveIntegerField(null=True, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "created_at"]),
        ]
