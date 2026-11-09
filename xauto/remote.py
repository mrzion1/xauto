"""Use case: control this PC from your Telegram bot.

A small watcher starts at Windows logon and long-polls the bot. Only messages
from your own chat (``telegram_chat_id``) are obeyed; everything else is
ignored without a reply. Commands:

    /claude   open the Claude Code terminal (your launcher .bat)
    /restart  close it and open it again
    /stop     close it
    /status   is it running?
    /screen   screenshot of all monitors

Commands sent while the PC was off are dropped if they are older than
``MAX_COMMAND_AGE`` so a stale /stop or /restart never fires hours later.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Callable, Protocol

from .services.claude_session import SessionError
from .services.screen import ScreenError
from .services.telegram_bot import TelegramError

log = logging.getLogger(__name__)

MAX_COMMAND_AGE = timedelta(minutes=10)
RETRY_DELAYS_S = (5, 15, 30, 60)    # network down at boot, Telegram hiccups

COMMANDS = {
    "claude": "открыть терминал Claude",
    "restart": "перезапустить терминал Claude",
    "stop": "закрыть терминал Claude",
    "status": "запущен ли Claude",
    "screen": "скриншот экрана",
}
HELP = "Команды:\n" + "\n".join(f"/{name} - {text}" for name, text in COMMANDS.items())


class Session(Protocol):
    def is_running(self) -> bool: ...
    def start(self) -> bool: ...
    def stop(self) -> bool: ...


def parse_command(text: str) -> str | None:
    """'/screen@xatpbot extra' -> 'screen'; plain text -> None."""
    words = text[1:].split(maxsplit=1) if text.startswith("/") else []
    return words[0].split("@", 1)[0].lower() or None if words else None


class RemoteControl:
    def __init__(self, bot, chat_id: str, session: Session, screenshot: Callable[[], bytes],
                 clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc)) -> None:
        if not chat_id:
            raise TelegramError("telegram_chat_id is empty: run `python -m xauto telegram-setup` first")
        self.bot = bot
        self.chat_id = str(chat_id)
        self.session = session
        self.screenshot = screenshot
        self.clock = clock

    # --- one message -------------------------------------------------------------

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
            reply = action() if action else HELP
        except (SessionError, ScreenError) as exc:
            reply = f"Не вышло: {exc}"
        if reply:
            self.bot.send(self.chat_id, reply)

    def _start(self) -> str:
        return "Claude запущен." if self.session.start() else "Claude уже запущен."

    def _restart(self) -> str:
        was_running = self.session.stop()
        time.sleep(2)  # let the old console close before the new one opens
        self.session.start()
        return "Claude перезапущен." if was_running else "Claude не был запущен, открыл заново."

    def _stop(self) -> str:
        return "Claude закрыт." if self.session.stop() else "Claude и так не запущен."

    def _status(self) -> str:
        return "Claude запущен." if self.session.is_running() else "Claude не запущен. /claude - открыть."

    def _screen(self) -> str:
        stamp = datetime.now().strftime("%d.%m %H:%M:%S")
        self.bot.send_photo(self.chat_id, self.screenshot(), caption=stamp)
        return ""

    # --- loop --------------------------------------------------------------------

    def run_forever(self) -> None:
        announced = False
        offset: int | None = None
        failures = 0
        while True:
            try:
                if not announced:
                    self.bot.set_commands(COMMANDS)
                    self.bot.send(self.chat_id, "ПК онлайн.\n\n" + HELP)
                    announced = True
                for update in self.bot.get_updates(offset):
                    offset = update["update_id"] + 1   # confirm it even if handling fails
                    if "message" in update:
                        self._safe_handle(update["message"])
                failures = 0
            except Exception as exc:  # the watcher must outlive any single failure
                delay = RETRY_DELAYS_S[min(failures, len(RETRY_DELAYS_S) - 1)]
                failures += 1
                if isinstance(exc, TelegramError):
                    log.warning("telegram: %s; retry in %ss", exc, delay)
                else:
                    log.exception("unexpected error; retry in %ss", delay)
                time.sleep(delay)

    def _safe_handle(self, message: dict) -> None:
        try:
            self.handle(message)
        except Exception:  # one bad command must not kill the watcher
            log.exception("command failed")
