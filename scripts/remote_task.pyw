"""Entry point for the Telegram watcher (`python -m xauto install-remote`).

Started from the Windows Startup folder under pythonw.exe, so it has no
console window. One instance only: a second start exits right away.
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

from xauto.cli import main  # noqa: E402

sys.exit(main(["remote"]))
