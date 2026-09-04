from django.conf import settings
from django.db import models
from apps.core.models import TenantScopedModel


class Ticket(TenantScopedModel):
    class Type(models.TextChoices):
        VULNERABILITY = "vulnerability", "Vulnerability"
        INCIDENT = "incident", "Incident"
        CHANGE = "change", "Change"
        GENERAL = "general", "General"

    class Goal(models.TextChoices):
        INFORM = "inform", "Inform"
        RESOLVE = "resolve", "Resolve"

    class Status(models.TextChoices):
        NEW = "new", "New"
        IN_PROGRESS = "in_progress", "In progress"
        FOR_REVIEW = "for_review", "For review"  # на ознакомлении
        ON_CHECK = "on_check", "On check"  # на проверке
        REWORK = "rework", "Rework"  # на доработке
        CLOSED = "closed", "Closed"

    class Priority(models.TextChoices):
        CRITICAL = "critical", "Critical"
        HIGH = "high", "High"
        MEDIUM = "medium", "Medium"
        LOW = "low", "Low"

    title = models.CharField(max_length=512)
    description = models.TextField(blank=True, default="")
    ticket_type = models.CharField(max_length=32, choices=Type.choices)
    goal = models.CharField(max_length=16, choices=Goal.choices)
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.NEW)
    priority = models.CharField(max_length=16, choices=Priority.choices, default=Priority.MEDIUM)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_tickets"
    )
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_tickets",
    )
    vulnerabilities = models.ManyToManyField(
        "vulnerabilities.Vulnerability", blank=True, related_name="tickets"
    )
    assets = models.ManyToManyField("assets.Asset", blank=True, related_name="tickets")
    sla_deadline = models.DateTimeField(null=True, blank=True)
    planned_fixation_at = models.DateTimeField(null=True, blank=True)
    is_overdue = models.BooleanField(default=False)

    ALLOWED_TRANSITIONS = {
        Status.NEW: {Status.IN_PROGRESS, Status.FOR_REVIEW},
        Status.IN_PROGRESS: {Status.ON_CHECK, Status.REWORK},
        Status.FOR_REVIEW: {Status.ON_CHECK, Status.CLOSED},
        Status.ON_CHECK: {Status.REWORK, Status.CLOSED},
        Status.REWORK: {Status.IN_PROGRESS},
        Status.CLOSED: set(),
    }

    class Meta:
        ordering = ["-created_at"]

    def can_transition(self, new_status):
        if new_status == self.Status.FOR_REVIEW and self.goal != self.Goal.INFORM:
            return False
        return new_status in self.ALLOWED_TRANSITIONS.get(self.status, set())


class TicketComment(TenantScopedModel):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    body = models.TextField()


class TicketAttachment(TenantScopedModel):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="attachments")
    file = models.FileField(upload_to="tickets/%Y/%m/")
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    name = models.CharField(max_length=255)


class TicketHistory(TenantScopedModel):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="history")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=64)
    changes = models.JSONField(default=dict)
