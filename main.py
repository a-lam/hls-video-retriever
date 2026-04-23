import asyncio
import os
import re
import shutil
import sys
import tempfile
import time

import config
from config import (
    FILELIST_DIR,
    LISTING_SUBDIR_PATTERN,
    LISTING_URL,
    MAX_LISTING_PAGES,
    TARGET_URL,
    VIDEOS_DIR,
)
from browser import get_video_urls_and_cookies
from candidates import select_candidate
from converter import convert_ts_to_mp4
from downloader import fetch_segments
from extractor import extract_video_page_urls
from file_utils import slug_from_url, unique_path
from list_videos import list_dir
from logger import Logger, format_elapsed
from rename_videos import rename_files

CASE_INSENSITIVE_FS = os.name == "nt"


def _extract_subdir(url: str) -> str | None:
    """Return a sub-directory name extracted from url via LISTING_SUBDIR_PATTERN, or None."""
    if not LISTING_SUBDIR_PATTERN:
        return None
    m = re.search(LISTING_SUBDIR_PATTERN, url)
    return m.group(1) if m else None


def _load_skip_list(filelist_dir: str) -> set[str]:
    """Read all .txt files in filelist_dir and return a set of normalised filename keys."""
    skip_names: set[str] = set()
    if not os.path.isdir(filelist_dir):
        return skip_names
    for fname in os.listdir(filelist_dir):
        if not fname.lower().endswith(".txt"):
            continue
        txt_path = os.path.join(filelist_dir, fname)
        with open(txt_path, encoding="utf-8", errors="ignore") as fh:
            for line in fh:
                name = line.strip()
                if name:
                    skip_names.add(name.lower() if CASE_INSENSITIVE_FS else name)
    return skip_names


def _process_video_url(url: str, log: Logger, output_dir: str = VIDEOS_DIR) -> tuple[bool, str | None]:
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
    os.makedirs(output_dir, exist_ok=True)
    mp4_path = unique_path(output_dir, f"{slug}.mp4")

    with tempfile.NamedTemporaryFile(suffix=".ts", delete=False) as tmp:
        ts_path = tmp.name

    try:
        failed_segs, total_segs = fetch_segments(m3u8_url, cookies, req_headers, ts_path, log)
        if not convert_ts_to_mp4(ts_path, mp4_path, log):
            return False, "conversion error"
        done_msg = f"[+] {os.path.basename(mp4_path)} [COMPLETED]"
        if failed_segs:
            done_msg += f"  [{failed_segs}/{total_segs} segments failed]"
        log.success(done_msg)
        return True, os.path.basename(mp4_path)
    except Exception as e:
        return False, f"download error: {e}"
    finally:
        if os.path.exists(ts_path):
            os.remove(ts_path)


def _run_single_mode(log: Logger) -> None:
    ok, result = _process_video_url(TARGET_URL, log)
    if not ok:
        log.warning(f"[-] {result}")
        sys.exit(1)


def _run_listing_mode(log: Logger, start_time: float) -> None:
    if not LISTING_URL.startswith(("http://", "https://")):
        log.warning(f"[-] LISTING_URL does not look like a valid URL: {LISTING_URL!r}")
        sys.exit(1)

    base_url = re.sub(r'/page/\d+/?$', '', LISTING_URL.rstrip('/')) + '/'
    m = re.search(r'/page/(\d+)/?$', LISTING_URL)
    start_page = int(m.group(1)) if m else 1

    subdir = _extract_subdir(base_url)
    effective_dir = os.path.join(VIDEOS_DIR, subdir) if subdir else VIDEOS_DIR
    if subdir:
        log.info(f"[*] Sub-directory detected — saving to: {effective_dir}")

    filelist_dir = os.path.join(VIDEOS_DIR, FILELIST_DIR)
    txt_skip_names = _load_skip_list(filelist_dir)
    if txt_skip_names:
        log.info(f"[*] Loaded {len(txt_skip_names)} entries from skip list")

    succeeded = 0
    skipped = 0
    failures = []
    total = 0

    for i in range(MAX_LISTING_PAGES):
        page_num = start_page + i
        page_url = base_url if page_num == 1 else f"{base_url}page/{page_num}/"
        log.info(f"[*] Fetching listing page: {page_url}")

        video_urls = asyncio.run(extract_video_page_urls(page_url, log))
        if not video_urls:
            log.warning(f"[-] No video URLs found on page {page_num} — stopping pagination")
            break

        if i == MAX_LISTING_PAGES - 1:
            log.info(f"[*] Reached page limit of {MAX_LISTING_PAGES} — stopping pagination")

        total += len(video_urls)
        for url in video_urls:
            expected_name = f"{slug_from_url(url)}.mp4"
            lookup_key = expected_name.lower() if CASE_INSENSITIVE_FS else expected_name
            if os.path.exists(os.path.join(effective_dir, expected_name)) or lookup_key in txt_skip_names:
                log.info(f"[~] {expected_name} [SKIPPING - EXISTING]")
                skipped += 1
                continue

            try:
                ok, result = _process_video_url(url, log, output_dir=effective_dir)
                if ok:
                    succeeded += 1
                else:
                    failures.append((url, result))
                    label = "CONVERSION ERROR" if result == "conversion error" else "DOWNLOAD INCOMPLETE"
                    log.warning(f"[-] {slug_from_url(url)}.mp4 [FAILED - {label}]")
            except Exception as e:
                reason = f"unexpected error: {e}"
                failures.append((url, reason))
                log.warning(f"[-] {slug_from_url(url)}.mp4 [FAILED - DOWNLOAD INCOMPLETE]")

    failed = len(failures)
    elapsed = time.monotonic() - start_time
    log.success(
        f"\n[+] Summary: {total} found, {succeeded} succeeded, "
        f"{skipped} skipped, {failed} failed — completed in {format_elapsed(elapsed)}"
    )

    if subdir:
        out = list_dir(effective_dir)
        if out:
            log.info(f"[*] Video list written to: {out}")
            dest_dir = os.path.join(VIDEOS_DIR, FILELIST_DIR)
            os.makedirs(dest_dir, exist_ok=True)
            dest = os.path.join(dest_dir, os.path.basename(out))
            shutil.copy2(out, dest)
            log.info(f"[*] Copied listing to: {dest}")
        else:
            log.info(f"[*] No videos found in {effective_dir} — skipped list step")

        renamed, skipped_renames = rename_files(effective_dir)
        log.info(f"[*] Rename complete: {renamed} renamed, {skipped_renames} skipped")


def _validate_config() -> None:
    if config.STREAM_QUALITY not in (0, 1, 2):
        raise ValueError(f"STREAM_QUALITY must be 0, 1, or 2; got {config.STREAM_QUALITY!r}")
    if config.MAX_LISTING_PAGES < 1:
        raise ValueError(f"MAX_LISTING_PAGES must be >= 1; got {config.MAX_LISTING_PAGES!r}")
    if config.DOWNLOAD_WORKERS < 1:
        raise ValueError(f"DOWNLOAD_WORKERS must be >= 1; got {config.DOWNLOAD_WORKERS!r}")
    if config.SEGMENT_MAX_RETRIES < 0:
        raise ValueError(f"SEGMENT_MAX_RETRIES must be non-negative; got {config.SEGMENT_MAX_RETRIES!r}")


def main() -> None:
    _validate_config()
    log = Logger()
    start_time = time.monotonic()
    if LISTING_URL:
        _run_listing_mode(log, start_time)
    else:
        _run_single_mode(log)


if __name__ == "__main__":
    main()
