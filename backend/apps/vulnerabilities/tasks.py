from celery import shared_task
from apps.tenants.models import Tenant
from .models import SyncSchedule
from .services import sync_nvd, sync_kev
from django.utils import timezone


@shared_task
def run_scheduled_syncs():
    now = timezone.now()
    for schedule in SyncSchedule.objects.filter(enabled=True).select_related("tenant"):
        tenant = schedule.tenant
        if schedule.source == "nvd" and tenant.effective_flag("sync_nvd") and not tenant.offline_mode:
            sync_nvd(tenant, triggered_by="schedule")
        elif schedule.source == "kev" and tenant.effective_flag("sync_kev") and not tenant.offline_mode:
            sync_kev(tenant, triggered_by="schedule")
        schedule.last_run_at = now
        schedule.save(update_fields=["last_run_at"])
