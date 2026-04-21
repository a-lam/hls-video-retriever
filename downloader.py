import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor

import requests

from config import DOWNLOAD_WORKERS, SEGMENT_MAX_RETRIES, SEGMENT_RETRY_BACKOFF
from http_client import build_headers, fetch_m3u8_content

_session = requests.Session()


def _fetch_segment_with_retry(seg_url: str, cookies: list, headers: dict) -> bytes | None:
    """Fetch a single segment, retrying up to SEGMENT_MAX_RETRIES times with
    exponential backoff.  Returns the raw bytes, or None on final failure."""
    hdrs = build_headers(cookies, headers)
    for attempt in range(SEGMENT_MAX_RETRIES + 1):
        try:
            resp = _session.get(seg_url, headers=hdrs, timeout=30)
            resp.raise_for_status()
            return resp.content
        except Exception:
            if attempt < SEGMENT_MAX_RETRIES:
                time.sleep(SEGMENT_RETRY_BACKOFF * (2 ** attempt))  # 0.5s, 1s, 2s
    return None


def fetch_segments(m3u8_url: str, cookies: list, headers: dict, ts_path: str, log) -> tuple[int, int]:
    """
    Fetch all segments listed in the m3u8 playlist and concatenate them
    into the file at ts_path.  Segments are downloaded in parallel using a
    thread pool and written to disk in the correct order.

    Returns (failed_segments, total_segments).
    """
    content = fetch_m3u8_content(m3u8_url, cookies, headers)
    if not content:
        log.print("[-] Failed to fetch m3u8 playlist.")
        return 0, 0

    base_url = m3u8_url.rsplit("/", 1)[0] + "/"
    segments = [
        line if line.startswith("http") else urllib.parse.urljoin(base_url, line)
        for line in (ln.strip() for ln in content.splitlines())
        if line and not line.startswith("#")
    ]

    if not segments:
        log.print("[-] No segments found in playlist.")
        return 0, 0

    log.print(f"[*] Downloading {len(segments)} segments ({DOWNLOAD_WORKERS} workers)...")
    total_bytes = 0
    failed_segments = 0

    with ThreadPoolExecutor(max_workers=DOWNLOAD_WORKERS) as pool:
        futures = [
            pool.submit(_fetch_segment_with_retry, url, cookies, headers)
            for url in segments
        ]

        with open(ts_path, "wb") as out_file:
            for i, future in enumerate(futures):
                data = future.result()
                if data:
                    out_file.write(data)
                    total_bytes += len(data)
                else:
                    failed_segments += 1
                    log.warning(f"[-] Segment {i + 1}/{len(segments)} failed after {SEGMENT_MAX_RETRIES} retries — skipping.")
                log.progress(i + 1, len(segments), total_bytes)

    log.finish_progress()
    return failed_segments, len(segments)
