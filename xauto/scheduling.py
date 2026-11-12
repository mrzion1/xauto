"""Use case: push an account's approved posts into X's scheduler.

Shared by the CLI and the UI. Talks to AdsPower for the browser, to
``XScheduler`` for the X side, and writes every outcome back to the queue
right away, so a crash halfway never loses what was already scheduled.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Callable

from .config import Settings, post_dir
from .models import Account, PostStatus
from .services.adspower import AdsPowerClient, AdsPowerError
from .services.x_scheduler import ScheduleResult, XScheduler
from .storage import QueueRepository

log = logging.getLogger(__name__)


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

    # Background work: a closed profile is started headless (no window, no focus
    # stealing) and closed again; an open one is used as it is.
    adspower = AdsPowerClient(settings.adspower_api_url, settings.adspower_api_key)
    was_open = adspower.active_session(account.adspower_id) is not None
    session = adspower.start_profile(account.adspower_id, headless=not was_open)
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
    try:
        results = asyncio.run(scheduler.schedule_many(jobs, on_result=record))
    finally:
        if not was_open:
            try:
                adspower.stop_profile(account.adspower_id)
            except AdsPowerError:
                log.warning("could not stop the headless profile of @%s", account.handle)
    if not dry_run and any(r.ok for r in results):
        _rearm_notify()
    return results


def _rearm_notify() -> None:
    """New posts in X's scheduler need their link checks in Windows' scheduler."""
    from .notify import rearm_task

    try:
        rearm_task()
    except Exception:  # scheduling itself succeeded, so only log it
        log.exception("could not update the notify task")
