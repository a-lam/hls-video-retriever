import asyncio

from playwright.async_api import async_playwright

from config import BLOCKED_DOMAINS

BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)
PAGE_LOAD_TIMEOUT_MS = 60_000
PLAYER_INIT_WAIT_MS = 6_000
OVERLAY_DISMISS_TIMEOUT_MS = 500


async def _close_overlays(page, log):
    selectors = [
        "button[aria-label*='close' i]",
        "button[aria-label*='dismiss' i]",
        "[class*='close' i][role='button']",
        "[class*='popup' i] [class*='close' i]",
        "[class*='modal' i] [class*='close' i]",
        "[class*='overlay' i] [class*='close' i]",
        "button[class*='accept' i]",
        "button[id*='accept' i]",
        ".cc-btn.cc-dismiss",
    ]
    for sel in selectors:
        try:
            btn = page.locator(sel).first
            if await btn.is_visible(timeout=OVERLAY_DISMISS_TIMEOUT_MS):
                await btn.click(timeout=OVERLAY_DISMISS_TIMEOUT_MS)
                log.print(f"[*] Dismissed overlay: {sel}")
        except Exception:
            pass


async def get_video_urls_and_cookies(target_url, log):
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
            is_video = ".m3u8" in url or (
                ".mp4" in url
                and not any(s in url for s in ("thumbnail", "thumb", "preview", "poster"))
            )
            if not is_video:
                return
            if any(domain in url for domain in BLOCKED_DOMAINS):
                log.print(f"[~] Blocked: {url}")
                return

            req_headers = request.headers
            if ".m3u8" in url and "master" in url:
                log.print(f"[+] Master playlist: {url}")
                captured.append((0, url, req_headers))
            elif ".m3u8" in url:
                log.print(f"[+] Playlist: {url}")
                captured.append((1, url, req_headers))
            else:
                log.print(f"[+] Direct mp4: {url}")
                captured.append((2, url, req_headers))

        page.on("request", on_request)

        log.print(f"[*] Loading page: {target_url}")
        await page.goto(target_url, wait_until="load", timeout=PAGE_LOAD_TIMEOUT_MS)

        await _close_overlays(page, log)

        log.print("[*] Waiting for video player to initialise...")
        await page.wait_for_timeout(PLAYER_INIT_WAIT_MS)

        cookies = await context.cookies()
        await browser.close()

    captured.sort(key=lambda x: x[0])
    return captured, cookies
