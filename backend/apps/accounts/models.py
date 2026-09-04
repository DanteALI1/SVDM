from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    is_platform_admin = models.BooleanField(default=False)
    preferred_language = models.CharField(max_length=5, default="ru", choices=[("ru", "RU"), ("en", "EN")])
    preferred_theme = models.CharField(
        max_length=10, default="light", choices=[("light", "Light"), ("dark", "Dark")]
    )
    totp_secret = models.CharField(max_length=64, blank=True, default="")
    totp_confirmed = models.BooleanField(default=False)
    failed_login_count = models.PositiveIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
    must_enroll_2fa = models.BooleanField(default=False)

    def is_locked(self):
        return self.locked_until and self.locked_until > timezone.now()


class PasswordPolicy(models.Model):
    tenant = models.OneToOneField(
        "tenants.Tenant", on_delete=models.CASCADE, related_name="password_policy", null=True, blank=True
    )
    min_length = models.PositiveIntegerField(default=12)
    require_upper = models.BooleanField(default=True)
    require_lower = models.BooleanField(default=True)
    require_digit = models.BooleanField(default=True)
    require_special = models.BooleanField(default=True)
    max_failed_attempts = models.PositiveIntegerField(default=5)
    lockout_minutes = models.PositiveIntegerField(default=30)
