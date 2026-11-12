"""Use case: when a scheduled post goes live, send its link to your Telegram bot.

It does not poll: the Windows task "Xauto notify" only has one-shot triggers
right after each scheduled post (see ``ATTEMPTS``), and ``rearm_task`` rebuilds
them whenever posts are scheduled or a check has run. If the PC was off at
posting time, Windows runs the missed check at startup and the link is marked
as late.
"""

from __future__ import annotations

import logging
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .config import Settings
from .models import Account, Post, PostStatus, TelegramStatus
from .services import win_task
from .services.adspower import AdsPowerClient, AdsPowerError
from .services.telegram_bot import TelegramBot
from .services.x_timeline import find_post_urls
from .storage import AccountRepository, QueueRepository

log = logging.getLogger(__name__)

# Checks after posting time: the first finds almost every post, the other two
# cover X publishing late. After the last one we stop and send the profile link.
ATTEMPTS = (timedelta(minutes=1), timedelta(minutes=5), timedelta(minutes=15))
# A trigger may fire a few seconds early; never look before this.
PUBLISH_GRACE = timedelta(seconds=45)
GIVE_UP_AFTER = ATTEMPTS[-1] - timedelta(minutes=1)
TASK_NAME = "Xauto notify"
# A link sent this long after posting time gets a "late" note.
LATE_AFTER = timedelta(minutes=30)


@dataclass
class NotifyReport:
    sent: int = 0
    waiting: int = 0
    gave_up: int = 0


def due_posts(posts: list[Post], now: datetime) -> list[Post]:
    """Scheduled posts whose time has passed and whose link was not sent yet."""
    return [
        p for p in posts
        if p.status in (PostStatus.SCHEDULED, PostStatus.PUBLISHED)
        and p.telegram is TelegramStatus.PENDING
        and p.scheduled_at + PUBLISH_GRACE <= now
    ]


def build_message(post: Post, url: str, now: datetime) -> str:
    first_line = post.text.strip().splitlines()[0]
    local_time = post.scheduled_at.astimezone().strftime("%d.%m %H:%M")
    lines = [f"Пост вышел · @{post.account}", "", first_line, "", url]
    if now - post.scheduled_at > LATE_AFTER:
        lines.append(f"\n(вышел в {local_time}, ссылка с опозданием: ПК был выключен)")
    return "\n".join(lines)


def build_give_up_message(post: Post) -> str:
    local_time = post.scheduled_at.astimezone().strftime("%d.%m %H:%M")
    return (f"Не нашёл пост от {local_time} на странице @{post.account}. "
            f"Проверь, вышел ли он: https://x.com/{post.account}\n\n{post.text.strip().splitlines()[0]}")


def run_notify(settings: Settings, now: datetime | None = None) -> NotifyReport:
    now = now or datetime.now(timezone.utc)
    report = NotifyReport()
    repo = QueueRepository()
    due = due_posts(repo.load(), now)
    if not due:
        return report

    bot = TelegramBot(settings.telegram_bot_token)
    if not settings.telegram_chat_id:
        raise RuntimeError("telegram_chat_id is empty: run `python -m xauto telegram-setup` first")
    accounts = {a.handle: a for a in AccountRepository().load()}

    for handle in sorted({p.account for p in due}):
        account = accounts.get(handle)
        if account is None:
            continue
        mine = [p for p in due if p.account == handle]
        urls = _lookup_urls(account, settings, mine)

        for post in mine:
            fresh = repo.get(post.id)
            if fresh is None:
                continue
            url = urls.get(post.id) or fresh.tweet_url
            if url:
                bot.send(settings.telegram_chat_id, build_message(fresh, url, now))
                fresh.status, fresh.tweet_url, fresh.telegram = PostStatus.PUBLISHED, url, TelegramStatus.SENT
                report.sent += 1
            elif now - fresh.scheduled_at >= GIVE_UP_AFTER:
                bot.send(settings.telegram_chat_id, build_give_up_message(fresh))
                fresh.telegram = TelegramStatus.MISSED
                report.gave_up += 1
            else:
                report.waiting += 1
                continue
            repo.upsert(fresh)
    return report


def _lookup_urls(account: Account, settings: Settings, posts: list[Post]) -> dict[str, str]:
    """Read the profile page; start the AdsPower profile headless if it is closed."""
    adspower = AdsPowerClient(settings.adspower_api_url, settings.adspower_api_key)
    try:
        was_open = adspower.active_session(account.adspower_id) is not None
        session = adspower.start_profile(account.adspower_id, headless=not was_open)
    except AdsPowerError as exc:
        log.warning("AdsPower unavailable for @%s: %s", account.handle, exc)
        return {}  # try again on the next run; give-up timer still applies

    try:
        return find_post_urls(session.debug_port, account.handle, {p.id: p.text for p in posts})
    except Exception as exc:  # X slow / layout change: retry next run instead of crashing the task
        log.warning("could not read @%s profile: %s: %s", account.handle, type(exc).__name__, exc)
        return {}
    finally:
        if not was_open:
            try:
                adspower.stop_profile(account.adspower_id)  # leave things as we found them
            except AdsPowerError:
                pass


def check_times(posts: list[Post], now: datetime) -> list[datetime]:
    """Future moments when a check is needed: ATTEMPTS after each post still waiting for its link."""
    waiting = [p for p in posts
               if p.status in (PostStatus.SCHEDULED, PostStatus.PUBLISHED) and p.telegram is TelegramStatus.PENDING]
    return sorted({p.scheduled_at + delay for p in waiting for delay in ATTEMPTS if p.scheduled_at + delay > now})


def rearm_task(now: datetime | None = None) -> list[datetime]:
    """Point the Windows task at the upcoming checks only; remove it when nothing is pending."""
    from .config import ROOT_DIR

    times = check_times(QueueRepository().load(), now or datetime.now(timezone.utc))
    if not times:
        win_task.remove(TASK_NAME)
        return []
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    runner = ROOT_DIR / "scripts" / "notify_task.pyw"
    win_task.install(TASK_NAME, win_task.build_xml(
        times, str(pythonw), f'"{runner}"', "Xauto: send links of scheduled posts that went live"))
    return times
