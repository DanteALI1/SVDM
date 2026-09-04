from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


class Tenant(TimeStampedModel):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    is_active = models.BooleanField(default=True)

    # Branding
    logo = models.ImageField(upload_to="branding/logos/", blank=True, null=True)
    favicon = models.ImageField(upload_to="branding/favicons/", blank=True, null=True)
    primary_color = models.CharField(max_length=7, default="#1E4FD6")
    secondary_color = models.CharField(max_length=7, default="#FFFFFF")
    accent_color = models.CharField(max_length=7, default="#0B2A6F")

    # Contour / feature flags (tenant-level)
    feature_sync_nvd = models.BooleanField(default=True)
    feature_sync_kev = models.BooleanField(default=True)
    feature_sync_bdu = models.BooleanField(default=True)
    feature_outbound_mail = models.BooleanField(default=False)
    feature_sso = models.BooleanField(default=False)
    feature_product_updates = models.BooleanField(default=True)
    feature_2fa_totp = models.BooleanField(default=False)
    offline_mode = models.BooleanField(default=False)

    # SMTP
    smtp_host = models.CharField(max_length=255, blank=True, default="")
    smtp_port = models.PositiveIntegerField(default=587)
    smtp_user = models.CharField(max_length=255, blank=True, default="")
    smtp_password = models.CharField(max_length=255, blank=True, default="")
    smtp_use_tls = models.BooleanField(default=True)
    smtp_from = models.EmailField(blank=True, default="")

    # Source API keys
    nvd_api_key = models.CharField(max_length=255, blank=True, default="")

    # Session / audit overrides
    session_idle_minutes = models.PositiveIntegerField(default=60)
    audit_retention_days = models.PositiveIntegerField(default=180)

    # SSO placeholders
    sso_provider = models.CharField(
        max_length=32,
        blank=True,
        default="",
        choices=[
            ("", "None"),
            ("oidc", "OIDC"),
            ("saml", "SAML"),
            ("ldap", "LDAP"),
            ("ad", "Active Directory"),
        ],
    )
    sso_config = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return self.name

    @property
    def smtp_configured(self):
        return bool(self.feature_outbound_mail and self.smtp_host and self.smtp_from)

    def effective_flag(self, flag_name: str) -> bool:
        """Apply platform kill-switch on top of tenant flag."""
        from apps.platform_admin.models import PlatformSettings

        platform = PlatformSettings.get_solo()
        kill = getattr(platform, f"kill_{flag_name}", False)
        tenant_val = getattr(self, f"feature_{flag_name}", False)
        if kill:
            return False
        return bool(tenant_val)


class Membership(TimeStampedModel):
    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        ANALYST = "analyst", "Security Analyst"
        ASSET_OWNER = "asset_owner", "Asset Owner"
        READER = "reader", "Reader"
        WIKI_EDITOR = "wiki_editor", "Wiki Editor"

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memberships")
    role = models.CharField(max_length=32, choices=Role.choices)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("tenant", "user")

    def effective_role(self):
        """Wiki editor outside wiki acts as analyst."""
        return self.role


class WorkCalendar(TimeStampedModel):
    tenant = models.OneToOneField(Tenant, on_delete=models.CASCADE, related_name="work_calendar")
    workday_start = models.TimeField(default="09:00")
    workday_end = models.TimeField(default="18:00")
    workdays = models.JSONField(default=list)  # [0..6] Mon=0
    exceptions = models.JSONField(default=list)  # [{date, is_working, note}]


class Contour(TimeStampedModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="contours")
    name = models.CharField(max_length=128)
    code = models.SlugField()
    is_system = models.BooleanField(default=False)

    class Meta:
        unique_together = ("tenant", "code")


DEFAULT_CONTOURS = [
    ("dsp", "ДСП"),
    ("internet", "Интернет"),
    ("intranet", "Intranet"),
    ("dmz", "DMZ"),
]
