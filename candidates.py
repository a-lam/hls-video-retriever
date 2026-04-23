import re
import urllib.parse

from config import SEGMENT_THRESHOLD, STREAM_QUALITY
from http_client import fetch_m3u8_content


def parse_m3u8_streams(content: str, base_url: str = "") -> list[dict]:
    """
    Parse #EXT-X-STREAM-INF entries from master playlist text.
    Returns a list of {resolution, bandwidth, url} dicts.
    bandwidth is the raw integer value in bits/s (0 if absent).
    Relative URLs are resolved against base_url.
    """
    streams = []
    lines = content.splitlines()
    for i, line in enumerate(lines):
        if not line.startswith("#EXT-X-STREAM-INF"):
            continue
        res_match = re.search(r"RESOLUTION=(\d+x\d+)", line)
        bw_match = re.search(r"BANDWIDTH=(\d+)", line)
        url = None
        for j in range(i + 1, len(lines)):
            candidate = lines[j].strip()
            if candidate and not candidate.startswith("#"):
                url = candidate
                break
        if not url:
            continue
        if not url.startswith("http"):
            url = urllib.parse.urljoin(base_url, url)
        streams.append({
            "resolution": res_match.group(1) if res_match else None,
            "bandwidth": int(bw_match.group(1)) if bw_match else 0,
            "url": url,
        })
    return streams


def pick_stream(streams: list[dict], quality: int) -> dict:
    if quality not in (0, 1, 2):
        raise ValueError(f"quality must be 0, 1, or 2; got {quality!r}")
    if not streams:
        raise ValueError("pick_stream called with an empty stream list")
    ranked = sorted(streams, key=lambda s: s["bandwidth"])
    n = len(ranked)
    if quality == 0:
        return ranked[0]
    if quality == 1:
        return ranked[n // 2]   # middle, rounds up when n is even
    return ranked[-1]           # quality == 2


def count_segments(m3u8_content: str) -> int:
    """Count the number of media segments (non-comment, non-empty lines) in a playlist."""
    return sum(
        1 for line in m3u8_content.splitlines()
        if line.strip() and not line.startswith("#")
    )


def select_candidate(captured: list, log) -> tuple[str, dict] | None:
    """
    Choose the best m3u8 URL to download from the captured list.

    For each master playlist: parse it, pick the STREAM_QUALITY-tier sub-playlist,
    fetch it, and accept it only if it contains more than SEGMENT_THRESHOLD segments.

    Returns (url, req_headers) or None.
    """
    masters = [(url, hdrs) for (p, url, hdrs) in captured if p == 0]

    for master_url, master_hdrs in masters:
        content = fetch_m3u8_content(master_url, cookies=[], headers=master_hdrs, log=log)
        if not content:
            log.warning(f"[-] Failed to fetch master playlist: {master_url}")
            continue
        base_url = master_url.rsplit("/", 1)[0] + "/"
        streams = parse_m3u8_streams(content, base_url=base_url)
        if not streams:
            log.warning(f"[-] No streams found in master playlist: {master_url}")
            continue
        best = pick_stream(streams, STREAM_QUALITY)
        sub_content = fetch_m3u8_content(best["url"], cookies=[], headers=master_hdrs, log=log)
        if not sub_content:
            log.warning(f"[-] Failed to fetch sub-playlist: {best['url']}")
            continue
        seg_count = count_segments(sub_content)
        if seg_count <= SEGMENT_THRESHOLD:
            log.warning(
                f"[-] Sub-playlist has only {seg_count} segments "
                f"(threshold: {SEGMENT_THRESHOLD}) — skipping: {best['url']}"
            )
            continue
        log.info(f"[*] Selected sub-playlist ({best['bandwidth']} bps): {best['url']}")
        return best["url"], master_hdrs

    log.warning("[-] No suitable m3u8 candidate found.")
    return None
