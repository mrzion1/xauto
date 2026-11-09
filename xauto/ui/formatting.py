"""Locale-aware helpers for dates shown in the UI."""

from __future__ import annotations

import re
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


_URL_RE = re.compile(r"https?://\S+")

_WEEKDAYS = {
    "ru": ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"],
    "en": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
}


def day_header(value: datetime) -> str:
    """'Пн, 10 ноя' / 'Mon, Nov 10' in the PC's local time."""
    local = value.astimezone()
    lang = get_language() if get_language() in _WEEKDAYS else "en"
    weekday = _WEEKDAYS[lang][local.weekday()]
    month = _MONTHS[lang][local.month - 1]
    return f"{weekday}, {local.day} {month}" if lang == "ru" else f"{weekday}, {month} {local.day}"


def clock(value: datetime) -> str:
    return f"{value.astimezone():%H:%M}"


def duration(seconds: float) -> str:
    seconds = int(round(seconds))
    return f"{seconds // 60}:{seconds % 60:02d}"


def tweet_length(text: str) -> int:
    """Approximate X length: every URL counts as 23 characters."""
    without_urls = _URL_RE.sub("x" * 23, text)
    return len(without_urls)
