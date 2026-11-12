"""Find the URL of a post that X has just published from its scheduler.

X does not tell the scheduler which tweet id a scheduled post becomes, so we
read the account's own profile page (logged in, inside its AdsPower profile)
and match the post by the beginning of its text.
"""

from __future__ import annotations

import json
import re
import time

import requests
import websocket  # websocket-client

ARTICLE = 'article[data-testid="tweet"]'
TEXT = '[data-testid="tweetText"]'
MATCH_CHARS = 100   # profile pages may cut long posts ("Show more"), so compare the start only
LOAD_TIMEOUT_S = 40
CALL_TIMEOUT_S = 30


def normalize(text: str) -> str:
    """Collapse whitespace so line breaks and spacing differences don't matter."""
    return re.sub(r"\s+", " ", text).strip().lower()


def same_post(shown: str, queued: str) -> bool:
    a, b = normalize(shown)[:MATCH_CHARS], normalize(queued)[:MATCH_CHARS]
    return bool(a) and (a.startswith(b) or b.startswith(a))


def match_posts(items: list[dict], handle: str, texts: dict[str, str]) -> dict[str, str]:
    """Map queued post ids to URLs, given [{"text", "href"}] read from the profile page."""
    found: dict[str, str] = {}
    prefix = f"/{handle.lower()}/status/"
    for item in items:
        href = item.get("href") or ""
        if prefix not in href.lower():
            continue  # a retweet or quoted post of someone else
        for post_id, queued in texts.items():
            if post_id not in found and same_post(item.get("text", ""), queued):
                found[post_id] = f"https://x.com{href}"
    return found


def find_post_urls(debug_port: int, handle: str, texts: dict[str, str]) -> dict[str, str]:
    """Return {post_id: url} for the queued texts found on the profile page."""
    items = read_profile(debug_port, handle)
    return match_posts(items, handle, texts)


def read_profile(debug_port: int, handle: str, wait_s: float = LOAD_TIMEOUT_S) -> list[dict]:
    """Open the profile in a background tab over raw CDP and return its posts.

    Raw CDP instead of Playwright on purpose: Playwright's connect_over_cdp
    attaches to every target and hangs forever on a profile the user already
    has open with wallet extensions (MetaMask offscreen pages), which is exactly
    when the user is likely to be looking at the account.
    """
    with CdpBrowser(debug_port) as cdp:
        target_id = cdp.call("Target.createTarget", url=f"https://x.com/{handle}", background=True)["targetId"]
        try:
            session = cdp.call("Target.attachToTarget", targetId=target_id, flatten=True)["sessionId"]
            deadline = time.monotonic() + wait_s
            items: list[dict] = []
            while time.monotonic() < deadline:
                time.sleep(1)
                items = cdp.evaluate(session, _READ_ARTICLES_JS) or []
                if items:
                    time.sleep(1.5)  # let the rest of the first screen render
                    return cdp.evaluate(session, _READ_ARTICLES_JS) or items
            return items
        finally:
            cdp.call("Target.closeTarget", targetId=target_id)


class CdpBrowser:
    """Minimal synchronous client for the browser-level DevTools websocket."""

    def __init__(self, debug_port: int) -> None:
        info = requests.get(f"http://127.0.0.1:{debug_port}/json/version", timeout=10).json()
        self._ws_url = info["webSocketDebuggerUrl"]
        self._ws: websocket.WebSocket | None = None
        self._next_id = 0

    def __enter__(self) -> "CdpBrowser":
        self._ws = websocket.create_connection(self._ws_url, timeout=CALL_TIMEOUT_S, suppress_origin=True)
        return self

    def __exit__(self, *exc) -> None:
        if self._ws is not None:
            self._ws.close()

    def call(self, method: str, session_id: str | None = None, **params) -> dict:
        self._next_id += 1
        msg_id = self._next_id
        payload: dict = {"id": msg_id, "method": method, "params": params}
        if session_id:
            payload["sessionId"] = session_id
        self._ws.send(json.dumps(payload))
        while True:  # skip events and replies to other calls
            reply = json.loads(self._ws.recv())
            if reply.get("id") == msg_id:
                if "error" in reply:
                    raise RuntimeError(f"{method}: {reply['error'].get('message')}")
                return reply.get("result", {})

    def evaluate(self, session_id: str, expression: str):
        result = self.call("Runtime.evaluate", session_id, expression=expression, returnByValue=True)
        return result.get("result", {}).get("value")


# The timestamp link inside a post is its canonical /<handle>/status/<id> URL.
_READ_ARTICLES_JS = f"""
Array.from(document.querySelectorAll('{ARTICLE}')).map(a => {{
  const text = a.querySelector('{TEXT}');
  const time = a.querySelector('time');
  const link = time && time.closest('a');
  return text && link ? {{ text: text.innerText, href: link.getAttribute('href') }} : null;
}}).filter(Boolean)
"""
