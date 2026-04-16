"""
Download an HLS video from a web page by:
  1. Loading the page headlessly with Playwright, blocking popups/new-tab traps
  2. Intercepting network requests to capture the video playlist or segment URL
  3. Fetching all segments and concatenating them into a single MP4
"""
import asyncio
import os
import re
import shutil
import subprocess
import sys
import datetime
import urllib.request
import urllib.parse
from playwright.async_api import async_playwright

# URL of the page containing the HLS video player.
TARGET_URL = "https://example.com/your-video-post/"

# Set True to keep all output (segments, log, mp4) inside the timestamped folder.
# Set False (normal) to place the final mp4 in VIDEOS_DIR.
TESTING = False
VIDEOS_DIR = "videos"

# Hostname of the primary video CDN. Requests from this domain are treated as
# the main content (master/media playlist or direct mp4). Leave empty to treat
# all video requests equally.
MAIN_CDN = ""

# Hostnames to skip — ad networks, tracking pixels, etc.
AD_CDNS = ()


# ---------------------------------------------------------------------------
# Output folder + logging
# ---------------------------------------------------------------------------

def unique_path(folder, filename):
    """Return a path inside folder that doesn't exist, appending (1), (2), … as needed."""
    base, ext = os.path.splitext(filename)
    path = os.path.join(folder, filename)
    counter = 1
    while os.path.exists(path):
        path = os.path.join(folder, f"{base} ({counter}){ext}")
        counter += 1
    return path


def make_output_folder():
    """Create a timestamped folder named after the target URL slug."""
    path = TARGET_URL.rstrip("/")
    slug = path.split("/")[-1] or path.split("/")[-2]
    slug = re.sub(r"[^\w\-]", "_", slug)[:60]
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    folder = f"{slug}__{timestamp}"
    os.makedirs(folder, exist_ok=True)
    return folder


def _fmt_bytes(n):
    if n >= 1_073_741_824:
        return f"{n / 1_073_741_824:.2f} GB"
    if n >= 1_048_576:
        return f"{n / 1_048_576:.1f} MB"
    return f"{n / 1024:.1f} KB"


class Logger:
    """Write to a log file; in verbose mode also print to stdout."""
    def __init__(self, log_path, verbose=False):
        self._file = open(log_path, "w", encoding="utf-8")
        self._verbose = verbose

    def print(self, *args, **kwargs):
        msg = " ".join(str(a) for a in args)
        if self._verbose:
            print(msg, **kwargs)
        self._file.write(msg + "\n")
        self._file.flush()

    def status(self, msg):
        """Overwrite a single status line (non-verbose mode only)."""
        if not self._verbose:
            sys.stdout.write(f"\r  {msg:<70}")
            sys.stdout.flush()

    def progress(self, current, total, total_bytes):
        """Update an inline progress bar (non-verbose mode only)."""
        if self._verbose:
            return
        bar_width = 30
        filled = int(bar_width * current / total) if total else 0
        arrow = ">" if filled < bar_width else ""
        bar = "=" * filled + arrow + " " * (bar_width - filled - len(arrow))
        line = f"\r  Downloading  [{bar}] {current}/{total}  {_fmt_bytes(total_bytes)}"
        sys.stdout.write(f"{line:<78}")
        sys.stdout.flush()

    def finish_progress(self, total_bytes, out_path):
        """Replace the progress bar with a final completion line."""
        if not self._verbose:
            name = os.path.basename(out_path)
            sys.stdout.write(f"\r  Downloaded   {name}  ({_fmt_bytes(total_bytes)}){' ' * 20}\n")
            sys.stdout.flush()

    def close(self):
        self._file.close()


# ---------------------------------------------------------------------------
# URL enrichment helpers
# ---------------------------------------------------------------------------

def _build_request(url, cookies, headers, method="GET"):
    req = urllib.request.Request(url, method=method)
    req.add_header("User-Agent", headers.get("user-agent", "Mozilla/5.0"))
    req.add_header("Referer", TARGET_URL)
    cookie_str = "; ".join(f"{c['name']}={c['value']}" for c in cookies if c.get("name"))
    if cookie_str:
        req.add_header("Cookie", cookie_str)
    return req


def get_resolution_hint(url):
    match = re.search(r"(\d{3,4})[pP]", url)
    return f"{match.group(1)}p" if match else None


def get_file_size(url, cookies, headers):
    """HEAD request → human-readable Content-Length, or None."""
    try:
        req = _build_request(url, cookies, headers, method="HEAD")
        with urllib.request.urlopen(req, timeout=10) as resp:
            length = resp.headers.get("Content-Length")
        if length:
            size = int(length)
            if size >= 1_073_741_824:
                return f"{size / 1_073_741_824:.2f} GB"
            if size >= 1_048_576:
                return f"{size / 1_048_576:.1f} MB"
            return f"{size / 1024:.1f} KB"
    except Exception:
        pass
    return None


def fetch_m3u8_streams(url, cookies, headers):
    """Fetch a master m3u8 and return a list of stream dicts with resolution/bandwidth."""
    try:
        req = _build_request(url, cookies, headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            content = resp.read().decode("utf-8", errors="replace")
        streams = []
        for line in content.splitlines():
            if line.startswith("#EXT-X-STREAM-INF"):
                res = re.search(r"RESOLUTION=(\d+x\d+)", line)
                bw = re.search(r"BANDWIDTH=(\d+)", line)
                streams.append({
                    "resolution": res.group(1) if res else None,
                    "bandwidth": f"{int(bw.group(1)) // 1000}kbps" if bw else None,
                })
        return streams
    except Exception:
        return []


def format_candidate(i, priority, url, cookies, headers):
    """Return a multi-line display string for one candidate URL."""
    priority_labels = {0: "m3u8 master playlist", 1: "m3u8 playlist", 2: "direct mp4", 9: "other"}
    label = priority_labels.get(priority, f"priority {priority}")

    details = []

    res_hint = get_resolution_hint(url)
    if res_hint:
        details.append(f"resolution: {res_hint}")

    size = get_file_size(url, cookies, headers)
    if size:
        details.append(f"size: {size}")

    if priority == 0:   # master playlist — parse available streams
        streams = fetch_m3u8_streams(url, cookies, headers)
        if streams:
            stream_strs = []
            for s in streams:
                parts = [p for p in (s["resolution"], s["bandwidth"]) if p]
                stream_strs.append(" @ ".join(parts))
            details.append(f"streams: {', '.join(stream_strs)}")

    detail_str = f"  |  {' | '.join(details)}" if details else ""
    return f"  [{i + 1}] ({label}){detail_str}\n      {url}"


# ---------------------------------------------------------------------------
# Playwright: load page and capture video requests
# ---------------------------------------------------------------------------

async def get_video_urls_and_cookies(log):
    captured = []   # (priority, url)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        )

        page = await context.new_page()

        async def close_popup(popup):
            try:
                await popup.close()
            except Exception:
                pass
        page.on("popup", lambda popup: asyncio.ensure_future(close_popup(popup)))

        async def dismiss_dialog(dialog):
            try:
                await dialog.dismiss()
            except Exception:
                pass
        page.on("dialog", lambda d: asyncio.ensure_future(dismiss_dialog(d)))

        def on_request(request):
            url = request.url
            is_video = ".m3u8" in url or (
                ".mp4" in url and not any(s in url for s in ("thumbnail", "thumb", "preview", "poster"))
            )
            if not is_video:
                return

            if any(cdn in url for cdn in AD_CDNS):
                log.print(f"[~] Skip (ad/tracker): {url}")
                return

            req_headers = request.headers  # capture actual browser headers for this request

            if MAIN_CDN and MAIN_CDN not in url:
                log.print(f"[?] Other video URL: {url}")
                captured.append((9, url, req_headers))
            else:
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

        log.print(f"[*] Loading page: {TARGET_URL}")
        log.status(f"Loading page: {TARGET_URL}")
        await page.goto(TARGET_URL, wait_until="load", timeout=60000)

        await _close_overlays(page, log)

        log.print("[*] Waiting for video player to initialise...")
        log.status("Waiting for video player to initialise...")
        await page.wait_for_timeout(6000)

        cookies = await context.cookies()
        user_agent = await page.evaluate("() => navigator.userAgent")
        await browser.close()

    if not captured:
        return [], [], {}

    captured.sort(key=lambda x: x[0])
    headers = {"user-agent": user_agent}

    log.print(f"\n[*] All candidate URLs found ({len(captured)} total):")
    for i, (priority, url, _) in enumerate(captured):
        log.print(format_candidate(i, priority, url, cookies, headers))
    log.print()

    return captured, cookies, headers


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
            if await btn.is_visible(timeout=500):
                await btn.click(timeout=500)
                log.print(f"[*] Dismissed overlay: {sel}")
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Segment download
# ---------------------------------------------------------------------------

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:149.0) Gecko/20100101 Firefox/149.0"
)
# Some CDNs enforce CORS and require matching Origin/Referer headers.
# Set these to the origin of the video player page if segment downloads fail.
PLAYER_ORIGIN  = ""
PLAYER_REFERER = ""


def _make_player_request(url, cookies):
    """Build a urllib Request with the player headers the server expects."""
    req = urllib.request.Request(url)
    req.add_header("User-Agent", USER_AGENT)
    req.add_header("Accept", "*/*")
    req.add_header("Accept-Language", "en-CA,en-US;q=0.9,en;q=0.8")
    if PLAYER_ORIGIN:
        req.add_header("Origin", PLAYER_ORIGIN)
    if PLAYER_REFERER:
        req.add_header("Referer", PLAYER_REFERER)
    req.add_header("Sec-Fetch-Dest", "empty")
    req.add_header("Sec-Fetch-Mode", "cors")
    req.add_header("Sec-Fetch-Site", "cross-site")
    cookie_str = "; ".join(f"{c['name']}={c['value']}" for c in cookies if c.get("name"))
    if cookie_str:
        req.add_header("Cookie", cookie_str)
    return req


def fetch_segments(m3u8_url, cookies, folder, candidate_index, log):
    """Fetch the m3u8, download all segments, concatenate into a single .ts file."""
    log.print(f"[*] Fetching m3u8: {m3u8_url}")
    try:
        with urllib.request.urlopen(_make_player_request(m3u8_url, cookies), timeout=15) as resp:
            content = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        log.print(f"[-] Failed to fetch m3u8: {e}")
        return

    log.print(f"[*] m3u8 content:\n{content}")

    base_url = m3u8_url.rsplit("/", 1)[0] + "/"
    segments = [
        line if line.startswith("http") else urllib.parse.urljoin(base_url, line)
        for line in (l.strip() for l in content.splitlines())
        if line and not line.startswith("#")
    ]

    if not segments:
        log.print("[-] No segments found in m3u8.")
        return

    out_path = os.path.join(folder, f"candidate_{candidate_index + 1}.ts")
    log.print(f"\n[*] Downloading {len(segments)} segments -> {out_path}")
    total_bytes = 0
    with open(out_path, "wb") as out_file:
        for seg_i, seg_url in enumerate(segments):
            log.print(f"  [{seg_i + 1}/{len(segments)}] {seg_url}")
            try:
                with urllib.request.urlopen(_make_player_request(seg_url, cookies), timeout=30) as resp:
                    data = resp.read()
                out_file.write(data)
                total_bytes += len(data)
                log.print(f"      -> {len(data) / 1024:.1f} KB")
            except Exception as e:
                log.print(f"      -> ERROR: {e}")
            log.progress(seg_i + 1, len(segments), total_bytes)

    log.print(f"\n[+] Done: {out_path} ({total_bytes / 1_048_576:.1f} MB)")
    log.finish_progress(total_bytes, out_path)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main():
    folder = make_output_folder()
    log = Logger(os.path.join(folder, "output.log"), verbose=TESTING)

    log.print(f"[*] Output folder : {folder}")
    log.print(f"[*] Target URL    : {TARGET_URL}\n")

    captured, cookies, _ = await get_video_urls_and_cookies(log)

    if not captured:
        log.print("[-] Could not find any video URLs on the page.")
        log.close()
        return

    TARGET_M3U8 = "index-f1-v1-a1.m3u8"
    m3u8s = [(i, entry[1]) for i, entry in enumerate(captured) if TARGET_M3U8 in entry[1]]

    if m3u8s:
        log.print(f"[*] Found {len(m3u8s)} {TARGET_M3U8} candidate(s) — fetching segments into: {folder}/")
        for i, url in m3u8s:
            log.print(f"\n--- Candidate [{i + 1}] ---")
            fetch_segments(url, cookies, folder, i, log)
    else:
        log.print(f"[-] No {TARGET_M3U8} URL found — nothing downloaded.")
        log.print("    All candidates:")
        for i, entry in enumerate(captured):
            url = entry[1]
            log.print(f"      [{i + 1}] {url}")

    path = TARGET_URL.rstrip("/")
    slug = path.split("/")[-1] or path.split("/")[-2]
    slug = re.sub(r"[^\w\-]", "_", slug)[:60]

    if TESTING:
        mp4_path = os.path.join(folder, f"{slug}.mp4")
    else:
        os.makedirs(VIDEOS_DIR, exist_ok=True)
        mp4_path = unique_path(VIDEOS_DIR, f"{slug}.mp4")

    ts_files = [
        os.path.join(folder, f"candidate_{i + 1}.ts")
        for i, _ in m3u8s
        if os.path.exists(os.path.join(folder, f"candidate_{i + 1}.ts"))
    ]

    if ts_files:
        ts_path = ts_files[0]
        log.print(f"\n[*] Converting {ts_path} -> {mp4_path}")
        log.status(f"Converting to mp4: {os.path.basename(mp4_path)}")
        result = subprocess.run(
            ["ffmpeg", "-f", "mpegts", "-i", ts_path, "-c", "copy", mp4_path],
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            log.print(f"[+] Conversion complete: {mp4_path}")
            log.status(f"Done: {mp4_path}")
            os.remove(ts_path)
            if not TESTING:
                log.close()
                shutil.rmtree(folder)
                return
        else:
            log.print(f"[-] ffmpeg failed (exit {result.returncode}):\n{result.stderr}")

    log.close()


if __name__ == "__main__":
    asyncio.run(main())
