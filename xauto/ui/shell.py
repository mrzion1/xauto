"""Root layout and screen navigation.

The window is a Stack: the animated background at the bottom and exactly one
screen on top. Navigating swaps that top layer, so the particles keep running.
"""

from __future__ import annotations

import flet as ft

from ..config import Settings
from ..i18n import get_language, set_language
from ..models import Account
from .background import build_background


class Shell:
    def __init__(self, page: ft.Page, settings: Settings) -> None:
        self.page = page
        self.settings = settings
        self._stack = ft.Stack([self._stretch(build_background())], expand=True)
        page.add(self._stack)

    # --- Navigation ---------------------------------------------------------

    def show_home(self) -> None:
        from .home import HomeView  # local import: screens import Shell for type hints

        self._show(HomeView(self))

    def show_posts(self, account: Account) -> None:
        from .posts import PostsView

        self._show(PostsView(self, account))

    def toggle_language(self) -> None:
        self.settings.language = "en" if get_language() == "ru" else "ru"
        self.settings.save()
        set_language(self.settings.language)
        self.show_home()

    # --- Internals ----------------------------------------------------------

    def _show(self, view: ft.Control) -> None:
        layers = self._stack.controls
        if len(layers) > 1:
            layers.pop()
        layers.append(self._stretch(view))
        self.page.update()

    @staticmethod
    def _stretch(control: ft.Control) -> ft.Control:
        control.left = control.top = control.right = control.bottom = 0
        return control
