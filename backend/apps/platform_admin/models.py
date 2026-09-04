from django.db import models
from apps.core.models import TimeStampedModel


class PlatformSettings(TimeStampedModel):
    """Singleton platform settings with global kill-switches."""

    kill_sync_nvd = models.BooleanField(default=False)
    kill_sync_kev = models.BooleanField(default=False)
    kill_sync_bdu = models.BooleanField(default=False)
    kill_outbound_mail = models.BooleanField(default=False)
    kill_sso = models.BooleanField(default=False)
    kill_product_updates = models.BooleanField(default=False)
    kill_2fa_totp = models.BooleanField(default=False)
    global_nvd_api_key = models.CharField(max_length=255, blank=True, default="")
    setup_completed = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = "Platform settings"

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
