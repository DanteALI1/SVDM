"""SLA overdue using tenant work calendar (no pre-filled RU holidays)."""
from datetime import datetime, time, timedelta
from django.utils import timezone


def compute_overdue(ticket) -> bool:
    if not ticket.sla_deadline or ticket.status == ticket.Status.CLOSED:
        return False
    return timezone.now() > ticket.sla_deadline


def is_working_moment(calendar, dt: datetime) -> bool:
    """Check if datetime falls into working hours considering exceptions."""
    local = timezone.localtime(dt)
    date_str = local.date().isoformat()
    for exc in calendar.exceptions or []:
        if exc.get("date") == date_str:
            return bool(exc.get("is_working"))
    weekday = local.weekday()  # Mon=0
    if weekday not in (calendar.workdays or []):
        return False
    start = calendar.workday_start if isinstance(calendar.workday_start, time) else time(9, 0)
    end = calendar.workday_end if isinstance(calendar.workday_end, time) else time(18, 0)
    t = local.time()
    return start <= t <= end
