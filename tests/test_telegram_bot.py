import pytest

from xauto.services import telegram_bot
from xauto.services.telegram_bot import TelegramBot, TelegramError


class FakeResponse:
    status_code = 200

    def __init__(self, body):
        self.body = body

    def json(self):
        return self.body


@pytest.fixture
def calls(monkeypatch):
    seen = []

    def fake_post(url, **kwargs):
        seen.append((url.rsplit("/", 1)[-1], kwargs))
        return FakeResponse({"ok": True, "result": []})

    monkeypatch.setattr(telegram_bot.requests, "post", fake_post)
    return seen


def test_long_poll_wait_and_http_timeout_are_separate(calls):
    TelegramBot("t").get_updates(offset=7, wait_s=50)
    method, kwargs = calls[0]
    assert method == "getUpdates"
    assert kwargs["json"]["timeout"] == 50 and kwargs["json"]["offset"] == 7
    assert kwargs["timeout"] > 50  # HTTP must outlast Telegram's long poll


def test_photo_goes_as_multipart(calls):
    TelegramBot("t").send_photo(1, b"jpeg", caption="now")
    method, kwargs = calls[0]
    assert method == "sendPhoto" and kwargs["files"]["photo"][1] == b"jpeg"
    assert kwargs["data"] == {"chat_id": 1, "caption": "now"}


def test_api_error_is_raised(monkeypatch):
    monkeypatch.setattr(telegram_bot.requests, "post",
                        lambda url, **kw: FakeResponse({"ok": False, "description": "Unauthorized"}))
    with pytest.raises(TelegramError, match="Unauthorized"):
        TelegramBot("t").send(1, "hi")
