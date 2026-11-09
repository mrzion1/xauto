"""Use case: control this PC from a dedicated Telegram bot (not the post-links bot).

Telegram lets only one program read a bot's messages, and the same bot is used
by Claude Code's Telegram channel. So the bot is handed back and forth:

* Claude terminal closed: this watcher long-polls the bot and obeys
  /claude, /screen, /status (and /restart, /stop as no-ops with a hint).
* Claude terminal open: the watcher stops polling and Claude reads the bot.
  Claude handles /screen itself and asks the watcher to /restart or /stop it
  through a small request file (``python -m xauto session restart|stop``),
  because a process can't reliably kill and relaunch its own console.

Only messages from your own chat are obeyed; everyone else gets no reply.
Commands older than ``MAX_COMMAND_AGE`` are dropped so a stale command never
fires hours later when the PC comes back on.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Protocol

from .services.claude_session import SessionError
from .services.screen import ScreenError
from .services.telegram_bot import TelegramError

log = logging.getLogger(__name__)

MAX_COMMAND_AGE = timedelta(minutes=10)
RETRY_DELAYS_S = (5, 15, 30, 60)    # network down at boot, Telegram hiccups
POLL_WAIT_S = 25                     # long-poll window; also how fast we notice Claude was started by hand
CONFLICT_WAIT_S = 30                 # 409: another program polls the bot
SESSION_CHECK_S = 3                  # while Claude runs: how often to look for requests / exit

COMMANDS = {
    "claude": "открыть терминал Claude",
    "restart": "перезапустить терминал Claude",
    "stop": "закрыть терминал Claude",
    "status": "запущен ли Claude",
    "screen": "скриншот экрана",
}
HELP = "Команды:\n" + "\n".join(f"/{name} - {text}" for name, text in COMMANDS.items())
SESSION_ACTIONS = ("restart", "stop")


class Session(Protocol):
    def is_running(self) -> bool: ...
    def channel_active(self) -> bool: ...
    def start(self) -> bool: ...
    def stop(self) -> bool: ...


def parse_command(text: str) -> str | None:
    """'/screen@somebot extra' -> 'screen'; plain text -> None."""
    words = text[1:].split(maxsplit=1) if text.startswith("/") else []
    return words[0].split("@", 1)[0].lower() or None if words else None


# --- Requests from the Claude session (file based, no network involved) ----------


def request_session_action(request_file: Path, action: str) -> None:
    if action not in SESSION_ACTIONS:
        raise ValueError(f"unknown session action: {action}")
    request_file.write_text(json.dumps({"action": action}), encoding="utf-8")


def take_session_request(request_file: Path) -> str | None:
    try:
        action = json.loads(request_file.read_text(encoding="utf-8")).get("action")
    except (OSError, ValueError, AttributeError):
        return None
    finally:
        request_file.unlink(missing_ok=True)
    return action if action in SESSION_ACTIONS else None


# --- Watcher ---------------------------------------------------------------------


class RemoteControl:
    def __init__(self, bot, chat_id: str, session: Session, screenshot: Callable[[], bytes],
                 request_file: Path | None = None,
                 clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc)) -> None:
        if not chat_id:
            raise TelegramError("remote_chat_id is empty in config/settings.json")
        self.bot = bot
        self.chat_id = str(chat_id)
        self.session = session
        self.screenshot = screenshot
        self.request_file = request_file
        self.clock = clock

    # --- one message from Telegram (only while Claude is closed) -----------------

    def handle(self, message: dict) -> None:
        if str((message.get("chat") or {}).get("id")) != self.chat_id:
            return  # not you: stay silent, don't even confirm the bot is alive
        sent_at = datetime.fromtimestamp(message.get("date", 0), timezone.utc)
        if self.clock() - sent_at > MAX_COMMAND_AGE:
            log.info("skipped stale message from %s", sent_at.isoformat())
            return

        command = parse_command(message.get("text") or "")
        action = {
            "claude": self._start,
            "restart": self._restart,
            "stop": self._stop,
            "status": self._status,
            "screen": self._screen,
        }.get(command)
        log.info("command: %s", command)
        try:
            reply = action() if action else "Claude сейчас закрыт.\n\n" + HELP
        except (SessionError, ScreenError) as exc:
            reply = f"Не вышло: {exc}"
        if reply:
            self.bot.send(self.chat_id, reply)

    def _start(self) -> str:
        if not self.session.start():
            return "Claude уже запущен."
        return "Claude запускается, через полминуты пиши сюда же."

    def _restart(self) -> str:
        was_running = self.session.stop()
        time.sleep(2)  # let the old console close before the new one opens
        self.session.start()
        return "Claude перезапущен." if was_running else "Claude не был запущен, открыл."

    def _stop(self) -> str:
        return "Claude закрыт." if self.session.stop() else "Claude и так закрыт."

    def _status(self) -> str:
        return "Claude запущен." if self.session.is_running() else "Claude закрыт. /claude - открыть."

    def _screen(self) -> str:
        stamp = datetime.now().strftime("%d.%m %H:%M:%S")
        self.bot.send_photo(self.chat_id, self.screenshot(), caption=stamp)
        return ""

    # --- one request from the Claude session ---------------------------------------

    def serve_session_request(self) -> None:
        if self.request_file is None:
            return
        action = take_session_request(self.request_file)
        if action == "stop":
            self.session.stop()
            self.bot.send(self.chat_id, "Claude закрыт. /claude - открыть.")
        elif action == "restart":
            self.session.stop()
            time.sleep(2)
            self.session.start()
            self.bot.send(self.chat_id, "Claude перезапускается, через полминуты пиши.")

    # --- loop --------------------------------------------------------------------

    def run_forever(self) -> None:
        offset: int | None = None
        announced = False
        failures = 0
        while True:
            try:
                if not announced:
                    announced = self._announce()
                offset = self.step(offset)
                failures = 0
            except Exception as exc:  # the watcher must outlive any single failure
                delay = RETRY_DELAYS_S[min(failures, len(RETRY_DELAYS_S) - 1)]
                failures += 1
                if isinstance(exc, TelegramError) and "conflict" in str(exc).lower():
                    # Someone else polls the bot (a Claude channel we didn't detect): stay out of its way.
                    log.info("bot is busy elsewhere (409); waiting")
                    delay, failures = CONFLICT_WAIT_S, 0
                elif isinstance(exc, TelegramError):
                    log.warning("telegram: %s; retry in %ss", exc, delay)
                else:
                    log.exception("unexpected error; retry in %ss", delay)
                time.sleep(delay)

    def step(self, offset: int | None) -> int | None:
        """One round of the loop; returns the next getUpdates offset."""
        if self._claude_owns_bot():
            # Polling now would kick Claude's channel off (409); only serve its restart / stop requests.
            self.serve_session_request()
            time.sleep(SESSION_CHECK_S)
            return offset

        for update in self.bot.get_updates(offset, wait_s=POLL_WAIT_S):
            offset = update["update_id"] + 1
            if "message" in update:
                self._safe_handle(update["message"])
        if offset is not None and self._claude_owns_bot():
            # Confirm what we've read before Claude starts polling, or it would see /claude again.
            self.bot.get_updates(offset, wait_s=0)
        return offset

    def _claude_owns_bot(self) -> bool:
        return self.session.is_running() or self.session.channel_active()

    def _announce(self) -> bool:
        """Menu + "PC online" message. Best effort: never blocks polling (e.g. bot not started yet)."""
        try:
            self.bot.set_commands(COMMANDS)
            self.bot.send(self.chat_id, "ПК онлайн.\n\n" + HELP)
            return True
        except TelegramError as exc:
            log.warning("announce failed: %s", exc)
            return False

    def _safe_handle(self, message: dict) -> None:
        try:
            self.handle(message)
        except Exception:  # one bad command must not kill the watcher
            log.exception("command failed")
