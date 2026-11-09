"""Thin client for the AdsPower Local API.

Docs: https://localapi-doc-en.adspower.com/

Only the endpoints available on the free AdsPower plan are used here
(``browser/start`` and ``browser/active``). Listing profiles is a paid-only
feature, so the user types the profile id once when adding an account.

Opening a page inside an AdsPower profile is done through the browser's own
Chrome DevTools endpoint (``/json/new``) - no Playwright needed, and the
profile keeps its fingerprint and proxy exactly as configured in AdsPower.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from urllib.parse import quote

import requests

# AdsPower rate-limits the local API to roughly one request per second.
_MIN_INTERVAL_S = 1.05
_TIMEOUT_S = 60


class AdsPowerError(RuntimeError):
    """Raised for any AdsPower failure, with a message that is safe to show in the UI."""


@dataclass(frozen=True)
class BrowserSession:
    debug_port: int
    ws_endpoint: str


class AdsPowerClient:
    def __init__(self, base_url: str, api_key: str = "") -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key.strip()
        self._lock = threading.Lock()
        self._last_call = 0.0

    # --- Low level ----------------------------------------------------------

    def _get(self, path: str, **params: str) -> dict:
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}

        # Serialize calls and keep them >1s apart so AdsPower never rejects us.
        with self._lock:
            wait = _MIN_INTERVAL_S - (time.monotonic() - self._last_call)
            if wait > 0:
                time.sleep(wait)
            try:
                response = requests.get(f"{self.base_url}{path}", params=params, headers=headers, timeout=_TIMEOUT_S)
            except requests.ConnectionError as exc:
                raise AdsPowerError("AdsPower is not running or its Local API is disabled.") from exc
            finally:
                self._last_call = time.monotonic()

        try:
            body = response.json()
        except ValueError as exc:
            raise AdsPowerError(f"Unexpected AdsPower response (HTTP {response.status_code}).") from exc

        if body.get("code") != 0:
            raise AdsPowerError(body.get("msg") or "Unknown AdsPower error.")
        return body.get("data") or {}

    # --- Public API ---------------------------------------------------------

    def is_running(self) -> bool:
        try:
            requests.get(f"{self.base_url}/status", timeout=3)
            return True
        except requests.RequestException:
            return False

    def active_session(self, profile_id: str) -> BrowserSession | None:
        """Return the session of an already opened profile, or None."""
        data = self._get("/api/v1/browser/active", user_id=profile_id)
        if data.get("status") != "Active":
            return None
        return self._session_from(data)

    def start_profile(self, profile_id: str) -> BrowserSession:
        """Open the profile (or reuse it if it is already open)."""
        session = self.active_session(profile_id)
        if session:
            return session
        # open_tabs=1 -> do not restore the AdsPower start page / previous tabs.
        data = self._get("/api/v1/browser/start", user_id=profile_id, open_tabs="1")
        return self._session_from(data)

    def open_url(self, profile_id: str, url: str) -> None:
        """Open ``url`` in a new tab of the given profile and bring that tab to front."""
        session = self.start_profile(profile_id)
        devtools = f"http://127.0.0.1:{session.debug_port}"

        # Chrome 111+ only accepts PUT for /json/new.
        tab = requests.put(f"{devtools}/json/new?{quote(url, safe=':/?&=')}", timeout=15).json()
        requests.get(f"{devtools}/json/activate/{tab['id']}", timeout=15)

    # --- Helpers ------------------------------------------------------------

    @staticmethod
    def _session_from(data: dict) -> BrowserSession:
        try:
            return BrowserSession(
                debug_port=int(data["debug_port"]),
                ws_endpoint=data.get("ws", {}).get("puppeteer", ""),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise AdsPowerError("AdsPower did not return a debug port for this profile.") from exc
