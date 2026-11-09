"""Filesystem layout and user settings.

Everything personal (accounts, AdsPower profile IDs, API keys, avatars, the post
queue) lives under ``data/`` or in ``config/settings.json``. Both are git-ignored,
so the repository itself never carries private information.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import asdict, dataclass, fields
from pathlib import Path

# --- Paths -------------------------------------------------------------------

ROOT_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = ROOT_DIR / "assets"
CONFIG_DIR = ROOT_DIR / "config"
DATA_DIR = ROOT_DIR / "data"

SETTINGS_FILE = CONFIG_DIR / "settings.json"
SETTINGS_EXAMPLE_FILE = CONFIG_DIR / "settings.example.json"

ACCOUNTS_FILE = DATA_DIR / "accounts.json"
QUEUE_FILE = DATA_DIR / "queue.json"
AVATARS_DIR = DATA_DIR / "avatars"
MEDIA_DIR = DATA_DIR / "media"


def ensure_dirs() -> None:
    """Create the private runtime folders on first launch."""
    for folder in (DATA_DIR, AVATARS_DIR, MEDIA_DIR):
        folder.mkdir(parents=True, exist_ok=True)


# --- Settings ----------------------------------------------------------------


@dataclass
class Settings:
    """User-level settings, stored in ``config/settings.json``."""

    language: str = "ru"
    adspower_api_url: str = "http://127.0.0.1:50325"
    adspower_api_key: str = ""
    # Card turns yellow when the queue runs out within this many days.
    refill_warning_days: int = 2

    @classmethod
    def load(cls) -> "Settings":
        # First launch: start from the committed example instead of failing.
        if not SETTINGS_FILE.exists() and SETTINGS_EXAMPLE_FILE.exists():
            shutil.copyfile(SETTINGS_EXAMPLE_FILE, SETTINGS_FILE)

        if not SETTINGS_FILE.exists():
            return cls()

        try:
            raw = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return cls()  # a broken settings file should not block the app from starting
        known = {f.name for f in fields(cls)}
        # Unknown keys are ignored so older/newer settings files never crash the app.
        return cls(**{k: v for k, v in raw.items() if k in known})

    def save(self) -> None:
        SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        SETTINGS_FILE.write_text(json.dumps(asdict(self), indent=2, ensure_ascii=False), encoding="utf-8")
