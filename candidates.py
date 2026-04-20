import re
import urllib.parse

from config import FALLBACK_PLAYLIST, SEGMENT_THRESHOLD
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


def count_segments(m3u8_content: str) -> int:
    """Count the number of media segments (non-comment, non-empty lines) in a playlist."""
    return sum(
        1 for line in m3u8_content.splitlines()
        if line.strip() and not line.startswith("#")
    )


def select_candidate(captured: list, log) -> tuple[str, dict] | None:
    """
    Choose the best m3u8 URL to download from the captured list.

    Priority:
      1. Exactly one master playlist → fetch it, return the highest-bandwidth sub-playlist.
      2. First regular playlist with more than SEGMENT_THRESHOLD segments.
      3. First regular playlist whose filename matches FALLBACK_PLAYLIST.
      4. None — nothing suitable found.

    Returns (url, req_headers) or None.
    """
    masters = [(url, hdrs) for (p, url, hdrs) in captured if p == 0]
    regulars = [(url, hdrs) for (p, url, hdrs) in captured if p == 1]

    # Strategy 1: exactly one master playlist
    if len(masters) == 1:
        master_url, master_hdrs = masters[0]
        log.print(f"[*] Single master playlist found — fetching: {master_url}")
        content = fetch_m3u8_content(master_url, cookies=[], headers=master_hdrs)
        if content:
            base_url = master_url.rsplit("/", 1)[0] + "/"
            streams = parse_m3u8_streams(content, base_url=base_url)
            if streams:
                best = max(streams, key=lambda s: s["bandwidth"])
                log.print(f"[*] Selected sub-playlist ({best['bandwidth']} bps): {best['url']}")
                return best["url"], master_hdrs
        log.print("[-] Could not parse master playlist — falling through.")

    # Strategy 2: first regular playlist with enough segments
    for url, hdrs in regulars:
        content = fetch_m3u8_content(url, cookies=[], headers=hdrs)
        if content:
            n = count_segments(content)
            if n > SEGMENT_THRESHOLD:
                log.print(f"[*] Selected playlist with {n} segments: {url}")
                return url, hdrs

    # Strategy 3: filename stem (without extension) matches FALLBACK_PLAYLIST
    for url, hdrs in regulars:
        filename = url.split("/")[-1].split("?")[0]
        stem = filename.rsplit(".", 1)[0] if "." in filename else filename
        if stem == FALLBACK_PLAYLIST:
            log.print(f"[*] Selected fallback playlist: {url}")
            return url, hdrs

    log.print("[-] No suitable m3u8 candidate found.")
    return None
