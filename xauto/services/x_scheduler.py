"""Put approved posts into X's native scheduler through an AdsPower profile.

How it works
------------
1. AdsPower starts (or reuses) the account's browser profile, so X sees the
   usual fingerprint, proxy and cookies.
2. Playwright attaches to that browser over CDP and opens one tab per post on
   ``x.com/compose/post``: text, media, then the "Schedule" dialog.
3. Before X receives anything, the outgoing ``CreateScheduledTweet`` request is
   intercepted and checked against the queue: send time (UTC), exact text and
   number of attachments. Any mismatch aborts the request, so nothing wrong
   can be scheduled. In dry-run mode the request is always aborted, which
   exercises the whole flow without touching the account.

X changes its markup now and then. All selectors live in ``Selectors`` below,
so a breakage is a one-place fix.
"""

from __future__ import annotations

import asyncio
import json
import random
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from playwright.async_api import Page, Request, Route, async_playwright

from ..models import Post

COMPOSE_URL = "https://x.com/compose/post"
SCHEDULE_ENDPOINT = "**/CreateScheduledTweet*"

UPLOAD_TIMEOUT_MS = 5 * 60_000      # long videos take a while to process
STEP_TIMEOUT_MS = 30_000
TIME_TOLERANCE_S = 60               # X schedules with minute precision


class Selectors:
    DIALOG = '[role="dialog"]'
    TEXTAREA = '[role="dialog"] [data-testid="tweetTextarea_0"]'
    FILE_INPUT = '[role="dialog"] input[data-testid="fileInput"]'
    SCHEDULE_BUTTON = '[role="dialog"] [data-testid="scheduleOption"]'
    CONFIRM = '[data-testid="scheduledConfirmationPrimaryAction"]'
    SUBMIT = '[role="dialog"] [data-testid="tweetButton"]'
    ATTACHMENTS = '[role="dialog"] [data-testid="attachments"]'


class SchedulerError(RuntimeError):
    """Scheduling one post failed; the message is safe to show in the UI."""


@dataclass
class ScheduleResult:
    post_id: str
    ok: bool
    dry_run: bool
    message: str = ""
    scheduled_id: str = ""
    screenshot: Path | None = None


@dataclass
class _Expected:
    """What the outgoing request must contain."""

    execute_at: int
    text: str
    media_count: int
    dry_run: bool
    problems: list[str] = field(default_factory=list)
    seen: bool = False


# --- Payload helpers -----------------------------------------------------------


def _find_key(obj: Any, key: str) -> Any:
    """Depth-first search for ``key`` in a nested JSON payload."""
    if isinstance(obj, dict):
        if key in obj:
            return obj[key]
        for value in obj.values():
            found = _find_key(value, key)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for value in obj:
            found = _find_key(value, key)
            if found is not None:
                return found
    return None


def _normalize(text: str) -> str:
    """X trims trailing spaces per line and the ends of the post."""
    return "\n".join(line.rstrip() for line in text.strip().replace("\r\n", "\n").split("\n"))


def check_payload(payload: dict, expected: _Expected) -> list[str]:
    """Compare a CreateScheduledTweet payload with the queued post. Empty list = OK."""
    problems = []

    execute_at = _find_key(payload, "execute_at")
    if not isinstance(execute_at, (int, float)):
        problems.append("send time not found in X's request")
    elif abs(int(execute_at) - expected.execute_at) > TIME_TOLERANCE_S:
        got = datetime.fromtimestamp(int(execute_at), tz=timezone.utc)
        want = datetime.fromtimestamp(expected.execute_at, tz=timezone.utc)
        problems.append(f"wrong send time: X got {got:%Y-%m-%d %H:%M} UTC, queue says {want:%Y-%m-%d %H:%M} UTC")

    status = _find_key(payload, "status")
    if not isinstance(status, str):
        problems.append("post text not found in X's request")
    elif _normalize(status) != _normalize(expected.text):
        problems.append("post text in X differs from the queue (typing went wrong)")

    media_ids = _find_key(payload, "media_ids") or []
    if len(media_ids) != expected.media_count:
        problems.append(f"{len(media_ids)} attachment(s) in X, expected {expected.media_count}")
    return problems


# --- Browser steps ---------------------------------------------------------------


async def _type_text(page: Page, text: str) -> None:
    """Type line by line: Enter inside X's editor makes a new line, it never sends."""
    box = page.locator(Selectors.TEXTAREA)
    await box.click()
    lines = text.replace("\r\n", "\n").split("\n")
    for index, line in enumerate(lines):
        if line:
            await page.keyboard.insert_text(line)
        if index < len(lines) - 1:
            await page.keyboard.press("Enter")
        await page.wait_for_timeout(random.randint(40, 120))


async def _attach_media(page: Page, files: list[Path]) -> None:
    if not files:
        return
    await page.locator(Selectors.FILE_INPUT).set_input_files([str(f) for f in files])
    await page.locator(Selectors.ATTACHMENTS).wait_for(timeout=STEP_TIMEOUT_MS)
    # The submit button stays disabled until X finishes uploading / processing.
    submit = page.locator(Selectors.SUBMIT)
    deadline = asyncio.get_running_loop().time() + UPLOAD_TIMEOUT_MS / 1000
    while await submit.get_attribute("aria-disabled") == "true":
        if asyncio.get_running_loop().time() > deadline:
            raise SchedulerError("media upload did not finish in 5 minutes")
        await page.wait_for_timeout(1000)


async def _local_fields(page: Page, when: datetime) -> dict[str, int]:
    """Date/time fields as the *browser* sees them; X's dialog uses the browser clock."""
    millis = int(when.timestamp() * 1000)
    return await page.evaluate(
        """ms => { const d = new Date(ms);
                   return {year: d.getFullYear(), month: d.getMonth() + 1, day: d.getDate(),
                           hour: d.getHours(), minute: d.getMinutes()}; }""",
        millis,
    )


async def _select_by_label(page: Page, label: str, value: str) -> None:
    """X's schedule selects are only identifiable by their visible label."""
    select_id = await page.evaluate(
        """label => { for (const s of document.querySelectorAll('select')) {
                          const l = document.getElementById(s.getAttribute('aria-labelledby') || '');
                          if (l && l.textContent.trim() === label) return s.id; }
                      return null; }""",
        label,
    )
    if not select_id:
        raise SchedulerError(f"schedule dialog has no '{label}' field (X changed its layout?)")
    await page.locator(f"select#{select_id}").select_option(value=value)


async def _set_schedule(page: Page, when: datetime) -> None:
    await page.locator(Selectors.SCHEDULE_BUTTON).click()
    await page.locator(Selectors.CONFIRM).wait_for(timeout=STEP_TIMEOUT_MS)

    f = await _local_fields(page, when)
    hour12 = f["hour"] % 12 or 12
    await _select_by_label(page, "Year", str(f["year"]))   # year first: it limits months/days
    await _select_by_label(page, "Month", str(f["month"]))
    await _select_by_label(page, "Day", str(f["day"]))
    await _select_by_label(page, "Hour", str(hour12))
    await _select_by_label(page, "Minute", str(f["minute"]))
    await _select_by_label(page, "AM/PM", "pm" if f["hour"] >= 12 else "am")
    await page.locator(Selectors.CONFIRM).click()


# --- Public API ------------------------------------------------------------------


class XScheduler:
    def __init__(self, debug_port: int, dry_run: bool = False) -> None:
        self.debug_port = debug_port
        self.dry_run = dry_run

    async def schedule_many(
        self,
        posts: list[tuple[Post, list[Path], Path]],
        on_result: Callable[[ScheduleResult], None] | None = None,
    ) -> list[ScheduleResult]:
        """Schedule posts one by one in the already running AdsPower browser.

        ``posts`` items are (post, media files, folder for failure screenshots).
        """
        results: list[ScheduleResult] = []
        async with async_playwright() as pw:
            browser = await pw.chromium.connect_over_cdp(f"http://127.0.0.1:{self.debug_port}")
            context = browser.contexts[0]
            try:
                for index, (post, media, folder) in enumerate(posts):
                    result = await self._schedule_one(context, post, media, folder)
                    results.append(result)
                    if on_result:
                        on_result(result)
                    if index < len(posts) - 1:
                        await asyncio.sleep(random.uniform(4, 10))  # don't hammer X
            finally:
                await browser.close()  # detaches only; the AdsPower window stays open
        return results

    async def _schedule_one(self, context, post: Post, media: list[Path], folder: Path) -> ScheduleResult:
        expected = _Expected(
            execute_at=int(post.scheduled_at.timestamp()),
            text=post.text,
            media_count=len(media),
            dry_run=self.dry_run,
        )
        response_body: dict = {}

        async def guard(route: Route, request: Request) -> None:
            expected.seen = True
            try:
                payload = request.post_data_json or {}
            except ValueError:
                payload = {}
            expected.problems = check_payload(payload, expected)
            if expected.dry_run or expected.problems:
                # Keep what X would have received: the first thing to look at when X changes its API.
                folder.mkdir(parents=True, exist_ok=True)
                (folder / "schedule_request.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
                await route.abort()
            else:
                response = await route.fetch()
                try:
                    response_body.update(await response.json())
                except ValueError:
                    pass
                await route.fulfill(response=response)

        page = await context.new_page()
        await page.route(SCHEDULE_ENDPOINT, guard)
        try:
            if post.scheduled_at <= datetime.now(timezone.utc):
                raise SchedulerError("send time is already in the past")

            await page.goto(COMPOSE_URL, wait_until="domcontentloaded")
            await page.locator(Selectors.TEXTAREA).wait_for(timeout=STEP_TIMEOUT_MS)
            await _type_text(page, post.text)
            await _attach_media(page, media)
            await _set_schedule(page, post.scheduled_at)

            await page.locator(Selectors.SUBMIT).click()
            # Give the guard time to see (and maybe abort) the request.
            for _ in range(30):
                if expected.seen:
                    break
                await page.wait_for_timeout(500)
            if not expected.seen:
                raise SchedulerError("X never sent the schedule request")
            if expected.problems:
                raise SchedulerError("; ".join(expected.problems))
            await page.wait_for_timeout(1500)

            if self.dry_run:
                return ScheduleResult(post.id, ok=True, dry_run=True, message="dry run: all checks passed")
            scheduled_id = str(_find_key(response_body, "rest_id") or "")
            return ScheduleResult(post.id, ok=True, dry_run=False, message="scheduled", scheduled_id=scheduled_id)

        except Exception as exc:  # any step can fail on a live site; report, don't crash the batch
            shot = folder / "schedule_error.png"
            try:
                folder.mkdir(parents=True, exist_ok=True)
                await page.screenshot(path=str(shot))
            except Exception:
                shot = None
            message = str(exc) if isinstance(exc, SchedulerError) else f"{type(exc).__name__}: {exc}"
            return ScheduleResult(post.id, ok=False, dry_run=self.dry_run, message=message, screenshot=shot)
        finally:
            await page.close()
