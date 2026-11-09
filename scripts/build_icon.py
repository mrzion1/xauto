"""Render the app icon (white X mark on a black tile) into assets/.

    python scripts/build_icon.py

Produces ``assets/icon.png`` (512px) and ``assets/icon.ico`` (16-256px) using
only Pillow. The X mark is made of straight segments, so its SVG path is
parsed here directly instead of pulling in an SVG renderer.
"""

from __future__ import annotations

import re
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"

# Same path as assets/x_logo.svg (24x24 viewBox).
X_PATH = (
    "M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68"
    "l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"
)

SIZE = 1024              # draw big, downscale later for smooth edges
TILE_COLOR = (8, 8, 9, 255)
BORDER_COLOR = (58, 58, 64, 255)
MARK_COLOR = (255, 255, 255, 255)
MARK_SCALE = 0.56        # share of the tile taken by the X mark


def parse_path(d: str) -> list[list[tuple[float, float]]]:
    """Parse an SVG path made only of M/m, L/l, H/h and Z/z into polygons."""
    tokens = re.findall(r"[MmLlHhZz]|-?\d*\.?\d+", d)
    polygons: list[list[tuple[float, float]]] = []
    current: list[tuple[float, float]] = []
    x = y = 0.0
    command = ""
    i = 0

    while i < len(tokens):
        token = tokens[i]
        if token.isalpha():
            command = token
            i += 1
            if command in "Zz":
                polygons.append(current)
                x, y = current[0]
                current = []
            continue

        if command in "Mm":
            dx, dy = float(tokens[i]), float(tokens[i + 1])
            x, y = (x + dx, y + dy) if command == "m" else (dx, dy)
            current = [(x, y)]
            command = "l" if command == "m" else "L"  # implicit lineto after moveto
            i += 2
        elif command in "Ll":
            dx, dy = float(tokens[i]), float(tokens[i + 1])
            x, y = (x + dx, y + dy) if command == "l" else (dx, dy)
            current.append((x, y))
            i += 2
        elif command in "Hh":
            value = float(tokens[i])
            x = x + value if command == "h" else value
            current.append((x, y))
            i += 1
        else:
            raise ValueError(f"Unsupported path command: {command!r}")

    return polygons


def render(size: int = SIZE) -> Image.Image:
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    # Rounded black tile with a hairline border so it stays visible on dark taskbars.
    radius = int(size * 0.22)
    inset = int(size * 0.02)
    draw.rounded_rectangle((inset, inset, size - inset, size - inset), radius, fill=BORDER_COLOR)
    border = max(2, size // 128)
    draw.rounded_rectangle(
        (inset + border, inset + border, size - inset - border, size - inset - border),
        radius - border,
        fill=TILE_COLOR,
    )

    # Center the 24x24 mark inside the tile.
    scale = size * MARK_SCALE / 24
    offset = (size - 24 * scale) / 2
    outer, hole = parse_path(X_PATH)
    to_px = lambda pts: [(offset + px * scale, offset + py * scale) for px, py in pts]  # noqa: E731
    draw.polygon(to_px(outer), fill=MARK_COLOR)
    draw.polygon(to_px(hole), fill=TILE_COLOR)  # the thin inner stroke is a cut-out
    return image


def main() -> None:
    big = render()
    png = big.resize((512, 512), Image.LANCZOS)
    png.save(ASSETS / "icon.png")
    big.resize((256, 256), Image.LANCZOS).save(
        ASSETS / "icon.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    )
    print(f"icon written to {ASSETS}")


if __name__ == "__main__":
    main()
