"""Public X profile lookup (display name + avatar) without logging in.

Primary source is the FxTwitter API; if it has nothing for the handle we fall
back to unavatar.io for the picture only. Both are public, read-only services,
so no account cookies ever leave the AdsPower profile.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import requests

from ..config import AVATARS_DIR

_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) postdeck"}
_TIMEOUT_S = 15


@dataclass(frozen=True)
class ProfileInfo:
    display_name: str
    avatar_url: str


def fetch_profile(handle: str) -> ProfileInfo:
    """Best-effort lookup; returns empty fields instead of raising."""
    name, avatar = "", ""

    try:
        body = requests.get(f"https://api.fxtwitter.com/{handle}", headers=_HEADERS, timeout=_TIMEOUT_S).json()
        user = body.get("user") or {}
        name = user.get("name", "")
        # "_normal" is 48px; "_400x400" looks sharp on the cards.
        avatar = (user.get("avatar_url") or "").replace("_normal.", "_400x400.")
    except (requests.RequestException, ValueError):
        pass

    if not avatar:
        try:
            body = requests.get(f"https://unavatar.io/x/{handle}?json", headers=_HEADERS, timeout=_TIMEOUT_S).json()
            avatar = body.get("url") or ""
        except (requests.RequestException, ValueError):
            pass

    return ProfileInfo(display_name=name, avatar_url=avatar)


def download_avatar(handle: str, url: str) -> str:
    """Save the avatar into data/avatars/ and return the file name ('' on failure)."""
    if not url:
        return ""
    try:
        response = requests.get(url, headers=_HEADERS, timeout=_TIMEOUT_S)
        response.raise_for_status()
    except requests.RequestException:
        return ""

    suffix = Path(url.split("?")[0]).suffix or ".jpg"
    file_name = f"{handle}{suffix}"
    AVATARS_DIR.mkdir(parents=True, exist_ok=True)
    (AVATARS_DIR / file_name).write_bytes(response.content)
    return file_name
