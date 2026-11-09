"""Round-trip and parsing rules for the on-disk models."""

from datetime import datetime, timedelta, timezone

import pytest

from xauto.models import Account, Post, PostStatus, TelegramStatus, normalize_handle


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("@SonicDrip", "sonicdrip"),
        ("sonicdrip", "sonicdrip"),
        ("  @name  ", "name"),
        ("https://x.com/Name", "name"),
        ("https://twitter.com/name/status/123", "name"),
        ("x.com/name?s=21", "name"),
    ],
)
def test_normalize_handle(raw, expected):
    assert normalize_handle(raw) == expected


def test_account_round_trip():
    account = Account(handle="demo", adspower_id="k1abc", display_name="Demo")
    restored = Account.from_dict(account.to_dict())
    assert restored == account
    assert restored.at_handle == "@demo"
    assert restored.profile_url == "https://x.com/demo"


def test_post_round_trip_keeps_timezone():
    when = datetime(2026, 11, 10, 14, 0, tzinfo=timezone(timedelta(hours=3)))
    post = Post(account="demo", scheduled_at=when, text="gm", media=["a.png"])
    restored = Post.from_dict(post.to_dict())

    assert restored.scheduled_at == when
    assert restored.media == ["a.png"]
    assert restored.status is PostStatus.DRAFT
    assert restored.telegram is TelegramStatus.PENDING


def test_post_naive_datetime_becomes_local_aware():
    post = Post.from_dict({"account": "@Demo", "scheduled_at": "2026-11-10T14:00", "text": "gm"})
    assert post.scheduled_at.tzinfo is not None
    assert post.account == "demo"


def test_post_rejects_unknown_status():
    with pytest.raises(ValueError):
        Post.from_dict({"account": "demo", "scheduled_at": "2026-11-10T14:00", "text": "", "status": "nope"})
