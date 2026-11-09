"""Minimal Telegram Bot API client: send yourself a message, discover your chat id.

Only the user's own bot is used (token from @BotFather), so no personal
Telegram account is ever logged in by Xauto.
"""

from __future__ import annotations

import requests

API = "https://api.telegram.org/bot{token}/{method}"
TIMEOUT_S = 20


class TelegramError(RuntimeError):
    pass


class TelegramBot:
    def __init__(self, token: str) -> None:
        if not token:
            raise TelegramError("telegram_bot_token is empty in config/settings.json")
        self.token = token

    def _call(self, method: str, **params) -> dict | list:
        try:
            response = requests.post(API.format(token=self.token, method=method), json=params, timeout=TIMEOUT_S)
            body = response.json()
        except (requests.RequestException, ValueError) as exc:
            raise TelegramError(f"Telegram is unreachable: {type(exc).__name__}") from exc
        if not body.get("ok"):
            raise TelegramError(body.get("description") or f"Telegram error (HTTP {response.status_code})")
        return body["result"]

    def send(self, chat_id: str | int, text: str) -> None:
        # Link previews stay on: Telegram shows the X card, handy before forwarding.
        self._call("sendMessage", chat_id=chat_id, text=text)

    def latest_private_chat_id(self) -> int | None:
        """Chat id of the last person who wrote to the bot (that's you, after /start)."""
        for update in reversed(self._call("getUpdates")):
            chat = (update.get("message") or {}).get("chat") or {}
            if chat.get("type") == "private":
                return chat["id"]
        return None

    def bot_username(self) -> str:
        return self._call("getMe").get("username", "")
