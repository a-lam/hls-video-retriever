import urllib.request


def build_request(url, cookies, headers, method="GET"):
    """Build a urllib Request using the provided headers and cookies."""
    req = urllib.request.Request(url, method=method)
    for key, value in headers.items():
        req.add_header(key, value)
    cookie_str = "; ".join(f"{c['name']}={c['value']}" for c in cookies if c.get("name"))
    if cookie_str:
        req.add_header("Cookie", cookie_str)
    return req


def get_file_size(url, cookies, headers):
    """HEAD request → human-readable Content-Length, or None."""
    try:
        req = build_request(url, cookies, headers, method="HEAD")
        with urllib.request.urlopen(req, timeout=10) as resp:
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


def fetch_m3u8_content(url, cookies, headers):
    """GET a playlist URL and return the raw text body, or None on failure."""
    try:
        req = build_request(url, cookies, headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception:
        return None
