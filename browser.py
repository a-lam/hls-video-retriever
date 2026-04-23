import asyncio
from urllib.parse import urlparse

from playwright.async_api import async_playwright

from config import (
    BLOCKED_DOMAINS,
    BROWSER_USER_AGENT,
    OVERLAY_DISMISS_SELECTORS,
    OVERLAY_DISMISS_TIMEOUT_MS,
    PAGE_LOAD_TIMEOUT_MS,
    PLAYER_INIT_WAIT_MS,
    VIDEO_STEM_FALLBACK,
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

    Each entry in captured is a (priority, url, req_headers) tuple:
      0 = master m3u8 playlist
      1 = regular m3u8 playlist
      2 = direct mp4
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
            filename = url.split("/")[-1].split("?")[0]
            stem = filename.rsplit(".", 1)[0] if "." in filename else filename
            is_m3u8 = ".m3u8" in url
            is_playlist_stem = stem == VIDEO_STEM_FALLBACK
            is_video = is_m3u8 or is_playlist_stem or (
                ".mp4" in url
                and not any(s in url for s in ("thumbnail", "thumb", "preview", "poster"))
            )
            if not is_video:
                return
            parsed_host = urlparse(url).hostname or ""
            if any(parsed_host == d or parsed_host.endswith(f".{d}") for d in BLOCKED_DOMAINS):
                log.info(f"[~] Blocked: {url}")
                return

            req_headers = request.headers
            if is_m3u8 and "master" in url:
                log.info(f"[+] Master playlist: {url}")
                captured.append((0, url, req_headers))
            elif is_m3u8 or is_playlist_stem:
                log.info(f"[+] Playlist: {url}")
                captured.append((1, url, req_headers))
            else:
                log.info(f"[+] Direct mp4: {url}")
                captured.append((2, url, req_headers))

        page.on("request", on_request)

        log.info(f"[*] Loading page: {target_url}")
        await page.goto(target_url, wait_until="load", timeout=PAGE_LOAD_TIMEOUT_MS)

        await _close_overlays(page, log)

        log.info("[*] Waiting for video player to initialise...")
        await page.wait_for_timeout(PLAYER_INIT_WAIT_MS)

        cookies = await context.cookies()
        await browser.close()

    captured.sort(key=lambda x: x[0])
    seen_urls: set[str] = set()
    deduped = []
    for entry in captured:
        if entry[1] not in seen_urls:
            seen_urls.add(entry[1])
            deduped.append(entry)
    return deduped, cookies
