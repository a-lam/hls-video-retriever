import urllib.parse

from playwright.async_api import async_playwright

from browser import BROWSER_USER_AGENT


async def extract_video_page_urls(listing_url: str, log) -> list[str]:
    """
    Render listing_url headlessly, extract all article link hrefs matching
    '.site-main > div > article a', resolve relative URLs, deduplicate, and
    return the ordered list of video-page URLs.
    """
    seen = set()
    urls = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent=BROWSER_USER_AGENT)
        page = await context.new_page()

        await page.goto(listing_url, wait_until="networkidle")

        elements = await page.query_selector_all(".site-main > div > article a")
        for el in elements:
            href = await el.get_attribute("href")
            if not href:
                continue
            resolved = urllib.parse.urljoin(listing_url, href)
            if resolved not in seen:
                seen.add(resolved)
                urls.append(resolved)

        await browser.close()

    return urls
