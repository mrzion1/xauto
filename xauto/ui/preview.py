"""Post preview styled like a post on X (dark mode), plus review actions."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

import flet as ft

from ..config import post_dir
from ..i18n import t
from ..models import Account, Post, PostStatus
from ..services.media import is_video, open_in_system, thumbnail_for, video_duration
from . import theme
from .common import account_avatar, show_toast
from .formatting import duration, short_date, tweet_length
from .status import status_chip

# X dark mode palette, used only inside the mock so it reads as "a real post".
X_BG = "#000000"
X_BORDER = "#2F3336"
X_TEXT = "#E7E9EA"
X_MUTED = "#71767B"

FREE_LIMIT = 280  # longer posts need X Premium


class PreviewDialog(ft.AlertDialog):
    def __init__(self, post: Post, account: Account, on_status_change: Callable[[Post, PostStatus], None]) -> None:
        self.post = post
        self.account = account
        self._on_status_change = on_status_change
        folder = post_dir(post.id)

        super().__init__(
            modal=False,
            bgcolor="#0E0E11",
            shape=ft.RoundedRectangleBorder(radius=theme.RADIUS_L),
            content_padding=ft.Padding.all(20),
            content=ft.Container(
                width=600,
                content=ft.Column(
                    [self._mock(folder), self._meta()],
                    spacing=16,
                    tight=True,
                    scroll=ft.ScrollMode.AUTO,
                ),
            ),
            actions=self._actions(folder),
            actions_alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )

    # --- The "tweet" ----------------------------------------------------------

    def _mock(self, folder: Path) -> ft.Control:
        header = ft.Row(
            [
                ft.Text(self.account.display_name or self.account.handle, color=X_TEXT,
                        weight=ft.FontWeight.W_700, size=15),
                ft.Text(f"{self.account.at_handle} · {short_date(self.post.scheduled_at)}", color=X_MUTED, size=14),
            ],
            spacing=6,
            wrap=True,
        )
        body = ft.Text(self.post.text, color=X_TEXT, size=15, selectable=True)
        engagement = ft.Row(
            [ft.Icon(icon, size=18, color=X_MUTED) for icon in (
                ft.Icons.CHAT_BUBBLE_OUTLINE, ft.Icons.REPEAT, ft.Icons.FAVORITE_BORDER,
                ft.Icons.BAR_CHART, ft.Icons.BOOKMARK_BORDER,
            )],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )

        column: list[ft.Control] = [header, body]
        media = [folder / name for name in self.post.media]
        if media:
            column.append(self._media(media))
        column.append(engagement)

        return ft.Container(
            bgcolor=X_BG,
            border=ft.Border.all(1, X_BORDER),
            border_radius=16,
            padding=16,
            content=ft.Row(
                [
                    ft.Container(account_avatar(self.account, radius=20), alignment=ft.Alignment.TOP_CENTER),
                    ft.Column(column, spacing=10, expand=True),
                ],
                vertical_alignment=ft.CrossAxisAlignment.START,
                spacing=12,
            ),
        )

    def _media(self, files: list[Path]) -> ft.Control:
        tiles = [self._media_tile(f, single=len(files) == 1) for f in files]
        if len(tiles) == 1:
            return tiles[0]
        return ft.ResponsiveRow(tiles, spacing=4, run_spacing=4)

    def _media_tile(self, file: Path, single: bool) -> ft.Control:
        thumb = thumbnail_for(file)
        picture: ft.Control
        if thumb:
            picture = ft.Image(src=thumb.read_bytes(), fit=ft.BoxFit.COVER, width=float("inf"),
                               height=320 if single else 160)
        else:
            picture = ft.Container(
                height=200, bgcolor="#16181C", alignment=ft.Alignment.CENTER,
                content=ft.Text(file.name if file.exists() else t("preview.missing", name=file.name),
                                color=X_MUTED if file.exists() else theme.DANGER),
            )

        layers: list[ft.Control] = [picture]
        if is_video(file):
            # Play button + duration badge, like X's video player before it starts.
            layers.append(ft.Container(
                alignment=ft.Alignment.CENTER, left=0, top=0, right=0, bottom=0,
                content=ft.Container(
                    width=64, height=64, border_radius=32, bgcolor="#CC1D9BF0", alignment=ft.Alignment.CENTER,
                    content=ft.Icon(ft.Icons.PLAY_ARROW_ROUNDED, size=40, color="#FFFFFF"),
                ),
            ))
            seconds = video_duration(file)
            if seconds:
                layers.append(ft.Container(
                    left=10, bottom=10, padding=ft.Padding.symmetric(horizontal=6, vertical=2),
                    bgcolor="#B3000000", border_radius=4,
                    content=ft.Text(duration(seconds), size=12, color="#FFFFFF"),
                ))

        return ft.Container(
            content=ft.Stack(layers),
            border_radius=16,
            border=ft.Border.all(1, X_BORDER),
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            tooltip=t("preview.open_file"),
            on_click=lambda _: open_in_system(file) if file.exists() else None,
            col=12 if single else 6,
        )

    # --- Below the mock ---------------------------------------------------------

    def _meta(self) -> ft.Control:
        length = tweet_length(self.post.text)
        long_post = length > FREE_LIMIT
        items: list[ft.Control] = [
            status_chip(self.post.status),
            ft.Text(t("preview.when", date=short_date(self.post.scheduled_at)), size=13, color=theme.TEXT_MUTED),
            ft.Text(
                t("preview.length", count=length) + (f" · {t('preview.premium')}" if long_post else ""),
                size=13,
                color=theme.WARN if long_post else theme.TEXT_MUTED,
            ),
        ]
        if self.post.error:
            items.append(ft.Text(self.post.error, size=13, color=theme.DANGER))
        return ft.Row(items, spacing=14, wrap=True, vertical_alignment=ft.CrossAxisAlignment.CENTER)

    def _actions(self, folder: Path) -> list[ft.Control]:
        left = ft.TextButton(
            t("preview.folder"),
            icon=ft.Icons.FOLDER_OPEN_OUTLINED,
            on_click=lambda _: open_in_system(folder) if folder.exists() else show_toast(
                self.page, t("preview.no_folder"), error=True),
            style=ft.ButtonStyle(color=theme.TEXT_MUTED),
        )

        right: list[ft.Control] = [
            ft.TextButton(t("preview.close"), on_click=lambda _: self.page.pop_dialog(),
                          style=ft.ButtonStyle(color=theme.TEXT_MUTED)),
        ]
        # Only the review step is editable here; later statuses belong to the scheduler.
        if self.post.status is PostStatus.DRAFT:
            right.append(theme.primary_button(t("preview.approve"), ft.Icons.CHECK_ROUNDED,
                                              on_click=lambda _: self._set_status(PostStatus.APPROVED)))
        elif self.post.status is PostStatus.APPROVED:
            right.append(theme.ghost_button(t("preview.unapprove"), ft.Icons.UNDO_ROUNDED,
                                            on_click=lambda _: self._set_status(PostStatus.DRAFT)))

        return [left, ft.Row(right, spacing=8, tight=True)]

    def _set_status(self, status: PostStatus) -> None:
        self.page.pop_dialog()
        self._on_status_change(self.post, status)
