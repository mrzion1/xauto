"""Block commits that would leak private data into the public repository.

Runs as a git pre-commit hook (see .githooks/pre-commit) and in CI.

    python scripts/check_secrets.py            # scan staged changes (pre-commit)
    python scripts/check_secrets.py --all      # scan every tracked file (CI)

A line can be whitelisted with the marker ``secret-scan: ignore``.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass

# Files that must never be committed, whatever they contain.
FORBIDDEN_PATHS = [
    re.compile(r"^data/"),
    re.compile(r"^config/settings\.json$"),
    re.compile(r"\.session(-journal)?$"),
    re.compile(r"(^|/)\.env$"),
]

# Content patterns: (name, regex).
PATTERNS = [
    ("IPv4 address", re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")),
    ("proxy with credentials", re.compile(r"\b[\w.-]+:\d{2,5}:[^\s:]+:[^\s:]+\b|//[^/\s:@]+:[^/\s@]+@")),
    ("e-mail address", re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")),
    ("filled api_key", re.compile(r"\"(?:adspower_)?api_(?:key|hash)\"\s*:\s*\"[^\"]+\"")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b")),
    ("Telegram bot token", re.compile(r"\b\d{8,10}:[A-Za-z0-9_-]{35}\b")),
    ("32-char hex secret", re.compile(r"\b[a-f0-9]{32}\b")),
    ("private key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----|\b0x[a-fA-F0-9]{64}\b")),
]

# Harmless values that look like secrets.
ALLOWED_VALUES = {
    "127.0.0.1",
    "0.0.0.0",
    "noreply@anthropic.com",
}
ALLOWED_SUFFIXES = ("@users.noreply.github.com", "@example.com")
IGNORE_MARKER = "secret-scan: ignore"
SKIP_FILES = {"scripts/check_secrets.py"}  # this file is full of patterns by design


@dataclass
class Finding:
    path: str
    line_no: int
    kind: str
    snippet: str


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True, encoding="utf-8").stdout


def _files(scan_all: bool) -> list[str]:
    if scan_all:
        return _git("ls-files").splitlines()
    return _git("diff", "--cached", "--name-only", "--diff-filter=ACMR").splitlines()


def _content(path: str, scan_all: bool) -> str:
    try:
        if scan_all:
            with open(path, encoding="utf-8") as fh:
                return fh.read()
        # Pre-commit must look at the *staged* version, not the working copy.
        return _git("show", f":{path}")
    except (OSError, UnicodeDecodeError, subprocess.CalledProcessError):
        return ""  # binary or unreadable files are skipped


def _is_allowed(value: str) -> bool:
    return value in ALLOWED_VALUES or value.endswith(ALLOWED_SUFFIXES)


def scan(scan_all: bool) -> list[Finding]:
    findings: list[Finding] = []
    for path in _files(scan_all):
        if any(rule.search(path) for rule in FORBIDDEN_PATHS):
            findings.append(Finding(path, 0, "forbidden file", path))
            continue
        if path in SKIP_FILES:
            continue

        for line_no, line in enumerate(_content(path, scan_all).splitlines(), start=1):
            if IGNORE_MARKER in line:
                continue
            for kind, pattern in PATTERNS:
                for match in pattern.finditer(line):
                    if not _is_allowed(match.group(0)):
                        findings.append(Finding(path, line_no, kind, match.group(0)))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--all", action="store_true", help="scan all tracked files instead of the staged diff")
    args = parser.parse_args()

    findings = scan(args.all)
    if not findings:
        print("secret-scan: clean")
        return 0

    print("secret-scan: possible private data found, commit blocked:\n")
    for f in findings:
        where = f"{f.path}:{f.line_no}" if f.line_no else f.path
        # Show only the start of the match so the scan output itself does not leak it.
        print(f"  {where:<40} {f.kind:<24} {f.snippet[:6]}...")
    print(f"\nFix it, or add '{IGNORE_MARKER}' to a line that is a false positive.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
