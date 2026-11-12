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
    assert due_posts([_post(0)], NOW) == []
    assert len(due_posts([_post(1)], NOW)) == 1


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


def test_match_posts_keeps_own_posts_only():
    from xauto.services.x_timeline import match_posts
    items = [
        {"text": "Mike Tyson made around $400 million", "href": "/someone/status/1"},
        {"text": "Mike Tyson made around\n$400 million", "href": "/WorkMadz/status/2"},
    ]
    found = match_posts(items, "workmadz", {"a": "Mike Tyson made around $400 million in his career"})
    assert found == {"a": "https://x.com/WorkMadz/status/2"}


def test_check_times_only_after_waiting_posts():
    from xauto.notify import ATTEMPTS, check_times

    waiting = _post(-60)                                              # in an hour
    sent = _post(-120, status=PostStatus.PUBLISHED, telegram=TelegramStatus.SENT)
    draft = _post(-180, status=PostStatus.DRAFT)
    just_posted = _post(3)                                            # 3 minutes ago: +1 min check is over

    times = check_times([waiting, sent, draft, just_posted], NOW)

    expected = [just_posted.scheduled_at + d for d in ATTEMPTS[1:]] + [waiting.scheduled_at + d for d in ATTEMPTS]
    assert times == sorted(expected)


def test_task_xml_has_one_trigger_per_time():
    from datetime import datetime, timezone
    from xauto.services.win_task import build_xml

    xml = build_xml([datetime(2026, 11, 13, 16, 45, tzinfo=timezone.utc)], r"C:\py\pythonw.exe", '"D:/x/run.pyw"')
    assert xml.count("<TimeTrigger>") == 1
    assert "<StartWhenAvailable>true</StartWhenAvailable>" in xml
    assert "&quot;" not in xml.split("<Arguments>")[0]
