"""Visual mapping of post statuses (shared by the list and the preview)."""

from __future__ import annotations

import flet as ft

from ..i18n import t
from ..models import PostStatus
from . import theme

STATUS_COLORS: dict[PostStatus, str] = {
    PostStatus.DRAFT: theme.TEXT_MUTED,
    PostStatus.APPROVED: theme.ACCENT,
    PostStatus.SCHEDULED: "#8AB4FF",
    PostStatus.PUBLISHED: theme.OK,
    PostStatus.FAILED: theme.DANGER,
}


def status_chip(status: PostStatus) -> ft.Control:
    color = STATUS_COLORS[status]
    return ft.Container(
        content=ft.Text(t(f"status.{status.value}"), size=11, color=color, weight=ft.FontWeight.W_600),
        padding=ft.Padding.symmetric(horizontal=10, vertical=4),
        border=theme.border(ft.Colors.with_opacity(0.4, color)),
        border_radius=20,
    )
