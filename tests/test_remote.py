from datetime import datetime, timedelta, timezone

import pytest

from xauto import remote
from xauto.remote import RemoteControl, parse_command
from xauto.services.claude_session import SessionError
from xauto.services.screen import ScreenError
from xauto.services.telegram_bot import TelegramError

NOW = datetime(2026, 11, 10, 17, 0, tzinfo=timezone.utc)
ME = "111"


class FakeBot:
    def __init__(self):
        self.texts, self.photos = [], []

    def send(self, chat_id, text):
        self.texts.append((chat_id, text))

    def send_photo(self, chat_id, image, caption=""):
        self.photos.append((chat_id, image))


class FakeSession:
    def __init__(self, running=False, fail=False):
        self.running, self.fail, self.starts, self.stops = running, fail, 0, 0

    def is_running(self):
        return self.running

    def start(self):
        if self.fail:
            raise SessionError("launcher not found: x.bat")
        self.starts += 1
        was, self.running = self.running, True
        return not was

    def stop(self):
        self.stops += 1
        was, self.running = self.running, False
        return was


def message(text, chat=ME, age=timedelta(seconds=5)):
    return {"chat": {"id": int(chat)}, "date": int((NOW - age).timestamp()), "text": text}


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(remote.time, "sleep", lambda s: None)


def make(session=None, screenshot=lambda: b"jpeg"):
    bot = FakeBot()
    control = RemoteControl(bot, ME, session or FakeSession(), screenshot, clock=lambda: NOW)
    return control, bot


@pytest.mark.parametrize("text, expected", [
    ("/screen", "screen"),
    ("/Screen@xatpbot", "screen"),
    ("/claude please", "claude"),
    ("hello", None),
    ("/", None),
])
def test_parse_command(text, expected):
    assert parse_command(text) == expected


def test_strangers_get_no_reply():
    session = FakeSession()
    control, bot = make(session)
    control.handle(message("/claude", chat="999"))
    assert bot.texts == [] and session.starts == 0


def test_stale_commands_are_dropped():
    session = FakeSession(running=True)
    control, bot = make(session)
    control.handle(message("/stop", age=timedelta(hours=2)))
    assert session.stops == 0 and bot.texts == []


def test_claude_starts_once():
    session = FakeSession()
    control, bot = make(session)
    control.handle(message("/claude"))
    control.handle(message("/claude"))
    assert [t for _, t in bot.texts] == ["Claude запущен.", "Claude уже запущен."]


def test_restart_stops_then_starts():
    session = FakeSession(running=True)
    control, bot = make(session)
    control.handle(message("/restart"))
    assert (session.stops, session.starts, session.running) == (1, 1, True)
    assert bot.texts[-1][1] == "Claude перезапущен."


def test_session_errors_are_reported():
    control, bot = make(FakeSession(fail=True))
    control.handle(message("/claude"))
    assert bot.texts[-1][1].startswith("Не вышло: launcher not found")


def test_screen_sends_photo_only():
    control, bot = make()
    control.handle(message("/screen"))
    assert bot.photos == [(ME, b"jpeg")] and bot.texts == []


def test_screen_error_is_reported():
    def locked():
        raise ScreenError("screen grab failed (is the PC locked?)")

    control, bot = make(screenshot=locked)
    control.handle(message("/screen"))
    assert "locked" in bot.texts[-1][1]


def test_unknown_text_gets_help():
    control, bot = make()
    control.handle(message("привет"))
    assert "/claude" in bot.texts[-1][1]


def test_needs_chat_id():
    with pytest.raises(TelegramError):
        RemoteControl(FakeBot(), "", FakeSession(), lambda: b"")
