import urllib.parse

from playwright.async_api import async_playwright

from config import BROWSER_USER_AGENT, LISTING_PAGE_SELECTOR, LISTING_URL_ATTR, PAGE_LOAD_TIMEOUT_MS


async def extract_video_page_urls(listing_url: str, log) -> list[str]:
    """
    Render listing_url headlessly, extract all article link hrefs matching
    LISTING_PAGE_SELECTOR, resolve relative URLs, deduplicate, and return
    the ordered list of video-page URLs.
    """
    seen: set[str] = set()
    urls: list[str] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent=BROWSER_USER_AGENT)
        page = await context.new_page()

        try:
            await page.goto(listing_url, wait_until="networkidle", timeout=PAGE_LOAD_TIMEOUT_MS)
        except Exception as e:
            log.warning(f"[-] Failed to load listing page {listing_url}: {e}")
            await browser.close()
            return []

        elements = await page.query_selector_all(LISTING_PAGE_SELECTOR)
        if not elements:
            log.warning(
                f"[-] No elements matched LISTING_PAGE_SELECTOR={LISTING_PAGE_SELECTOR!r} "
                "on this page — check config.py"
            )

        for el in elements:
            raw = await el.get_attribute(LISTING_URL_ATTR)
            if not raw:
                continue
            resolved = urllib.parse.urljoin(listing_url, raw)
            if resolved not in seen:
                seen.add(resolved)
                urls.append(resolved)

        await browser.close()

    return urls
