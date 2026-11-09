"""Card that represents one X account on the home screen."""

from __future__ import annotations

from typing import Callable

import flet as ft

from ..i18n import t
from ..models import Account
from ..storage import QueueSummary
from . import theme
from .common import account_avatar
from .formatting import short_date


class AccountCard(ft.Container):
    def __init__(
        self,
        account: Account,
        summary: QueueSummary,
        warning_days: int,
        on_open: Callable[[Account], None],
        on_posts: Callable[[Account], None],
        on_edit: Callable[[Account], None],
        on_delete: Callable[[Account], None],
    ) -> None:
        self.account = account
        self._on_open = on_open

        self._open_button = ft.OutlinedButton(
            t("card.open"),
            icon=ft.Icons.OPEN_IN_NEW_ROUNDED,
            on_click=lambda _: self._handle_open(),
            tooltip=t("card.open.tooltip"),
            expand=True,
            style=ft.ButtonStyle(
                color=theme.TEXT,
                side=ft.BorderSide(1, theme.BORDER_HOVER),
                shape=ft.RoundedRectangleBorder(radius=theme.RADIUS_S),
                padding=ft.Padding.symmetric(horizontal=14, vertical=12),
            ),
        )
        self._posts_button = ft.Button(
            t("card.posts.open"),
            icon=ft.Icons.VIEW_AGENDA_OUTLINED,
            on_click=lambda _: on_posts(account),
            expand=True,
            bgcolor=theme.ACCENT,
            color=theme.ON_ACCENT,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=theme.RADIUS_S),
                padding=ft.Padding.symmetric(horizontal=14, vertical=12),
            ),
        )
        self._spinner = ft.ProgressRing(width=16, height=16, stroke_width=2, color=theme.TEXT, visible=False)

        menu = ft.PopupMenuButton(
            icon=ft.Icons.MORE_HORIZ_ROUNDED,
            icon_color=theme.TEXT_MUTED,
            bgcolor="#1A1A1F",
            items=[
                ft.PopupMenuItem(content=t("card.edit"), icon=ft.Icons.EDIT_OUTLINED, on_click=lambda _: on_edit(account)),
                ft.PopupMenuItem(content=t("card.delete"), icon=ft.Icons.DELETE_OUTLINE, on_click=lambda _: on_delete(account)),
            ],
        )

        header = ft.Row(
            [
                account_avatar(account),
                ft.Column(
                    [
                        ft.Text(account.display_name or account.handle, size=17, weight=ft.FontWeight.W_600,
                                color=theme.TEXT, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                        ft.Text(account.at_handle, size=13, color=theme.TEXT_MUTED, selectable=True),
                    ],
                    spacing=2,
                    expand=True,
                ),
                menu,
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        super().__init__(
            content=ft.Column(
                [
                    header,
                    ft.Container(height=1, bgcolor=theme.BORDER),
                    self._queue_block(summary, warning_days),
                    ft.Row([self._posts_button, self._open_button, self._spinner],
                           vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
                ],
                spacing=16,
            ),
            bgcolor=theme.SURFACE,
            border=theme.border(),
            border_radius=theme.RADIUS_L,
            padding=20,
            blur=ft.Blur(12, 12),
            animate=ft.Animation(180, ft.AnimationCurve.EASE_OUT),
            on_hover=self._on_hover,
            col={"xs": 12, "sm": 6, "lg": 4},
        )

    # --- Pieces -------------------------------------------------------------

    @staticmethod
    def _queue_block(summary: QueueSummary, warning_days: int) -> ft.Control:
        days = summary.days_left()

        # Traffic light: red = nothing planned / ran out, yellow = refill soon, green = fine.
        if summary.last_post_at is None:
            color, title, note = theme.DANGER, t("card.queue.empty"), ""
        else:
            title = t("card.queue.until", date=short_date(summary.last_post_at))
            if days < 0:
                color, note = theme.DANGER, t("card.queue.over", days=-days)
            elif days == 0:
                color, note = theme.WARN, t("card.queue.today")
            else:
                color = theme.WARN if days <= warning_days else theme.OK
                note = t("card.queue.days", days=days)

        dot = ft.Container(width=8, height=8, border_radius=4, bgcolor=color,
                           shadow=ft.BoxShadow(blur_radius=8, color=color))
        return ft.Column(
            [
                ft.Row([dot, ft.Text(title, size=14, color=theme.TEXT, weight=ft.FontWeight.W_500)], spacing=10),
                ft.Row(
                    [
                        ft.Text(note, size=12, color=color),
                        ft.Text(t("card.posts", count=summary.upcoming), size=12, color=theme.TEXT_FAINT),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
            ],
            spacing=6,
        )

    # --- Events -------------------------------------------------------------

    def _on_hover(self, e: ft.Event) -> None:
        hovered = bool(e.data)  # True on enter, False on exit
        self.border = theme.border(theme.BORDER_HOVER if hovered else theme.BORDER)
        self.bgcolor = theme.SURFACE_HOVER if hovered else theme.SURFACE
        self.update()

    def _handle_open(self) -> None:
        self.set_busy(True)
        self._on_open(self.account)

    def set_busy(self, busy: bool) -> None:
        self._open_button.disabled = busy
        self._spinner.visible = busy
        self.update()
