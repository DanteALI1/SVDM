from celery import shared_task
from celery.schedules import crontab
from apps.tenants.models import Tenant
from .models import SyncSchedule
from .services import sync_nvd, sync_kev
from django.utils import timezone
from datetime import timedelta


def _schedule_due(schedule, now) -> bool:
    if not schedule.enabled:
        return False
    # days_of_week filter (0=Mon)
    if schedule.days_of_week and now.weekday() not in schedule.days_of_week:
        return False
    # explicit run_dates
    if schedule.run_dates:
        today = now.date().isoformat()
        if today not in schedule.run_dates:
            return False
    interval = schedule.interval_hours or 24
    if schedule.last_run_at and (now - schedule.last_run_at) < timedelta(hours=interval):
        return False
    if schedule.next_run_at and now < schedule.next_run_at:
        return False
    return True


@shared_task
def run_scheduled_syncs():
    now = timezone.now()
    for schedule in SyncSchedule.objects.filter(enabled=True).select_related("tenant"):
        if not _schedule_due(schedule, now):
            continue
        tenant = schedule.tenant
        if schedule.source == "nvd" and tenant.effective_flag("sync_nvd") and not tenant.offline_mode:
            sync_nvd(tenant, triggered_by="schedule")
        elif schedule.source == "kev" and tenant.effective_flag("sync_kev") and not tenant.offline_mode:
            sync_kev(tenant, triggered_by="schedule")
        schedule.last_run_at = now
        schedule.next_run_at = now + timedelta(hours=schedule.interval_hours or 24)
        schedule.save(update_fields=["last_run_at", "next_run_at"])
