"""Start / stop the Claude Code terminal that the remote bot controls (Windows only).

The terminal is a visible console window running the user's launcher .bat
(e.g. ``claude --channels ...``). We remember the PID of that console's
cmd.exe in a small state file, so a restarted watcher still knows about it.
Stopping kills the whole process tree (cmd.exe -> claude -> its children).
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

# Console helpers (tasklist, taskkill) must not flash a window when we run under pythonw.
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


class SessionError(RuntimeError):
    pass


# Claude Code's Telegram channel plugin writes the PID of its poller here while it runs.
CHANNEL_PID_FILE = Path.home() / ".claude" / "channels" / "telegram" / "bot.pid"


def _process_name(pid: int) -> str:
    out = subprocess.run(
        ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
        capture_output=True, text=True, creationflags=NO_WINDOW,
    ).stdout.strip()
    # '"cmd.exe","1234",...' -> 'cmd.exe'; "INFO: No tasks ..." -> ''
    return out.split(",", 1)[0].strip('"').lower() if out.startswith('"') else ""


class ClaudeSession:
    def __init__(self, launcher: str | Path, state_file: Path,
                 channel_pid_file: Path | None = CHANNEL_PID_FILE) -> None:
        self.launcher = Path(launcher) if launcher else None
        self.state_file = state_file
        self.channel_pid_file = channel_pid_file

    # --- state --------------------------------------------------------------

    def _pid(self) -> int | None:
        try:
            return int(json.loads(self.state_file.read_text(encoding="utf-8"))["pid"])
        except (OSError, ValueError, KeyError, TypeError):
            return None

    def _remember(self, pid: int | None) -> None:
        if pid is None:
            self.state_file.unlink(missing_ok=True)
        else:
            self.state_file.write_text(json.dumps({"pid": pid}), encoding="utf-8")

    # --- queries ------------------------------------------------------------

    def is_running(self) -> bool:
        """Is the terminal we opened (by /claude or `session start`) still there?"""
        pid = self._pid()
        if pid is None:
            return False
        # Guard against PID reuse: the process must still be our console's cmd.exe.
        alive = _process_name(pid) == "cmd.exe"
        if not alive:
            self._remember(None)
        return alive

    def channel_active(self) -> bool:
        """Is any Claude session polling the bot right now (even one started by hand)?"""
        if self.channel_pid_file is None:
            return False
        try:
            pid = int(self.channel_pid_file.read_text(encoding="utf-8").strip())
        except (OSError, ValueError):
            return False
        return _process_name(pid) == "bun.exe"   # the plugin's poller runs on Bun

    # --- actions ------------------------------------------------------------

    def start(self) -> bool:
        """Open the terminal. Returns False if it was already running."""
        if self.launcher is None:
            raise SessionError("claude_launcher is empty in config/settings.json")
        if not self.launcher.is_file():
            raise SessionError(f"launcher not found: {self.launcher}")
        if self.is_running():
            return False
        self._remember(self._open_console())
        return True

    def _open_console(self) -> int:
        """Open the launcher in a fresh console window and return its cmd.exe PID.

        Popen(CREATE_NEW_CONSOLE) is not enough: when *our* stdin/stdout are
        pipes (started from another program), the new console inherits them and
        the interactive Claude UI ignores the keyboard. Start-Process goes
        through the shell, so the window always gets its own console handles.
        """
        script = ("(Start-Process -FilePath cmd.exe -ArgumentList '/c', ('\"' + $env:XA_BAT + '\"') "
                  "-WorkingDirectory $env:XA_DIR -PassThru).Id")
        env = {**os.environ, "XA_BAT": str(self.launcher), "XA_DIR": str(self.launcher.parent)}
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True, text=True, env=env, stdin=subprocess.DEVNULL, creationflags=NO_WINDOW,
        )
        try:
            return int(result.stdout.strip())
        except ValueError as exc:
            raise SessionError(f"could not open the terminal: {result.stderr.strip() or result.stdout.strip()}") from exc

    def stop(self) -> bool:
        """Close the terminal and everything started in it. Returns False if it wasn't running."""
        if not self.is_running():
            return False
        subprocess.run(
            ["taskkill", "/PID", str(self._pid()), "/T", "/F"],
            capture_output=True, creationflags=NO_WINDOW,
        )
        self._remember(None)
        return True
