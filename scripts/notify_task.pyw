"""Entry point for the Windows scheduled task (`python -m xauto install-task`).

.pyw runs under pythonw.exe, so no console window pops up every few minutes.
Task Scheduler starts it in System32, hence the explicit project path.
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

from xauto.cli import main  # noqa: E402

sys.exit(main(["notify"]))
