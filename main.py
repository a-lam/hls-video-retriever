import asyncio
import os
import sys
import tempfile

from config import TARGET_URL, LISTING_URL, VIDEOS_DIR
from logger import Logger
from browser import get_video_urls_and_cookies
from candidates import select_candidate
from file_utils import slug_from_url, unique_path
from downloader import fetch_segments
from converter import convert_ts_to_mp4
from extractor import extract_video_page_urls


def _process_video_url(url, log):
    """
    Run the full pipeline for a single video-page URL.
    Returns (success: bool, reason: str | None).
    """
    captured, cookies = asyncio.run(get_video_urls_and_cookies(url, log))

    if not captured:
        return False, "no candidates found"

    result = select_candidate(captured, log)
    if result is None:
        return False, "no suitable candidate"

    m3u8_url, req_headers = result

    slug = slug_from_url(url)
    os.makedirs(VIDEOS_DIR, exist_ok=True)
    mp4_path = unique_path(VIDEOS_DIR, f"{slug}.mp4")

    with tempfile.NamedTemporaryFile(suffix=".ts", delete=False) as tmp:
        ts_path = tmp.name

    try:
        fetch_segments(m3u8_url, cookies, req_headers, ts_path, log)
        if not convert_ts_to_mp4(ts_path, mp4_path, log):
            return False, "conversion error"
        log.success(f"[+] Done: {mp4_path}")
        return True, None
    except Exception as e:
        return False, f"download error: {e}"
    finally:
        if os.path.exists(ts_path):
            os.remove(ts_path)


def main():
    log = Logger()

    if LISTING_URL:
        video_urls = asyncio.run(extract_video_page_urls(LISTING_URL, log))

        if not video_urls:
            print("[-] No video page URLs found on the listing page.")
            sys.exit(1)

        for url in video_urls:
            print(url)

        succeeded = 0
        failures = []

        for url in video_urls:
            try:
                ok, reason = _process_video_url(url, log)
                if ok:
                    succeeded += 1
                else:
                    failures.append((url, reason))
            except Exception as e:
                failures.append((url, f"unexpected error: {e}"))

        total = len(video_urls)
        failed = len(failures)
        log.success(f"\n[+] Summary: {total} found, {succeeded} succeeded, {failed} failed")
        for url, reason in failures:
            log.success(f"    [-] {url} — {reason}")

    else:
        captured, cookies = asyncio.run(get_video_urls_and_cookies(TARGET_URL, log))

        if not captured:
            print("[-] No video URLs found on the page.")
            sys.exit(1)

        result = select_candidate(captured, log)
        if result is None:
            print("[-] No suitable m3u8 candidate found.")
            sys.exit(1)

        m3u8_url, req_headers = result

        slug = slug_from_url(TARGET_URL)
        os.makedirs(VIDEOS_DIR, exist_ok=True)
        mp4_path = unique_path(VIDEOS_DIR, f"{slug}.mp4")

        with tempfile.NamedTemporaryFile(suffix=".ts", delete=False) as tmp:
            ts_path = tmp.name

        try:
            fetch_segments(m3u8_url, cookies, req_headers, ts_path, log)
            if not convert_ts_to_mp4(ts_path, mp4_path, log):
                sys.exit(1)
            log.success(f"[+] Done: {mp4_path}")
        finally:
            if os.path.exists(ts_path):
                os.remove(ts_path)


if __name__ == "__main__":
    main()
