"""Posts screen: the queue of one account, grouped by day."""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import TYPE_CHECKING, Callable

import flet as ft

from ..config import QUEUE_FILE, post_dir
from ..scheduling import pending_posts, schedule_account
from ..i18n import plural, t
from ..models import Account, Post, PostStatus
from ..services.media import is_video, thumbnail_for
from ..services.x_scheduler import ProfileBusyError
from ..storage import QueueRepository
from . import theme
from .common import account_avatar, run_in_background, show_toast, watch_file
from .formatting import clock, compact_number, day_header
from .preview import PreviewDialog
from .status import status_chip

if TYPE_CHECKING:
    from .shell import Shell

THUMB_SIZE = 92


class PostTile(ft.Container):
    """One row in the list: time, status, text excerpt and a media thumbnail."""

    def __init__(self, post: Post, on_click: Callable[[Post], None]) -> None:
        self.post = post
        self._thumb_slot = ft.Container(
            width=THUMB_SIZE, height=THUMB_SIZE, border_radius=theme.RADIUS_S,
            bgcolor="#16161A", alignment=ft.Alignment.CENTER,
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            content=ft.Icon(ft.Icons.NOTES_ROUNDED, color=theme.TEXT_FAINT) if not post.media else None,
        )

        super().__init__(
            content=ft.Row(
                [
                    ft.Column(
                        [
                            ft.Text(clock(post.scheduled_at), size=20, weight=ft.FontWeight.W_700, color=theme.TEXT),
                            status_chip(post.status),
                            *self._views(post),
                        ],
                        spacing=8,
                        width=96,
                        horizontal_alignment=ft.CrossAxisAlignment.START,
                    ),
                    ft.Text(post.text, size=14, color=theme.TEXT, max_lines=3,
                            overflow=ft.TextOverflow.ELLIPSIS, expand=True),
                    self._thumb_slot,
                ],
                spacing=18,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor=theme.SURFACE,
            border=theme.border(),
            border_radius=theme.RADIUS_M,
            padding=16,
            blur=ft.Blur(12, 12),
            animate=ft.Animation(160, ft.AnimationCurve.EASE_OUT),
            on_hover=self._on_hover,
            on_click=lambda _: on_click(post),
            ink=False,
        )

    @staticmethod
    def _views(post: Post) -> list[ft.Control]:
        """Views after the first hour, under the status of a published post."""
        if not post.stats:
            return []
        return [ft.Row([ft.Icon(ft.Icons.BAR_CHART, size=14, color=theme.TEXT_MUTED),
                        ft.Text(compact_number(post.stats.views), size=12, color=theme.TEXT_MUTED)],
                       spacing=4, tight=True, tooltip=t("posts.views_tip"))]

    def load_thumbnail(self) -> None:
        """Called from a background thread: ffmpeg may need a moment for videos."""
        if not self.post.media:
            return
        first = post_dir(self.post.id) / self.post.media[0]
        thumb = thumbnail_for(first)
        layers: list[ft.Control] = []
        if thumb:
            layers.append(ft.Image(src=thumb.read_bytes(), width=THUMB_SIZE, height=THUMB_SIZE, fit=ft.BoxFit.COVER))
        else:
            layers.append(ft.Icon(ft.Icons.BROKEN_IMAGE_OUTLINED, color=theme.DANGER))
        if is_video(first):
            layers.append(ft.Container(
                left=0, top=0, right=0, bottom=0, alignment=ft.Alignment.CENTER,
                content=ft.Icon(ft.Icons.PLAY_CIRCLE_FILL_ROUNDED, color="#E6FFFFFF", size=34),
            ))
        if len(self.post.media) > 1:
            layers.append(ft.Container(
                right=6, bottom=6, padding=ft.Padding.symmetric(horizontal=6, vertical=1),
                bgcolor="#B3000000", border_radius=6,
                content=ft.Text(f"+{len(self.post.media) - 1}", size=11, color="#FFFFFF"),
            ))
        self._thumb_slot.content = ft.Stack(layers, width=THUMB_SIZE, height=THUMB_SIZE)
        if self._thumb_slot.page:
            self._thumb_slot.update()

    def _on_hover(self, e: ft.Event) -> None:
        hovered = bool(e.data)
        self.border = theme.border(theme.BORDER_HOVER if hovered else theme.BORDER)
        self.bgcolor = theme.SURFACE_HOVER if hovered else theme.SURFACE
        self.update()


class PostsView(ft.Container):
    def __init__(self, shell: "Shell", account: Account) -> None:
        self.shell = shell
        self.account = account
        self.repo = QueueRepository()
        self._running = False

        self._summary = ft.Row(spacing=10, wrap=True)
        self._list = ft.Column(spacing=12)

        super().__init__(
            expand=True,
            padding=ft.Padding.symmetric(horizontal=36, vertical=28),
            content=ft.Column(
                [self._header(), self._summary, ft.Container(height=4), self._list],
                spacing=18,
                scroll=ft.ScrollMode.AUTO,
                expand=True,
            ),
        )

    # --- Lifecycle ----------------------------------------------------------

    def did_mount(self) -> None:
        self._running = True
        self.refresh()
        self.page.run_task(watch_file, QUEUE_FILE, lambda: self._running, self.refresh)

    def will_unmount(self) -> None:
        self._running = False

    # --- Rendering ----------------------------------------------------------

    def _header(self) -> ft.Control:
        back = ft.IconButton(ft.Icons.ARROW_BACK_ROUNDED, icon_color=theme.TEXT, tooltip=t("posts.back"),
                             on_click=lambda _: self.shell.show_home())
        who = ft.Row(
            [
                account_avatar(self.account, radius=22),
                ft.Column(
                    [
                        ft.Text(self.account.display_name or self.account.handle, size=22,
                                weight=ft.FontWeight.W_700, color=theme.TEXT),
                        ft.Text(f"{self.account.at_handle} · {t('posts.title')}", size=13, color=theme.TEXT_MUTED),
                    ],
                    spacing=0,
                ),
            ],
            spacing=14,
        )
        approve_all = theme.ghost_button(t("posts.approve_all"), ft.Icons.DONE_ALL_ROUNDED,
                                         on_click=lambda _: self._approve_all())
        self._schedule_button = theme.primary_button(t("posts.schedule"), ft.Icons.SCHEDULE_SEND_ROUNDED,
                                                     on_click=lambda _: self._schedule())
        self._schedule_spinner = ft.ProgressRing(width=18, height=18, stroke_width=2, color=theme.TEXT, visible=False)
        actions = ft.Row([approve_all, self._schedule_spinner, self._schedule_button], spacing=10)
        return ft.Row([ft.Row([back, who], spacing=8), actions], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

    def refresh(self) -> None:
        try:
            posts = self.repo.for_account(self.account.handle)
        except (ValueError, KeyError) as exc:
            show_toast(self.page, f"queue.json: {exc}", error=True)
            return

        counts = defaultdict(int)
        for post in posts:
            counts[post.status] += 1
        self._summary.controls = [
            self._count_pill(plural(f"count.{status.value}", counts[status]), counts[status])
            for status in PostStatus if counts[status]
        ] or [self._count_pill(t("posts.total"), 0)]

        # Group by calendar day so the week reads like a schedule.
        by_day: dict[date, list[Post]] = defaultdict(list)
        for post in posts:
            by_day[post.scheduled_at.astimezone().date()].append(post)

        tiles: list[PostTile] = []
        controls: list[ft.Control] = []
        for day in sorted(by_day):
            controls.append(ft.Text(day_header(by_day[day][0].scheduled_at), size=13,
                                    weight=ft.FontWeight.W_600, color=theme.TEXT_MUTED))
            for post in by_day[day]:
                tile = PostTile(post, on_click=self._open_preview)
                tiles.append(tile)
                controls.append(tile)

        self._list.controls = controls or [self._empty_state()]
        if self.page:
            self.update()
        run_in_background(lambda: [tile.load_thumbnail() for tile in tiles])

    @staticmethod
    def _count_pill(label: str, count: int) -> ft.Control:
        return ft.Container(
            content=ft.Row(
                [ft.Text(str(count), size=16, weight=ft.FontWeight.W_700, color=theme.TEXT),
                 ft.Text(label, size=13, color=theme.TEXT_MUTED)],
                spacing=8, tight=True,
            ),
            padding=ft.Padding.symmetric(horizontal=14, vertical=8),
            bgcolor=theme.SURFACE,
            border=theme.border(),
            border_radius=40,
        )

    @staticmethod
    def _empty_state() -> ft.Control:
        return theme.glass(
            ft.Column(
                [
                    ft.Icon(ft.Icons.INBOX_OUTLINED, size=40, color=theme.TEXT_MUTED),
                    ft.Text(t("posts.empty.title"), size=18, color=theme.TEXT, weight=ft.FontWeight.W_600),
                    ft.Text(t("posts.empty.hint"), size=13, color=theme.TEXT_MUTED, text_align=ft.TextAlign.CENTER),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=10,
            ),
            padding=48,
        )

    # --- Actions ------------------------------------------------------------

    def _open_preview(self, post: Post) -> None:
        self.page.show_dialog(PreviewDialog(post, self.account, on_status_change=self._set_status))

    def _set_status(self, post: Post, status: PostStatus) -> None:
        # Re-read before writing so edits made meanwhile (CLI, Claude) are not lost.
        fresh = self.repo.get(post.id)
        if fresh is None:
            show_toast(self.page, t("posts.gone"), error=True)
            self.refresh()
            return
        fresh.status = status
        self.repo.upsert(fresh)
        show_toast(self.page, t(f"posts.toast.{status.value}"))
        self.refresh()

    def _schedule(self) -> None:
        """Push approved future posts into X's scheduler (runs in the background)."""
        todo = pending_posts(self.account.handle)
        if not todo:
            show_toast(self.page, t("posts.schedule.nothing"))
            return

        self._set_scheduling(True)
        show_toast(self.page, t("posts.schedule.started", count=len(todo)))

        def on_result(result) -> None:
            # Statuses are already saved by schedule_account; just repaint.
            if not result.ok:
                show_toast(self.page, t("posts.schedule.failed", error=result.message), error=True)
            self.refresh()

        def work() -> None:
            try:
                results = schedule_account(self.account, self.shell.settings, on_result=on_result)
                done = sum(r.ok for r in results)
                show_toast(self.page, t("posts.schedule.done", done=done, total=len(results)),
                           error=done != len(results))
            except ProfileBusyError:
                show_toast(self.page, t("posts.schedule.profile_busy"), error=True)
            except Exception as exc:  # AdsPower down, browser closed mid-way, ...
                show_toast(self.page, f"{type(exc).__name__}: {exc}", error=True)
            finally:
                self._set_scheduling(False)
                self.refresh()

        run_in_background(work)

    def _set_scheduling(self, busy: bool) -> None:
        self._schedule_button.disabled = busy
        self._schedule_spinner.visible = busy
        if self.page:
            self.update()

    def _approve_all(self) -> None:
        posts = self.repo.load()
        changed = 0
        for post in posts:
            if post.account == self.account.handle and post.status is PostStatus.DRAFT:
                post.status = PostStatus.APPROVED
                changed += 1
        if changed:
            self.repo.save(posts)
        show_toast(self.page, t("posts.toast.approved_all", count=changed))
        self.refresh()
