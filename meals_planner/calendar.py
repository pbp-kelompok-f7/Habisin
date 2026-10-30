"""Monthly navigation and account-owned meal counts for the planner calendar."""

import re
from datetime import date, timedelta
from urllib.parse import urlencode

from django.db.models import Count

from .models import PlannedMeal
from .services import MONTHS, parse_week, week_start


def parse_month(value):
    """Accept an explicit YYYY-MM month with room for adjacent grid dates."""
    error = "Pilih bulan dengan format YYYY-MM yang valid."
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}", value):
        raise ValueError(error)
    try:
        month = date.fromisoformat(value + "-01")
    except ValueError:
        raise ValueError(error) from None
    if not 2 <= month.year <= 9998:
        raise ValueError(error)
    return month


def _month_key(month):
    return f"{month.year:04d}-{month.month:02d}"


def month_state(user, month, today):
    """Build a six-week calendar without revealing another account's plans."""
    month = parse_month(_month_key(month))
    first_day = week_start(month)
    end = first_day + timedelta(days=42)
    counts = {
        row["date"]: row["count"]
        for row in PlannedMeal.objects.filter(
            user=user, date__gte=first_day, date__lt=end
        ).values("date").annotate(count=Count("pk")).order_by()
    }

    days = []
    total = 0
    scheduled_days = 0
    for offset in range(42):
        day = first_day + timedelta(days=offset)
        week = week_start(day)
        count = counts.get(day, 0)
        in_month = (day.year, day.month) == (month.year, month.month)
        if in_month:
            total += count
            scheduled_days += bool(count)
        try:
            parse_week(week.isoformat())
            selectable = True
        except ValueError:
            selectable = False
        days.append({
            "date": day.isoformat(),
            "day": day.day,
            "label": f"{day.day} {MONTHS[day.month]} {day.year}",
            "week": week.isoformat(),
            "weekday": day.weekday(),
            "in_month": in_month,
            "is_today": day == today,
            "count": count,
            "selectable": selectable,
            "url": "?" + urlencode({"week": week.isoformat(), "day": day.weekday()}) if selectable else None,
        })

    previous_month = None
    if month > date(2, 1, 1):
        previous_month = _month_key(month - timedelta(days=1))
    next_month = None
    if month < date(9998, 12, 1):
        following = date(month.year + 1, 1, 1) if month.month == 12 else date(month.year, month.month + 1, 1)
        next_month = _month_key(following)

    return {
        "month": _month_key(month),
        "label": f"{MONTHS[month.month]} {month.year}",
        "previous_month": previous_month,
        "next_month": next_month,
        "today": today.isoformat(),
        "days": days,
        "total": total,
        "scheduled_days": scheduled_days,
    }
