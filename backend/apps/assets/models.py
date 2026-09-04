from django.conf import settings
from django.db import models
from apps.core.models import TenantScopedModel, TimeStampedModel


class AssetType(TenantScopedModel):
    code = models.SlugField()
    name = models.CharField(max_length=128)
    is_system = models.BooleanField(default=False)

    class Meta:
        unique_together = ("tenant", "code")


DEFAULT_ASSET_TYPES = [
    ("server", "Server"),
    ("application", "Application"),
    ("database", "Database"),
    ("network", "Network"),
    ("container", "Container"),
    ("saas", "SaaS"),
    ("endpoint", "Endpoint"),
    ("storage", "Storage"),
    ("cloud", "Cloud"),
    ("ot_ics", "OT/ICS"),
]


class BusinessSystem(TenantScopedModel):
    name = models.CharField(max_length=255)
    code = models.SlugField(blank=True, default="")
    description = models.TextField(blank=True, default="")

    class Meta:
        unique_together = ("tenant", "name")


class Asset(TenantScopedModel):
    class Status(models.TextChoices):
        IN_SERVICE = "in_service", "In service"
        DECOMMISSIONED = "decommissioned", "Decommissioned"
        PLANNED = "planned", "Planned"

    class Environment(models.TextChoices):
        PROD = "prod", "Prod"
        STAGE = "stage", "Stage"
        DEV = "dev", "Dev"
        TEST = "test", "Test"

    class Criticality(models.TextChoices):
        CRITICAL = "Critical", "Critical"
        HIGH = "High", "High"
        MEDIUM = "Medium", "Medium"
        LOW = "Low", "Low"
        INFO = "Info", "Info"

    name = models.CharField(max_length=255)
    asset_type = models.ForeignKey(AssetType, on_delete=models.PROTECT, related_name="assets")
    status = models.CharField(max_length=32, choices=Status.choices)
    ip_address = models.GenericIPAddressField()
    fqdn = models.CharField(max_length=255)
    os_platform = models.CharField(max_length=255)
    environment = models.CharField(max_length=16, choices=Environment.choices)
    criticality = models.CharField(max_length=16, choices=Criticality.choices)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="owned_assets"
    )
    business_system = models.ForeignKey(
        BusinessSystem, on_delete=models.PROTECT, related_name="assets"
    )
    description = models.TextField(blank=True, default="")
    tags = models.JSONField(default=list, blank=True)
    inventory_number = models.CharField(max_length=128)
    location = models.CharField(max_length=255)
    contour = models.ForeignKey("tenants.Contour", on_delete=models.PROTECT, related_name="assets")
    security_officer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="secured_assets"
    )
    commissioned_at = models.DateField()

    class Meta:
        ordering = ["business_system__name", "name"]
        indexes = [
            models.Index(fields=["tenant", "environment"]),
            models.Index(fields=["tenant", "status"]),
        ]
