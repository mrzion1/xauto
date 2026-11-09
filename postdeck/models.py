"""Domain models: accounts and queued posts.

Models are plain dataclasses with explicit ``to_dict`` / ``from_dict`` so the
on-disk JSON format stays stable and readable by humans (and by Claude, who
fills the queue file).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


def new_id() -> str:
    """Short random id, good enough for a local single-user store."""
    return uuid.uuid4().hex[:10]


def normalize_handle(handle: str) -> str:
    """'@Name', 'name', 'https://x.com/name' -> 'name' (lowercase, no @)."""
    value = handle.strip()
    for prefix in ("https://", "http://", "www.", "x.com/", "twitter.com/"):
        if value.lower().startswith(prefix):
            value = value[len(prefix):]
    return value.strip("@/ ").split("/")[0].split("?")[0].lower()


# --- Account -----------------------------------------------------------------


@dataclass
class Account:
    """One X account bound to one AdsPower browser profile."""

    handle: str                 # without '@'
    adspower_id: str            # AdsPower profile id (the "ID" column in AdsPower)
    display_name: str = ""
    avatar_file: str = ""       # file name inside data/avatars/
    id: str = field(default_factory=new_id)

    @property
    def at_handle(self) -> str:
        return f"@{self.handle}"

    @property
    def profile_url(self) -> str:
        return f"https://x.com/{self.handle}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "handle": self.handle,
            "display_name": self.display_name,
            "adspower_id": self.adspower_id,
            "avatar_file": self.avatar_file,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "Account":
        return cls(
            id=raw.get("id") or new_id(),
            handle=normalize_handle(raw.get("handle", "")),
            display_name=raw.get("display_name", ""),
            adspower_id=raw.get("adspower_id", ""),
            avatar_file=raw.get("avatar_file", ""),
        )


# --- Post --------------------------------------------------------------------


class PostStatus(str, Enum):
    DRAFT = "draft"             # written, waiting for the user's review
    APPROVED = "approved"       # approved, waiting to be pushed to X's scheduler
    SCHEDULED = "scheduled"     # sits in X's native scheduler
    PUBLISHED = "published"     # live on X (tweet_url is known)
    FAILED = "failed"           # something went wrong, see `error`


class TelegramStatus(str, Enum):
    PENDING = "pending"         # will be sent to chats after the post goes live
    SENT = "sent"
    MISSED = "missed"           # PC was off when the post went live
    SKIPPED = "skipped"         # user decided not to send it
    OFF = "off"                 # this post is not shared to chats at all


@dataclass
class Post:
    """A single queued post. See docs/QUEUE_FORMAT.md for the JSON schema."""

    account: str                    # account handle, without '@'
    scheduled_at: datetime          # timezone-aware
    text: str
    media: list[str] = field(default_factory=list)   # file names inside data/media/
    status: PostStatus = PostStatus.DRAFT
    telegram: TelegramStatus = TelegramStatus.PENDING
    tweet_url: str = ""
    error: str = ""
    id: str = field(default_factory=new_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "account": self.account,
            "scheduled_at": self.scheduled_at.isoformat(timespec="minutes"),
            "text": self.text,
            "media": list(self.media),
            "status": self.status.value,
            "telegram": self.telegram.value,
            "tweet_url": self.tweet_url,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "Post":
        scheduled = datetime.fromisoformat(raw["scheduled_at"])
        if scheduled.tzinfo is None:
            # Naive timestamps are treated as local time of this PC.
            scheduled = scheduled.astimezone()
        return cls(
            id=raw.get("id") or new_id(),
            account=normalize_handle(raw["account"]),
            scheduled_at=scheduled,
            text=raw.get("text", ""),
            media=list(raw.get("media", [])),
            status=PostStatus(raw.get("status", PostStatus.DRAFT.value)),
            telegram=TelegramStatus(raw.get("telegram", TelegramStatus.PENDING.value)),
            tweet_url=raw.get("tweet_url", ""),
            error=raw.get("error", ""),
        )
