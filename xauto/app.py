"""Application bootstrap: window setup and the root layout."""

from __future__ import annotations

import flet as ft

from . import __version__
from .config import ASSETS_DIR, Settings, ensure_dirs
from .i18n import set_language
from .ui import theme
from .ui.shell import Shell


def main(page: ft.Page) -> None:
    ensure_dirs()
    settings = Settings.load()
    set_language(settings.language)

    page.title = f"Xauto {__version__}"
    page.window.icon = str(ASSETS_DIR / "icon.ico")  # replaces the default Flet icon in the title bar / taskbar
    page.theme_mode = ft.ThemeMode.DARK
    page.theme = theme.app_theme()
    page.dark_theme = theme.app_theme()
    page.bgcolor = theme.BG
    page.padding = 0
    page.window.width = 1180
    page.window.height = 800
    page.window.min_width = 520
    page.window.min_height = 560

    Shell(page, settings).show_home()


def run() -> None:
    ft.run(main, assets_dir=str(ASSETS_DIR))
