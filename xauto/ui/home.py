"""Home screen: header, quick stats and the grid of account cards."""

from __future__ import annotations

from typing import TYPE_CHECKING

import flet as ft

from ..config import QUEUE_FILE
from ..i18n import plural, t
from ..models import Account
from ..services.adspower import AdsPowerClient, AdsPowerError
from ..services.x_profile import download_avatar, fetch_profile
from ..storage import AccountRepository, QueueRepository
from . import theme
from .account_card import AccountCard
from .common import run_in_background, show_toast, watch_file
from .dialogs import AccountDialog, ConfirmDeleteDialog

if TYPE_CHECKING:
    from .shell import Shell


class HomeView(ft.Container):
    def __init__(self, shell: "Shell") -> None:
        self.shell = shell
        self.settings = shell.settings
        self.accounts_repo = AccountRepository()
        self.queue_repo = QueueRepository()
        self.adspower = AdsPowerClient(self.settings.adspower_api_url, self.settings.adspower_api_key)

        self._adspower_online = False
        self._running = False

        self._header = ft.Container()
        self._stats = ft.Row(spacing=12, wrap=True)
        self._grid = ft.ResponsiveRow(spacing=18, run_spacing=18)

        super().__init__(
            expand=True,
            padding=ft.Padding.symmetric(horizontal=36, vertical=28),
            content=ft.Column(
                [
                    self._header,
                    self._stats,
                    ft.Container(height=8),
                    ft.Text(t("home.accounts"), size=13, color=theme.TEXT_MUTED, weight=ft.FontWeight.W_600),
                    self._grid,
                ],
                spacing=18,
                scroll=ft.ScrollMode.AUTO,
                expand=True,
            ),
        )

    # --- Lifecycle ----------------------------------------------------------

    def did_mount(self) -> None:
        self._running = True
        self.refresh()
        run_in_background(self._sync_profiles)
        # Re-render when queue.json is changed from outside (CLI, Claude).
        self.page.run_task(watch_file, QUEUE_FILE, lambda: self._running, self.refresh)

    def will_unmount(self) -> None:
        self._running = False

    # --- Rendering ----------------------------------------------------------

    def refresh(self) -> None:
        try:
            accounts = self.accounts_repo.load()
        except (ValueError, KeyError) as exc:
            # Never fall back to an empty list here: a later save would wipe the file.
            show_toast(self.page, f"accounts.json: {exc}", error=True)
            return
        try:
            posts = self.queue_repo.load()
        except (ValueError, KeyError):
            posts = []  # a broken queue file must not take the whole UI down

        summaries = {a.id: self.queue_repo.summary_for(a.handle, posts) for a in accounts}
        need_refill = sum(
            1 for s in summaries.values()
            if s.days_left() is None or s.days_left() <= self.settings.refill_warning_days
        )

        queued = sum(s.upcoming for s in summaries.values())
        self._header.content = self._build_header()
        self._stats.controls = [
            self._stat(str(len(accounts)), plural("stats.accounts", len(accounts))),
            self._stat(str(queued), plural("stats.queued", queued)),
            self._stat(str(need_refill), t("stats.refill"), theme.WARN if need_refill else None),
            self._adspower_pill(),
        ]

        if accounts:
            self._grid.controls = [
                AccountCard(
                    account,
                    summaries[account.id],
                    self.settings.refill_warning_days,
                    on_open=self._open_account,
                    on_posts=self.shell.show_posts,
                    on_edit=self._edit_account,
                    on_delete=self._confirm_delete,
                )
                for account in accounts
            ]
        else:
            self._grid.controls = [self._empty_state()]

        if self.page:
            self.update()

    def _build_header(self) -> ft.Control:
        brand = ft.Row(
            [
                ft.Container(
                    content=ft.Image(src="x_logo.svg", width=22, height=22),
                    width=48, height=48, alignment=ft.Alignment.CENTER,
                    border=theme.border(theme.BORDER_HOVER), border_radius=theme.RADIUS_M,
                    bgcolor="#0E0E10",
                ),
                ft.Column(
                    [
                        ft.Text("Xauto", size=26, weight=ft.FontWeight.W_700, color=theme.TEXT),
                        ft.Text(t("app.subtitle"), size=13, color=theme.TEXT_MUTED),
                    ],
                    spacing=0,
                ),
            ],
            spacing=14,
        )
        actions = ft.Row(
            [
                ft.TextButton(t("lang.switch"), on_click=lambda _: self.shell.toggle_language(),
                              style=ft.ButtonStyle(color=theme.TEXT_MUTED)),
                ft.IconButton(ft.Icons.REFRESH_ROUNDED, icon_color=theme.TEXT_MUTED, tooltip=t("home.refresh"),
                              on_click=lambda _: run_in_background(self._sync_profiles)),
                theme.primary_button(t("home.add"), ft.Icons.ADD_ROUNDED, on_click=lambda _: self._add_account()),
            ],
            spacing=6,
        )
        return ft.Row([brand, actions], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

    @staticmethod
    def _stat(value: str, label: str, accent: str | None = None) -> ft.Control:
        return ft.Container(
            content=ft.Row(
                [
                    ft.Text(value, size=18, weight=ft.FontWeight.W_700, color=accent or theme.TEXT),
                    ft.Text(label, size=13, color=theme.TEXT_MUTED),
                ],
                spacing=8,
                tight=True,
            ),
            padding=ft.Padding.symmetric(horizontal=16, vertical=10),
            bgcolor=theme.SURFACE,
            border=theme.border(),
            border_radius=40,
            blur=ft.Blur(10, 10),
        )

    def _adspower_pill(self) -> ft.Control:
        color = theme.OK if self._adspower_online else theme.DANGER
        label = t("stats.adspower.on") if self._adspower_online else t("stats.adspower.off")
        return ft.Container(
            content=ft.Row(
                [
                    ft.Container(width=8, height=8, border_radius=4, bgcolor=color,
                                 shadow=ft.BoxShadow(blur_radius=8, color=color)),
                    ft.Text(label, size=13, color=theme.TEXT_MUTED),
                ],
                spacing=10,
                tight=True,
            ),
            padding=ft.Padding.symmetric(horizontal=16, vertical=13),
            bgcolor=theme.SURFACE,
            border=theme.border(),
            border_radius=40,
        )

    @staticmethod
    def _empty_state() -> ft.Control:
        return theme.glass(
            ft.Column(
                [
                    ft.Icon(ft.Icons.PERSON_ADD_ALT_1_OUTLINED, size=40, color=theme.TEXT_MUTED),
                    ft.Text(t("home.empty.title"), size=18, color=theme.TEXT, weight=ft.FontWeight.W_600),
                    ft.Text(t("home.empty.hint"), size=13, color=theme.TEXT_MUTED, text_align=ft.TextAlign.CENTER),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=10,
            ),
            padding=48,
            col=12,
        )

    # --- Actions ------------------------------------------------------------

    def _add_account(self) -> None:
        handles = {a.handle for a in self.accounts_repo.load()}
        self.page.show_dialog(AccountDialog(None, handles, on_submit=self._save_account))

    def _edit_account(self, account: Account) -> None:
        handles = {a.handle for a in self.accounts_repo.load()}
        self.page.show_dialog(AccountDialog(account, handles, on_submit=self._save_account))

    def _save_account(self, account: Account) -> None:
        self.accounts_repo.upsert(account)
        self.refresh()
        show_toast(self.page, t("toast.saved", handle=account.at_handle))
        # Name / avatar are fetched in the background so the dialog closes instantly.
        run_in_background(lambda: self._enrich(account))

    def _confirm_delete(self, account: Account) -> None:
        def delete(acc: Account) -> None:
            self.accounts_repo.delete(acc.id)
            self.refresh()
            show_toast(self.page, t("toast.deleted", handle=acc.at_handle))

        self.page.show_dialog(ConfirmDeleteDialog(account, on_confirm=delete))

    def _open_account(self, account: Account) -> None:
        card = next((c for c in self._grid.controls if isinstance(c, AccountCard) and c.account.id == account.id), None)

        def work() -> None:
            try:
                self.adspower.open_url(account.adspower_id, account.profile_url)
                show_toast(self.page, t("card.opened", handle=account.at_handle))
            except AdsPowerError as exc:
                show_toast(self.page, f"AdsPower: {exc}", error=True)
            except Exception as exc:  # network hiccups with the browser's devtools port
                show_toast(self.page, f"{type(exc).__name__}: {exc}", error=True)
            finally:
                if card and card.page:
                    card.set_busy(False)

        show_toast(self.page, t("card.opening", handle=account.at_handle))
        run_in_background(work)

    # --- Background work ----------------------------------------------------

    def _sync_profiles(self) -> None:
        """Check AdsPower and fill in missing names / avatars."""
        self._adspower_online = self.adspower.is_running()
        for account in self.accounts_repo.load():
            if not account.avatar_file or not account.display_name:
                self._enrich(account, refresh=False)
        self.refresh()

    def _enrich(self, account: Account, refresh: bool = True) -> None:
        info = fetch_profile(account.handle)
        changed = False
        if info.display_name and not account.display_name:
            account.display_name, changed = info.display_name, True
        if not account.avatar_file:
            file_name = download_avatar(account.handle, info.avatar_url)
            if file_name:
                account.avatar_file, changed = file_name, True
        if changed:
            self.accounts_repo.upsert(account)
        if refresh:
            self.refresh()
