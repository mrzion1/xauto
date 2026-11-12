"""Windows Task Scheduler: one task with one-shot triggers at given local times.

Registered from an XML definition because `schtasks /SD /ST` take dates in the
system locale format, while XML StartBoundary is always ISO 8601.
"""

from __future__ import annotations

import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape


class TaskError(RuntimeError):
    pass


def build_xml(times: list[datetime], command: str, arguments: str, description: str = "") -> str:
    """Task XML: runs `command arguments` once at each time (naive local or aware)."""
    triggers = "".join(
        "<TimeTrigger><StartBoundary>"
        f"{t.astimezone().replace(tzinfo=None).isoformat(timespec='seconds')}"
        "</StartBoundary><Enabled>true</Enabled></TimeTrigger>"
        for t in sorted(times)
    )
    return f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo><Description>{escape(description)}</Description></RegistrationInfo>
  <Triggers>{triggers}</Triggers>
  <Principals><Principal id="Author"><LogonType>InteractiveToken</LogonType><RunLevel>LeastPrivilege</RunLevel></Principal></Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <StartWhenAvailable>true</StartWhenAvailable>
    <ExecutionTimeLimit>PT10M</ExecutionTimeLimit>
    <Enabled>true</Enabled>
  </Settings>
  <Actions Context="Author"><Exec><Command>{escape(command)}</Command><Arguments>{escape(arguments)}</Arguments></Exec></Actions>
</Task>
"""


def install(name: str, xml: str) -> None:
    """Create or replace the task."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "task.xml"
        path.write_text(xml, encoding="utf-16")
        result = subprocess.run(["schtasks", "/Create", "/F", "/TN", name, "/XML", str(path)],
                                capture_output=True, text=True)
    if result.returncode != 0:
        raise TaskError(result.stderr.strip() or result.stdout.strip())


def remove(name: str) -> None:
    """Delete the task; a missing task is fine."""
    subprocess.run(["schtasks", "/Delete", "/F", "/TN", name], capture_output=True, text=True)
