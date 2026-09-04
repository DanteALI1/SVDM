"""SLA overdue using tenant work calendar (no pre-filled RU holidays)."""
from __future__ import annotations

from datetime import datetime, time, timedelta, date
from django.utils import timezone


def get_calendar(tenant):
    from apps.tenants.models import WorkCalendar

    cal, _ = WorkCalendar.objects.get_or_create(tenant=tenant, defaults={"workdays": [0, 1, 2, 3, 4]})
    return cal


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


def is_working_day(calendar, d: date) -> bool:
    date_str = d.isoformat()
    for exc in calendar.exceptions or []:
        if exc.get("date") == date_str:
            return bool(exc.get("is_working"))
    return d.weekday() in (calendar.workdays or [])


def working_minutes_between(calendar, start: datetime, end: datetime) -> float:
    if end <= start:
        return 0.0
    total = 0.0
    cursor = timezone.localtime(start)
    end_local = timezone.localtime(end)
    while cursor < end_local:
        nxt = min(cursor + timedelta(hours=1), end_local)
        mid = cursor + (nxt - cursor) / 2
        if is_working_moment(calendar, mid):
            total += (nxt - cursor).total_seconds() / 60.0
        cursor = nxt
    return total


def compute_overdue(ticket) -> bool:
    """True when now is past sla_deadline, respecting work calendar.

    If deadline falls on a non-working period, overdue starts at the next
    working moment after the deadline.
    """
    if not ticket.sla_deadline:
        return False
    if ticket.status == ticket.Status.CLOSED:
        return False
    now = timezone.now()
    try:
        cal = get_calendar(ticket.tenant)
    except Exception:
        return now > ticket.sla_deadline

    effective = timezone.localtime(ticket.sla_deadline)
    if not is_working_moment(cal, effective):
        # roll forward to next working minute (cap 14 days)
        for _ in range(14 * 24 * 60):
            effective += timedelta(minutes=1)
            if is_working_moment(cal, effective):
                break
    return timezone.localtime(now) > effective


def add_working_hours(calendar, start: datetime, hours: float) -> datetime:
    remaining = hours * 60.0
    cursor = timezone.localtime(start)
    guard = 0
    while remaining > 0 and guard < 100000:
        guard += 1
        if is_working_moment(calendar, cursor):
            remaining -= 1
        cursor += timedelta(minutes=1)
    return cursor
