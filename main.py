import asyncio
import os
import sys
import tempfile

from config import TARGET_URL, VIDEOS_DIR
from logger import Logger
from browser import get_video_urls_and_cookies
from candidates import select_candidate
from file_utils import slug_from_url, unique_path
from downloader import fetch_segments
from converter import convert_ts_to_mp4


def main():
    log = Logger()

    captured, cookies = asyncio.run(get_video_urls_and_cookies(TARGET_URL, log))

    if not captured:
        log.print("[-] No video URLs found on the page.")
        sys.exit(1)

    result = select_candidate(captured, log)
    if result is None:
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
        log.print(f"[+] Done: {mp4_path}")
    finally:
        if os.path.exists(ts_path):
            os.remove(ts_path)


if __name__ == "__main__":
    main()
