"""Design tokens: a monochrome black / graphite palette with white accents."""

from __future__ import annotations

import flet as ft

# --- Palette -----------------------------------------------------------------

BG = "#050506"
SURFACE = "#CC111114"          # translucent so the particle field shows through
SURFACE_HOVER = "#E61A1A1F"
BORDER = "#22FFFFFF"
BORDER_HOVER = "#55FFFFFF"

TEXT = "#F4F4F5"
TEXT_MUTED = "#8B8B94"
TEXT_FAINT = "#5A5A62"

ACCENT = "#FFFFFF"
ON_ACCENT = "#050506"

OK = "#8BE3B0"
WARN = "#F2C46D"
DANGER = "#FF7A7A"

# --- Shape -------------------------------------------------------------------

RADIUS_L = 20
RADIUS_M = 14
RADIUS_S = 10

FONT = "Segoe UI"
FONT_MONO = "Consolas"


def border(color: str = BORDER, width: float = 1) -> ft.Border:
    return ft.Border.all(width, color)


def glass(content: ft.Control, **kwargs) -> ft.Container:
    """Frosted panel used for cards, headers and dialogs."""
    defaults = dict(
        bgcolor=SURFACE,
        border=border(),
        border_radius=RADIUS_L,
        padding=20,
        blur=ft.Blur(12, 12),
    )
    defaults.update(kwargs)
    return ft.Container(content=content, **defaults)


def primary_button(label: str, icon: ft.IconData | None = None, on_click=None) -> ft.Button:
    return ft.Button(
        label,
        icon=icon,
        on_click=on_click,
        bgcolor=ACCENT,
        color=ON_ACCENT,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=RADIUS_S), padding=ft.Padding.symmetric(horizontal=18, vertical=14)),
    )


def ghost_button(label: str, icon: ft.IconData | None = None, on_click=None) -> ft.OutlinedButton:
    return ft.OutlinedButton(
        label,
        icon=icon,
        on_click=on_click,
        style=ft.ButtonStyle(
            color=TEXT,
            side=ft.BorderSide(1, BORDER_HOVER),
            shape=ft.RoundedRectangleBorder(radius=RADIUS_S),
            padding=ft.Padding.symmetric(horizontal=18, vertical=14),
        ),
    )


def app_theme() -> ft.Theme:
    return ft.Theme(
        font_family=FONT,
        color_scheme=ft.ColorScheme(primary=ACCENT, on_primary=ON_ACCENT, surface=BG, on_surface=TEXT),
    )
