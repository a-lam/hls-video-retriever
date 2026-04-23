import requests

from config import HEAD_REQUEST_TIMEOUT_S, GET_REQUEST_TIMEOUT_S
from logger import fmt_bytes


def build_headers(cookies: list, headers: dict) -> dict:
    """Merge captured browser headers and cookies into a plain dict for requests."""
    merged = dict(headers)
    cookie_str = "; ".join(f"{c['name']}={c['value']}" for c in cookies if c.get("name"))
    if cookie_str:
        merged["Cookie"] = cookie_str
    return merged


def get_file_size(url: str, cookies: list, headers: dict, log=None) -> str | None:
    """HEAD request → human-readable Content-Length, or None."""
    try:
        resp = requests.head(url, headers=build_headers(cookies, headers), timeout=HEAD_REQUEST_TIMEOUT_S)
        length = resp.headers.get("Content-Length")
        if length:
            return fmt_bytes(int(length))
    except requests.RequestException as e:
        if log:
            log.warning(f"[-] Could not retrieve file size for {url}: {e}")
    return None


def fetch_m3u8_content(url: str, cookies: list, headers: dict, log=None) -> str | None:
    """GET a playlist URL and return the raw text body, or None on failure."""
    try:
        resp = requests.get(url, headers=build_headers(cookies, headers), timeout=GET_REQUEST_TIMEOUT_S)
        resp.raise_for_status()
        return resp.content.decode("utf-8", errors="replace")
    except requests.RequestException as e:
        if log:
            log.warning(f"[-] Failed to fetch playlist {url}: {e}")
        return None
