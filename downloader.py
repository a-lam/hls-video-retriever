import urllib.parse
import urllib.request

from http_client import build_request, fetch_m3u8_content


def fetch_segments(m3u8_url, cookies, headers, ts_path, log):
    """
    Fetch all segments listed in the m3u8 playlist and concatenate them
    into the file at ts_path.  ts_path is created by the caller; this
    function only writes to it.
    """
    log.print(f"[*] Fetching playlist: {m3u8_url}")
    content = fetch_m3u8_content(m3u8_url, cookies, headers)
    if not content:
        log.print("[-] Failed to fetch m3u8 playlist.")
        return

    base_url = m3u8_url.rsplit("/", 1)[0] + "/"
    segments = [
        line if line.startswith("http") else urllib.parse.urljoin(base_url, line)
        for line in (ln.strip() for ln in content.splitlines())
        if line and not line.startswith("#")
    ]

    if not segments:
        log.print("[-] No segments found in playlist.")
        return

    log.print(f"[*] Downloading {len(segments)} segments...")
    total_bytes = 0
    with open(ts_path, "wb") as out_file:
        for i, seg_url in enumerate(segments):
            try:
                req = build_request(seg_url, cookies, headers)
                with urllib.request.urlopen(req, timeout=30) as resp:
                    data = resp.read()
                out_file.write(data)
                total_bytes += len(data)
            except Exception as e:
                log.print(f"[-] Segment {i + 1} failed: {e}")
            log.progress(i + 1, len(segments), total_bytes)

    log.finish_progress(total_bytes, ts_path)
