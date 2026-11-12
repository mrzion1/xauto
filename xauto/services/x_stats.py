"""Public engagement numbers of a post (views, likes, replies, reposts, bookmarks).

Read from the FxTwitter API, the same public read-only source as x_profile.py,
so no browser or AdsPower profile is needed. The numbers match what X shows
on the post itself.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

import requests

from ..models import PostStats

_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) xauto"}
_TIMEOUT_S = 15
_STATUS_ID = re.compile(r"/status/(\d+)")


class StatsError(RuntimeError):
    pass


def fetch_stats(tweet_url: str, now: datetime | None = None) -> PostStats:
    match = _STATUS_ID.search(tweet_url)
    if not match:
        raise StatsError(f"not a post URL: {tweet_url}")
    try:
        body = requests.get(f"https://api.fxtwitter.com/i/status/{match.group(1)}",
                            headers=_HEADERS, timeout=_TIMEOUT_S).json()
    except (requests.RequestException, ValueError) as exc:
        raise StatsError(f"FxTwitter is unreachable: {type(exc).__name__}") from exc
    tweet = body.get("tweet")
    if not tweet:
        raise StatsError(body.get("message") or "FxTwitter returned no post")
    return PostStats(
        views=int(tweet.get("views") or 0),
        likes=int(tweet.get("likes") or 0),
        replies=int(tweet.get("replies") or 0),
        reposts=int(tweet.get("retweets") or 0) + int(tweet.get("quotes") or 0),
        bookmarks=int(tweet.get("bookmarks") or 0),
        collected_at=now or datetime.now(timezone.utc),
    )
