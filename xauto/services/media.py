"""Helpers for post attachments: type detection, thumbnails, opening files."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".webm"}

THUMB_SUFFIX = ".thumb.jpg"


def is_image(path: Path) -> bool:
    return path.suffix.lower() in IMAGE_EXTENSIONS


def is_video(path: Path) -> bool:
    return path.suffix.lower() in VIDEO_EXTENSIONS


def thumbnail_for(path: Path) -> Path | None:
    """Preview image for an attachment.

    Images are their own preview. For videos a frame is grabbed once with
    ffmpeg and cached next to the file; returns None if ffmpeg is missing.
    """
    if is_image(path):
        return path if path.exists() else None
    if not is_video(path) or not path.exists():
        return None

    thumb = path.with_name(path.name + THUMB_SUFFIX)
    if thumb.exists() and thumb.stat().st_mtime >= path.stat().st_mtime:
        return thumb

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return None

    # A frame ~1s in avoids black intro frames; scale keeps the cache small.
    result = subprocess.run(
        [ffmpeg, "-y", "-loglevel", "error", "-ss", "1", "-i", str(path),
         "-frames:v", "1", "-vf", "scale=960:-2", str(thumb)],
        capture_output=True,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    return thumb if result.returncode == 0 and thumb.exists() else None


def video_duration(path: Path) -> float | None:
    """Duration in seconds via ffprobe, or None if unknown."""
    ffprobe = shutil.which("ffprobe")
    if not ffprobe or not path.exists():
        return None
    result = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)],
        capture_output=True,
        text=True,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    try:
        return float(result.stdout.strip())
    except ValueError:
        return None


def open_in_system(path: Path) -> None:
    """Open a file or folder with the default Windows application."""
    os.startfile(str(path))  # noqa: S606 - local, user-initiated
