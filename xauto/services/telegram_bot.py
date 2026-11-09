"""Minimal Telegram Bot API client: messages, photos, long polling, chat id discovery.

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

    def _call(self, method: str, *, files: dict | None = None, http_timeout: float = TIMEOUT_S, **params) -> dict | list:
        url = API.format(token=self.token, method=method)
        try:
            # Uploads go as multipart form data, everything else as JSON.
            if files:
                response = requests.post(url, data=params, files=files, timeout=http_timeout)
            else:
                response = requests.post(url, json=params, timeout=http_timeout)
            body = response.json()
        except (requests.RequestException, ValueError) as exc:
            raise TelegramError(f"Telegram is unreachable: {type(exc).__name__}") from exc
        if not body.get("ok"):
            raise TelegramError(body.get("description") or f"Telegram error (HTTP {response.status_code})")
        return body["result"]

    def send(self, chat_id: str | int, text: str) -> None:
        # Link previews stay on: Telegram shows the X card, handy before forwarding.
        self._call("sendMessage", chat_id=chat_id, text=text)

    def send_photo(self, chat_id: str | int, image: bytes, caption: str = "", filename: str = "screen.jpg") -> None:
        self._call("sendPhoto", files={"photo": (filename, image)}, chat_id=chat_id, caption=caption, http_timeout=60)

    def get_updates(self, offset: int | None, wait_s: int = 50) -> list[dict]:
        """Long polling: returns as soon as a message arrives, or after ``wait_s`` with nothing."""
        params = {"timeout": wait_s, "allowed_updates": ["message"]}
        if offset is not None:
            params["offset"] = offset
        # "timeout" here is Telegram's long-poll wait; the HTTP timeout must be longer.
        return self._call("getUpdates", http_timeout=wait_s + 15, **params)

    def set_commands(self, commands: dict[str, str]) -> None:
        """Fill the bot's "/" menu in Telegram."""
        self._call("setMyCommands", commands=[{"command": c, "description": d} for c, d in commands.items()])

    def latest_private_chat_id(self) -> int | None:
        """Chat id of the last person who wrote to the bot (that's you, after /start)."""
        for update in reversed(self._call("getUpdates")):
            chat = (update.get("message") or {}).get("chat") or {}
            if chat.get("type") == "private":
                return chat["id"]
        return None

    def bot_username(self) -> str:
        return self._call("getMe").get("username", "")
