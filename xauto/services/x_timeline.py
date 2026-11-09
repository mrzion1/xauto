"""Find the URL of a post that X has just published from its scheduler.

X does not tell the scheduler which tweet id a scheduled post becomes, so we
read the account's own profile page (logged in, inside its AdsPower profile)
and match the post by the beginning of its text.
"""

from __future__ import annotations

import re

from playwright.async_api import async_playwright

ARTICLE = 'article[data-testid="tweet"]'
TEXT = '[data-testid="tweetText"]'
MATCH_CHARS = 100   # profile pages may cut long posts ("Show more"), so compare the start only


def normalize(text: str) -> str:
    """Collapse whitespace so line breaks and spacing differences don't matter."""
    return re.sub(r"\s+", " ", text).strip().lower()


def same_post(shown: str, queued: str) -> bool:
    a, b = normalize(shown)[:MATCH_CHARS], normalize(queued)[:MATCH_CHARS]
    return bool(a) and (a.startswith(b) or b.startswith(a))


async def find_post_urls(debug_port: int, handle: str, texts: dict[str, str]) -> dict[str, str]:
    """Return {post_id: url} for the queued texts found on the profile page."""
    found: dict[str, str] = {}
    async with async_playwright() as pw:
        browser = await pw.chromium.connect_over_cdp(f"http://127.0.0.1:{debug_port}")
        page = await browser.contexts[0].new_page()
        try:
            await page.goto(f"https://x.com/{handle}", wait_until="domcontentloaded")
            await page.locator(ARTICLE).first.wait_for(timeout=30_000)
            await page.wait_for_timeout(1500)

            for article in await page.locator(ARTICLE).all():
                text_box = article.locator(TEXT)
                if not await text_box.count():
                    continue
                shown = await text_box.first.inner_text()
                # The timestamp link is the canonical /<handle>/status/<id> URL.
                href = await article.locator(f'a[href*="/{handle}/status/" i]:has(time)').first.get_attribute("href")
                if not href:
                    continue
                for post_id, queued in texts.items():
                    if post_id not in found and same_post(shown, queued):
                        found[post_id] = f"https://x.com{href}"
        finally:
            await page.close()
            await browser.close()
    return found
