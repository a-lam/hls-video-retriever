import asyncio
import os
import re
import sys
import tempfile
import time


def _format_elapsed(seconds):
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"

from config import TARGET_URL, LISTING_URL, VIDEOS_DIR, MAX_LISTING_PAGES
from logger import Logger
from browser import get_video_urls_and_cookies
from candidates import select_candidate
from file_utils import slug_from_url, unique_path, append_to_filelist
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
        return True, os.path.basename(mp4_path)
    except Exception as e:
        return False, f"download error: {e}"
    finally:
        if os.path.exists(ts_path):
            os.remove(ts_path)


CASE_INSENSITIVE_FS = os.name == "nt"


def main():
    log = Logger()
    start_time = time.monotonic()

    if LISTING_URL:
        if not LISTING_URL.startswith(("http://", "https://")):
            print(f"[-] LISTING_URL does not look like a valid URL: {LISTING_URL!r}")
            sys.exit(1)

        base_url = re.sub(r'/page/\d+/?$', '', LISTING_URL.rstrip('/')) + '/'
        m = re.search(r'/page/(\d+)/?$', LISTING_URL)
        start_page = int(m.group(1)) if m else 1

        txt_skip_names: set[str] = set()
        if os.path.isdir(VIDEOS_DIR):
            for fname in os.listdir(VIDEOS_DIR):
                if fname.lower().endswith(".txt"):
                    txt_path = os.path.join(VIDEOS_DIR, fname)
                    with open(txt_path, encoding="utf-8", errors="ignore") as fh:
                        for line in fh:
                            name = line.strip()
                            if name:
                                txt_skip_names.add(name.lower() if CASE_INSENSITIVE_FS else name)

        if txt_skip_names:
            print(f"[*] Loaded {len(txt_skip_names)} entries from skip list")

        succeeded = 0
        skipped = 0
        failures = []
        total = 0

        for i in range(MAX_LISTING_PAGES):
            page_num = start_page + i
            page_url = base_url if page_num == 1 else f"{base_url}page/{page_num}/"
            print(f"[*] Fetching listing page: {page_url}")

            video_urls = asyncio.run(extract_video_page_urls(page_url, log))
            if not video_urls:
                print(f"[-] No video URLs found on page {page_num} — stopping pagination")
                break

            if i == MAX_LISTING_PAGES - 1:
                print(f"[*] Reached page limit of {MAX_LISTING_PAGES} — stopping pagination")

            total += len(video_urls)
            for url in video_urls:
                expected_name = f"{slug_from_url(url)}.mp4"
                lookup_key = expected_name.lower() if CASE_INSENSITIVE_FS else expected_name
                if os.path.exists(os.path.join(VIDEOS_DIR, expected_name)) or lookup_key in txt_skip_names:
                    print(f"[~] Skipping (already exists): {expected_name}")
                    skipped += 1
                    continue

                try:
                    ok, result = _process_video_url(url, log)
                    if ok:
                        succeeded += 1
                        append_to_filelist(VIDEOS_DIR, result)
                    else:
                        failures.append((url, result))
                except Exception as e:
                    failures.append((url, f"unexpected error: {e}"))

        failed = len(failures)
        elapsed = time.monotonic() - start_time
        log.success(f"\n[+] Summary: {total} found, {succeeded} succeeded, {skipped} skipped, {failed} failed — completed in {_format_elapsed(elapsed)}")
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
            elapsed = time.monotonic() - start_time
            log.success(f"[+] Done: {mp4_path} — completed in {_format_elapsed(elapsed)}")
            append_to_filelist(VIDEOS_DIR, os.path.basename(mp4_path))
        finally:
            if os.path.exists(ts_path):
                os.remove(ts_path)


if __name__ == "__main__":
    main()
