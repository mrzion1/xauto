"""Application bootstrap: window setup and the root layout."""

from __future__ import annotations

import flet as ft

from . import __version__
from .config import ASSETS_DIR, Settings, ensure_dirs
from .i18n import set_language
from .ui import theme
from .ui.background import build_background
from .ui.home import HomeView


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

    # Background and content are layered; the content view is always the last child.
    background = build_background()
    content = HomeView(settings)
    for layer in (background, content):
        layer.left = layer.top = layer.right = layer.bottom = 0  # stretch each layer over the window
    page.add(ft.Stack([background, content], expand=True))


def run(web_port: int | None = None) -> None:
    """Start the desktop app (or a browser preview when ``web_port`` is given)."""
    if web_port:
        ft.run(main, assets_dir=str(ASSETS_DIR), view=None, port=web_port)
    else:
        ft.run(main, assets_dir=str(ASSETS_DIR))
