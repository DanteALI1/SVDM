"""Audit log retention cleanup."""
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.tenants.models import Tenant


@shared_task
def cleanup_audit_logs():
    deleted_total = 0
    for tenant in Tenant.objects.filter(is_active=True):
        days = tenant.audit_retention_days or 180
        cutoff = timezone.now() - timedelta(days=days)
        deleted, _ = AuditLog.objects.filter(tenant=tenant, created_at__lt=cutoff).delete()
        deleted_total += deleted
    # Platform / null-tenant logs: default 180
    cutoff = timezone.now() - timedelta(days=180)
    deleted, _ = AuditLog.objects.filter(tenant__isnull=True, created_at__lt=cutoff).delete()
    deleted_total += deleted
    return {"deleted": deleted_total}
