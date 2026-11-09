"""Locale-aware helpers for dates shown in the UI."""

from __future__ import annotations

from datetime import datetime

from ..i18n import get_language

_MONTHS = {
    "ru": ["янв", "фев", "мар", "апр", "мая", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"],
    "en": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
}


def short_date(value: datetime) -> str:
    """'14 ноя, 18:00' / 'Nov 14, 18:00' in the PC's local time."""
    local = value.astimezone()
    month = _MONTHS.get(get_language(), _MONTHS["en"])[local.month - 1]
    if get_language() == "ru":
        return f"{local.day} {month}, {local:%H:%M}"
    return f"{month} {local.day}, {local:%H:%M}"


def initials(name: str) -> str:
    parts = [p for p in name.replace("_", " ").split() if p]
    return "".join(p[0] for p in parts[:2]).upper() or "?"
