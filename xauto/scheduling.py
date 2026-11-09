"""Use case: push an account's approved posts into X's scheduler.

Shared by the CLI and the UI. Talks to AdsPower for the browser, to
``XScheduler`` for the X side, and writes every outcome back to the queue
right away, so a crash halfway never loses what was already scheduled.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Callable

from .config import Settings, post_dir
from .models import Account, PostStatus
from .services.adspower import AdsPowerClient
from .services.x_scheduler import ScheduleResult, XScheduler
from .storage import QueueRepository


def pending_posts(handle: str, repo: QueueRepository | None = None, post_ids: set[str] | None = None):
    """Approved posts of the account that are still in the future, oldest first."""
    repo = repo or QueueRepository()
    now = datetime.now(timezone.utc)
    return [
        p for p in repo.for_account(handle)
        if p.status is PostStatus.APPROVED and p.scheduled_at > now and (not post_ids or p.id in post_ids)
    ]


def schedule_account(
    account: Account,
    settings: Settings,
    dry_run: bool = False,
    post_ids: set[str] | None = None,
    on_result: Callable[[ScheduleResult], None] | None = None,
) -> list[ScheduleResult]:
    """Blocking entry point (run it in a background thread from the UI)."""
    repo = QueueRepository()
    posts = pending_posts(account.handle, repo, post_ids)
    if not posts:
        return []

    session = AdsPowerClient(settings.adspower_api_url, settings.adspower_api_key).start_profile(account.adspower_id)
    jobs = [(p, [post_dir(p.id) / name for name in p.media], post_dir(p.id)) for p in posts]

    def record(result: ScheduleResult) -> None:
        # Persist each outcome immediately; dry runs never change the queue.
        if not result.dry_run:
            fresh = repo.get(result.post_id)
            if fresh is not None:
                if result.ok:
                    fresh.status = PostStatus.SCHEDULED
                    fresh.scheduled_id = result.scheduled_id
                    fresh.error = ""
                else:
                    fresh.status = PostStatus.FAILED
                    fresh.error = result.message
                repo.upsert(fresh)
        if on_result:
            on_result(result)

    scheduler = XScheduler(session.debug_port, dry_run=dry_run)
    return asyncio.run(scheduler.schedule_many(jobs, on_result=record))
