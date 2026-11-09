"""JSON-backed repositories for accounts and the post queue.

Writes are atomic (write to a temp file, then replace) so a crash or a power
cut never leaves a half-written queue behind.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import ACCOUNTS_FILE, QUEUE_FILE
from .models import Account, Post, PostStatus, normalize_handle

SCHEMA_VERSION = 1


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    text = path.read_text(encoding="utf-8").strip()
    return json.loads(text) if text else default


def _write_json_atomic(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        os.replace(tmp_name, path)
    except BaseException:
        Path(tmp_name).unlink(missing_ok=True)
        raise


# --- Accounts ----------------------------------------------------------------


class AccountRepository:
    def __init__(self, path: Path = ACCOUNTS_FILE) -> None:
        self.path = path

    def load(self) -> list[Account]:
        raw = _read_json(self.path, {"accounts": []})
        return [Account.from_dict(item) for item in raw.get("accounts", [])]

    def save(self, accounts: list[Account]) -> None:
        payload = {"schema_version": SCHEMA_VERSION, "accounts": [a.to_dict() for a in accounts]}
        _write_json_atomic(self.path, payload)

    def upsert(self, account: Account) -> None:
        accounts = self.load()
        for index, existing in enumerate(accounts):
            if existing.id == account.id:
                accounts[index] = account
                break
        else:
            accounts.append(account)
        self.save(accounts)

    def delete(self, account_id: str) -> None:
        self.save([a for a in self.load() if a.id != account_id])


# --- Queue -------------------------------------------------------------------


@dataclass(frozen=True)
class QueueSummary:
    """What an account card needs to know about its queue."""

    total: int                      # posts that are not failed
    upcoming: int                   # of them, still in the future
    last_post_at: datetime | None   # the furthest planned post

    def days_left(self, now: datetime | None = None) -> int | None:
        if self.last_post_at is None:
            return None
        now = now or datetime.now().astimezone()
        return (self.last_post_at.date() - now.date()).days


class QueueRepository:
    def __init__(self, path: Path = QUEUE_FILE) -> None:
        self.path = path

    def load(self) -> list[Post]:
        raw = _read_json(self.path, {"posts": []})
        posts = [Post.from_dict(item) for item in raw.get("posts", [])]
        return sorted(posts, key=lambda p: p.scheduled_at)

    def save(self, posts: list[Post]) -> None:
        ordered = sorted(posts, key=lambda p: p.scheduled_at)
        payload = {"schema_version": SCHEMA_VERSION, "posts": [p.to_dict() for p in ordered]}
        _write_json_atomic(self.path, payload)

    def summary_for(self, handle: str, posts: list[Post] | None = None) -> QueueSummary:
        handle = normalize_handle(handle)
        posts = self.load() if posts is None else posts
        now = datetime.now().astimezone()

        mine = [p for p in posts if p.account == handle and p.status is not PostStatus.FAILED]
        return QueueSummary(
            total=len(mine),
            upcoming=sum(1 for p in mine if p.scheduled_at > now),
            last_post_at=max((p.scheduled_at for p in mine), default=None),
        )
