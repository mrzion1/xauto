"""Repositories: persistence, atomic writes and queue summaries."""

import json
from datetime import datetime, timedelta

from postdeck.models import Account, Post, PostStatus
from postdeck.storage import AccountRepository, QueueRepository


def _now():
    return datetime.now().astimezone()


def test_account_upsert_and_delete(tmp_path):
    repo = AccountRepository(tmp_path / "accounts.json")
    account = Account(handle="demo", adspower_id="k1")

    repo.upsert(account)
    account.display_name = "Renamed"
    repo.upsert(account)
    assert [a.display_name for a in repo.load()] == ["Renamed"]

    repo.delete(account.id)
    assert repo.load() == []


def test_missing_files_load_as_empty(tmp_path):
    assert AccountRepository(tmp_path / "nope.json").load() == []
    assert QueueRepository(tmp_path / "nope.json").load() == []


def test_atomic_write_leaves_no_temp_files(tmp_path):
    repo = QueueRepository(tmp_path / "queue.json")
    repo.save([Post(account="demo", scheduled_at=_now(), text="gm")])

    assert [p.name for p in tmp_path.iterdir()] == ["queue.json"]
    assert json.loads((tmp_path / "queue.json").read_text(encoding="utf-8"))["schema_version"] == 1


def test_queue_is_sorted_by_time(tmp_path):
    repo = QueueRepository(tmp_path / "queue.json")
    later = Post(account="demo", scheduled_at=_now() + timedelta(days=2), text="later")
    sooner = Post(account="demo", scheduled_at=_now() + timedelta(days=1), text="sooner")
    repo.save([later, sooner])
    assert [p.text for p in repo.load()] == ["sooner", "later"]


def test_summary_ignores_failed_and_other_accounts(tmp_path):
    repo = QueueRepository(tmp_path / "queue.json")
    now = _now()
    posts = [
        Post(account="demo", scheduled_at=now + timedelta(days=3), text="a"),
        Post(account="demo", scheduled_at=now - timedelta(days=1), text="past", status=PostStatus.PUBLISHED),
        Post(account="demo", scheduled_at=now + timedelta(days=9), text="x", status=PostStatus.FAILED),
        Post(account="other", scheduled_at=now + timedelta(days=20), text="b"),
    ]

    summary = repo.summary_for("@Demo", posts)

    assert summary.total == 2
    assert summary.upcoming == 1
    assert summary.days_left(now) == 3


def test_summary_for_empty_queue(tmp_path):
    summary = QueueRepository(tmp_path / "queue.json").summary_for("demo", [])
    assert summary.last_post_at is None
    assert summary.days_left() is None
