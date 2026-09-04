import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
app = Celery("svdb")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

app.conf.beat_schedule = {
    "run-vulnerability-sync-schedules": {
        "task": "apps.vulnerabilities.tasks.run_scheduled_syncs",
        "schedule": crontab(minute="*/15"),
    },
    "cleanup-audit-logs-daily": {
        "task": "apps.audit.tasks.cleanup_audit_logs",
        "schedule": crontab(hour=3, minute=15),
    },
}
