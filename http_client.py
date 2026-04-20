import requests


def build_headers(cookies: list, headers: dict) -> dict:
    """Merge captured browser headers and cookies into a plain dict for requests."""
    merged = dict(headers)
    cookie_str = "; ".join(f"{c['name']}={c['value']}" for c in cookies if c.get("name"))
    if cookie_str:
        merged["Cookie"] = cookie_str
    return merged


def get_file_size(url: str, cookies: list, headers: dict) -> str | None:
    """HEAD request → human-readable Content-Length, or None."""
    try:
        resp = requests.head(url, headers=build_headers(cookies, headers), timeout=10)
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


def fetch_m3u8_content(url: str, cookies: list, headers: dict) -> str | None:
    """GET a playlist URL and return the raw text body, or None on failure."""
    try:
        resp = requests.get(url, headers=build_headers(cookies, headers), timeout=15)
        resp.raise_for_status()
        return resp.content.decode("utf-8", errors="replace")
    except Exception:
        return None
