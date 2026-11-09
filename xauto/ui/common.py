"""Small helpers shared by several screens."""

from __future__ import annotations

import asyncio
import threading
from pathlib import Path
from typing import Callable

import flet as ft

from ..config import AVATARS_DIR
from ..models import Account
from . import theme
from .formatting import initials


def run_in_background(fn: Callable[[], None]) -> None:
    """Run slow work (network, ffmpeg, AdsPower) off the UI thread."""
    threading.Thread(target=fn, daemon=True).start()


def show_toast(page: ft.Page | None, message: str, error: bool = False) -> None:
    if page is None:
        return
    page.show_dialog(
        ft.SnackBar(
            ft.Text(message, color=theme.TEXT if error else theme.ON_ACCENT),
            bgcolor="#5A1F22" if error else theme.ACCENT,
            behavior=ft.SnackBarBehavior.FLOATING,
            width=420,
            duration=3000,
        )
    )


async def watch_file(path: Path, is_running: Callable[[], bool], on_change: Callable[[], None],
                     interval_s: float = 3) -> None:
    """Call ``on_change`` whenever the file's mtime changes (external edits, CLI, Claude)."""
    last = path.stat().st_mtime if path.exists() else 0.0
    while is_running():
        await asyncio.sleep(interval_s)
        current = path.stat().st_mtime if path.exists() else 0.0
        if current != last:
            last = current
            on_change()


def account_avatar(account: Account, radius: int = 26) -> ft.Control:
    """Round avatar with a thin ring; shows initials when there is no picture."""
    path = AVATARS_DIR / account.avatar_file if account.avatar_file else None
    image = path.read_bytes() if path and path.exists() else None
    return ft.Container(
        content=ft.CircleAvatar(
            foreground_image_src=image,
            content=ft.Text(initials(account.display_name or account.handle), color=theme.TEXT, size=radius * 0.6),
            bgcolor="#26262C",
            radius=radius,
        ),
        border=theme.border("#40FFFFFF", 1.5),
        border_radius=radius + 4,
        padding=2,
    )
