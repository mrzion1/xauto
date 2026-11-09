"""Pure parts of the Telegram notification flow."""

from datetime import datetime, timedelta, timezone

from xauto.models import Post, PostStatus, TelegramStatus
from xauto.notify import build_message, due_posts
from xauto.services.x_timeline import same_post

NOW = datetime(2026, 11, 10, 17, 0, tzinfo=timezone.utc)


def _post(minutes_ago: int, **kw) -> Post:
    base = dict(account="demo", scheduled_at=NOW - timedelta(minutes=minutes_ago), text="Hook line\n\nbody",
                status=PostStatus.SCHEDULED)
    base.update(kw)
    return Post(**base)


def test_due_posts_waits_for_grace_period():
    assert due_posts([_post(1)], NOW) == []
    assert len(due_posts([_post(5)], NOW)) == 1


def test_due_posts_skips_sent_off_and_unscheduled():
    posts = [
        _post(5, telegram=TelegramStatus.SENT),
        _post(5, telegram=TelegramStatus.OFF),
        _post(5, status=PostStatus.APPROVED),   # never handed to X
        _post(-60),                             # still in the future
    ]
    assert due_posts(posts, NOW) == []


def test_message_has_hook_and_link():
    text = build_message(_post(5), "https://x.com/demo/status/1", NOW)
    assert "Hook line" in text and "https://x.com/demo/status/1" in text
    assert "опозданием" not in text


def test_late_message_is_marked():
    assert "опозданием" in build_message(_post(120), "https://x.com/demo/status/1", NOW)


def test_same_post_ignores_line_breaks_and_truncation():
    queued = "Barbara Corcoran borrowed $1,000.\n\nIn the video below, she tells the story herself. " * 3
    shown = "Barbara Corcoran borrowed $1,000. In the video below, she tells"   # cut by "Show more"
    assert same_post(shown, queued)


def test_same_post_rejects_other_text():
    assert not same_post("Mike Tyson made $400 million", "Barbara Corcoran borrowed $1,000")
    assert not same_post("", "anything")
