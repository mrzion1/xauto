"""Start / stop the Claude Code terminal that the remote bot controls (Windows only).

The terminal is a visible console window running the user's launcher .bat
(e.g. ``claude --channels ...``). We remember the PID of that console's
cmd.exe in a small state file, so a restarted watcher still knows about it.
Stopping kills the whole process tree (cmd.exe -> claude -> its children).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

# Console helpers (tasklist, taskkill) must not flash a window when we run under pythonw.
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
NEW_CONSOLE = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)


class SessionError(RuntimeError):
    pass


class ClaudeSession:
    def __init__(self, launcher: str | Path, state_file: Path) -> None:
        self.launcher = Path(launcher) if launcher else None
        self.state_file = state_file

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
        pid = self._pid()
        if pid is None:
            return False
        out = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
            capture_output=True, text=True, creationflags=NO_WINDOW,
        ).stdout
        # Guard against PID reuse: the process must still be our console's cmd.exe.
        alive = '"cmd.exe"' in out.lower()
        if not alive:
            self._remember(None)
        return alive

    # --- actions ------------------------------------------------------------

    def start(self) -> bool:
        """Open the terminal. Returns False if it was already running."""
        if self.launcher is None:
            raise SessionError("claude_launcher is empty in config/settings.json")
        if not self.launcher.is_file():
            raise SessionError(f"launcher not found: {self.launcher}")
        if self.is_running():
            return False
        process = subprocess.Popen(
            ["cmd.exe", "/c", str(self.launcher)],
            cwd=self.launcher.parent, creationflags=NEW_CONSOLE,
        )
        self._remember(process.pid)
        return True

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
