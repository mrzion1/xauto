"""Animated backdrop: soft graphite glow, a faint X mark and drifting white particles."""

from __future__ import annotations

import asyncio
import math
import random
from dataclasses import dataclass

import flet as ft
import flet.canvas as cv

from . import theme

PARTICLE_COUNT = 70
FPS = 24


@dataclass
class _Particle:
    x: float
    y: float
    radius: float
    speed: float          # px per frame, upward
    drift: float          # horizontal sway amplitude
    phase: float          # twinkle / sway offset
    shape: cv.Circle


class ParticleField(cv.Canvas):
    """Canvas with slow upward-floating dots that twinkle.

    The animation loop runs as a page task and stops by itself once the
    control is removed from the page.
    """

    def __init__(self) -> None:
        super().__init__(expand=True, on_resize=self._on_resize)
        self._width = 1280.0
        self._height = 800.0
        self._tick = 0
        self._particles = [self._spawn(initial=True) for _ in range(PARTICLE_COUNT)]
        self.shapes = [p.shape for p in self._particles]

    # --- Lifecycle ----------------------------------------------------------

    def did_mount(self) -> None:
        self._running = True
        self.page.run_task(self._loop)

    def will_unmount(self) -> None:
        self._running = False

    def _on_resize(self, e: cv.CanvasResizeEvent) -> None:
        self._width, self._height = e.width, e.height

    # --- Simulation ---------------------------------------------------------

    def _spawn(self, initial: bool = False) -> _Particle:
        radius = random.choice((0.8, 1.0, 1.2, 1.5, 2.0))
        x = random.uniform(0, self._width)
        # On start fill the whole screen; afterwards respawn just below the bottom edge.
        y = random.uniform(0, self._height) if initial else self._height + 10
        particle = _Particle(
            x=x,
            y=y,
            radius=radius,
            speed=random.uniform(0.15, 0.55) * radius,
            drift=random.uniform(0.2, 0.8),
            phase=random.uniform(0, math.tau),
            shape=cv.Circle(x, y, radius, paint=ft.Paint(color="#00FFFFFF")),
        )
        return particle

    def _step(self) -> None:
        self._tick += 1
        for index, p in enumerate(self._particles):
            p.y -= p.speed
            p.x += math.sin(self._tick / 60 + p.phase) * p.drift * 0.3

            if p.y < -10 or p.x < -10 or p.x > self._width + 10:
                fresh = self._spawn()
                fresh.shape = p.shape            # reuse the existing canvas shape
                self._particles[index] = p = fresh

            # Twinkle: alpha oscillates between ~15% and ~75%.
            alpha = int(40 + 150 * (0.5 + 0.5 * math.sin(self._tick / 25 + p.phase)))
            p.shape.x, p.shape.y, p.shape.radius = p.x, p.y, p.radius
            p.shape.paint = ft.Paint(color=f"#{alpha:02X}FFFFFF")

    async def _loop(self) -> None:
        delay = 1 / FPS
        while self._running:
            self._step()
            try:
                self.update()
            except Exception:
                break  # page closed
            await asyncio.sleep(delay)


def build_background() -> ft.Control:
    """Full-window layer that sits under all page content."""
    glow = ft.Container(
        expand=True,
        gradient=ft.RadialGradient(
            center=ft.Alignment(0, -0.6),
            radius=1.2,
            colors=["#1E1E23", "#0C0C0E", theme.BG],
            stops=[0.0, 0.45, 1.0],
        ),
    )
    logo = ft.Container(
        expand=True,
        alignment=ft.Alignment(0.55, 0.15),
        content=ft.Image(src="x_logo.svg", width=560, height=560, opacity=0.05),
    )
    vignette = ft.Container(
        expand=True,
        gradient=ft.LinearGradient(
            begin=ft.Alignment(0, -1),
            end=ft.Alignment(0, 1),
            colors=["#00000000", "#00000000", "#AA000000"],
            stops=[0.0, 0.6, 1.0],
        ),
    )
    return ft.Stack([glow, logo, ParticleField(), vignette], expand=True)
