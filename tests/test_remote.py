from datetime import datetime, timedelta, timezone

import pytest

from xauto import remote
from xauto.remote import RemoteControl, parse_command, request_session_action, take_session_request
from xauto.services.claude_session import SessionError
from xauto.services.screen import ScreenError
from xauto.services.telegram_bot import TelegramError

NOW = datetime(2026, 11, 10, 17, 0, tzinfo=timezone.utc)
ME = "111"


class FakeBot:
    def __init__(self, updates=()):
        self.texts, self.photos = [], []
        self.updates, self.polls = list(updates), []

    def get_updates(self, offset, wait_s=50):
        self.polls.append((offset, wait_s))
        batch, self.updates = self.updates, []
        return batch

    def send(self, chat_id, text):
        self.texts.append((chat_id, text))

    def send_photo(self, chat_id, image, caption=""):
        self.photos.append((chat_id, image))


class FakeSession:
    def __init__(self, running=False, fail=False, channel=False):
        self.running, self.fail, self.starts, self.stops = running, fail, 0, 0
        self.channel = channel

    def is_running(self):
        return self.running

    def channel_active(self):
        return self.channel

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


def make(session=None, screenshot=lambda: b"jpeg", bot=None, request_file=None):
    bot = bot or FakeBot()
    control = RemoteControl(bot, ME, session or FakeSession(), screenshot,
                            request_file=request_file, clock=lambda: NOW)
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
    assert session.starts == 2  # second call is a no-op inside the session
    assert bot.texts[0][1].startswith("Claude запускается") and bot.texts[1][1] == "Claude уже запущен."


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


def test_session_request_roundtrip(tmp_path):
    file = tmp_path / "req.json"
    request_session_action(file, "restart")
    assert take_session_request(file) == "restart"
    assert not file.exists() and take_session_request(file) is None
    with pytest.raises(ValueError):
        request_session_action(file, "format c:")


def test_watcher_serves_restart_request_from_claude(tmp_path):
    file = tmp_path / "req.json"
    session = FakeSession(running=True)
    control, bot = make(session, request_file=file)
    request_session_action(file, "restart")
    control.step(None)
    assert (session.stops, session.starts, session.running) == (1, 1, True)
    assert bot.polls == []  # never touches the bot's updates while Claude owns them


def test_handoff_confirms_claude_command_before_claude_polls():
    bot = FakeBot(updates=[{"update_id": 41, "message": message("/claude")}])
    session = FakeSession()
    control, _ = make(session, bot=bot)
    assert control.step(None) == 42
    assert session.running
    assert bot.polls[-1] == (42, 0)  # ack, so Claude's channel won't receive /claude again


def test_no_extra_ack_while_claude_stays_closed():
    bot = FakeBot(updates=[{"update_id": 5, "message": message("/status")}])
    control, _ = make(bot=bot)
    control.step(None)
    assert len(bot.polls) == 1


def test_yields_bot_to_a_claude_channel_started_by_hand():
    bot = FakeBot(updates=[{"update_id": 1, "message": message("/status")}])
    control, _ = make(FakeSession(channel=True), bot=bot)
    control.step(None)
    assert bot.polls == []
