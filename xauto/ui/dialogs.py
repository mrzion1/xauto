"""Modal dialogs: add / edit an account and confirm deletion."""

from __future__ import annotations

from typing import Callable

import flet as ft

from ..i18n import t
from ..models import Account, normalize_handle
from . import theme


def _field(label: str, hint: str, value: str = "", autofocus: bool = False) -> ft.TextField:
    return ft.TextField(
        label=label,
        hint_text=hint,
        value=value,
        autofocus=autofocus,
        color=theme.TEXT,
        bgcolor="#0B0B0D",
        border_color=theme.BORDER_HOVER,
        focused_border_color=theme.ACCENT,
        border_radius=theme.RADIUS_S,
        label_style=ft.TextStyle(color=theme.TEXT_MUTED),
        hint_style=ft.TextStyle(color=theme.TEXT_FAINT),
        cursor_color=theme.ACCENT,
    )


class AccountDialog(ft.AlertDialog):
    """Add a new account (``account=None``) or edit an existing one."""

    def __init__(
        self,
        account: Account | None,
        existing_handles: set[str],
        on_submit: Callable[[Account], None],
    ) -> None:
        self._account = account
        self._existing = existing_handles - ({account.handle} if account else set())
        self._on_submit = on_submit

        self._handle = _field(t("dialog.handle"), t("dialog.handle.hint"),
                              account.at_handle if account else "", autofocus=True)
        self._adspower = _field(t("dialog.adspower"), t("dialog.adspower.hint"),
                                account.adspower_id if account else "")
        self._name = _field(t("dialog.name"), t("dialog.name.hint"),
                            account.display_name if account else "")

        title = t("dialog.edit.title", handle=account.at_handle) if account else t("dialog.add.title")
        super().__init__(
            modal=True,
            bgcolor="#121215",
            shape=ft.RoundedRectangleBorder(radius=theme.RADIUS_L),
            title=ft.Text(title, color=theme.TEXT, weight=ft.FontWeight.W_600),
            content=ft.Container(
                width=420,
                content=ft.Column([self._handle, self._adspower, self._name], spacing=14, tight=True),
            ),
            actions=[
                ft.TextButton(t("dialog.cancel"), on_click=lambda _: self._close(),
                              style=ft.ButtonStyle(color=theme.TEXT_MUTED)),
                theme.primary_button(t("dialog.save"), on_click=lambda _: self._submit()),
            ],
        )

    def _close(self) -> None:
        self.page.pop_dialog()

    def _submit(self) -> None:
        handle = normalize_handle(self._handle.value or "")
        adspower_id = (self._adspower.value or "").strip()

        # Validate in place, next to the field that is wrong.
        self._handle.error = None
        self._adspower.error = None
        if not handle:
            self._handle.error = t("dialog.required")
        elif handle in self._existing:
            self._handle.error = t("dialog.duplicate")
        if not adspower_id:
            self._adspower.error = t("dialog.required")
        if self._handle.error or self._adspower.error:
            self.update()
            return

        account = self._account or Account(handle=handle, adspower_id=adspower_id)
        handle_changed = account.handle != handle
        account.handle = handle
        account.adspower_id = adspower_id
        account.display_name = (self._name.value or "").strip()
        if handle_changed:
            account.avatar_file = ""  # force a fresh avatar for the new handle

        self._close()
        self._on_submit(account)


class ConfirmDeleteDialog(ft.AlertDialog):
    def __init__(self, account: Account, on_confirm: Callable[[Account], None]) -> None:
        def confirm(_):
            self.page.pop_dialog()
            on_confirm(account)

        super().__init__(
            modal=True,
            bgcolor="#121215",
            shape=ft.RoundedRectangleBorder(radius=theme.RADIUS_L),
            title=ft.Text(t("dialog.delete.title", handle=account.at_handle), color=theme.TEXT),
            content=ft.Text(t("dialog.delete.body"), color=theme.TEXT_MUTED, width=380),
            actions=[
                ft.TextButton(t("dialog.cancel"), on_click=lambda _: self.page.pop_dialog(),
                              style=ft.ButtonStyle(color=theme.TEXT_MUTED)),
                ft.Button(t("dialog.delete.confirm"), on_click=confirm, bgcolor=theme.DANGER, color=theme.ON_ACCENT),
            ],
        )
