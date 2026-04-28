import asyncio
from fnmatch import fnmatch
from urllib.parse import urlparse

from playwright.async_api import async_playwright

from config import (
    BLOCKED_DOMAINS,
    BROWSER_USER_AGENT,
    MASTER_PLAYLIST_PATTERNS,
    OVERLAY_DISMISS_SELECTORS,
    OVERLAY_DISMISS_TIMEOUT_MS,
    PAGE_LOAD_TIMEOUT_MS,
    PLAYER_INIT_WAIT_MS,
)


async def _close_overlays(page, log) -> None:
    for sel in OVERLAY_DISMISS_SELECTORS:
        try:
            btn = page.locator(sel).first
            if await btn.is_visible(timeout=OVERLAY_DISMISS_TIMEOUT_MS):
                await btn.click(timeout=OVERLAY_DISMISS_TIMEOUT_MS)
        except Exception:
            pass  # selector not present or timed out — expected, not an error


async def get_video_urls_and_cookies(target_url: str, log) -> tuple[list, list]:
    """
    Launch a headless browser, navigate to target_url, intercept video requests,
    and return (captured, cookies).

    Each entry in captured is a (url, req_headers) tuple for a master m3u8 playlist.
    """
    captured = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent=BROWSER_USER_AGENT)
        page = await context.new_page()

        async def close_popup(popup):
            try:
                await popup.close()
            except Exception:
                pass

        async def dismiss_dialog(dialog):
            try:
                await dialog.dismiss()
            except Exception:
                pass

        page.on("popup", lambda popup: asyncio.ensure_future(close_popup(popup)))
        page.on("dialog", lambda d: asyncio.ensure_future(dismiss_dialog(d)))

        def on_request(request):
            url = request.url
            filename = urlparse(url).path.rsplit("/", 1)[-1]
            if not any(fnmatch(filename.lower(), p) for p in MASTER_PLAYLIST_PATTERNS):
                return
            parsed_host = urlparse(url).hostname or ""
            if any(parsed_host == d or parsed_host.endswith(f".{d}") for d in BLOCKED_DOMAINS):
                log.info(f"[~] Blocked: {url}")
                return
            if any(u == url for u, _ in captured):
                return
            log.info(f"[+] Master playlist: {url}")
            captured.append((url, request.headers))

        page.on("request", on_request)

        log.info(f"[*] Loading page: {target_url}")
        await page.goto(target_url, wait_until="load", timeout=PAGE_LOAD_TIMEOUT_MS)

        await _close_overlays(page, log)

        if not captured:
            log.info("[*] Waiting for video player to initialise...")
            await page.wait_for_timeout(PLAYER_INIT_WAIT_MS)

        cookies = await context.cookies()
        await browser.close()

    seen_urls: set[str] = set()
    deduped = []
    for entry in captured:
        if entry[0] not in seen_urls:
            seen_urls.add(entry[0])
            deduped.append(entry)
    return deduped, cookies
