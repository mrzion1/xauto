"""Screenshot of the whole desktop (all monitors) for the remote /screen command."""

from __future__ import annotations

import io

from PIL import ImageGrab

# Telegram photos: max 10 MB and width + height <= 10000. JPEG keeps it small and fast.
MAX_SIDE = 3840
JPEG_QUALITY = 85


class ScreenError(RuntimeError):
    pass


def capture_jpeg() -> bytes:
    try:
        image = ImageGrab.grab(all_screens=True)
    except OSError as exc:  # locked screen / no interactive desktop
        raise ScreenError("screen grab failed (is the PC locked?)") from exc

    image.thumbnail((MAX_SIDE, MAX_SIDE))
    buffer = io.BytesIO()
    image.convert("RGB").save(buffer, format="JPEG", quality=JPEG_QUALITY)
    return buffer.getvalue()
