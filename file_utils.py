import os
import re
from urllib.parse import unquote


def slug_from_url(url: str) -> str:
    """Extract the last path segment from url and sanitise it for use as a filename."""
    segment = unquote(url.rstrip("/").split("/")[-1])
    return re.sub(r"[^\w\-]", "_", segment)[:60]


def unique_path(folder: str, filename: str) -> str:
    """Return a path inside folder that doesn't exist, appending (1), (2), … as needed."""
    base, ext = os.path.splitext(filename)
    path = os.path.join(folder, filename)
    counter = 1
    while os.path.exists(path):
        path = os.path.join(folder, f"{base} ({counter}){ext}")
        counter += 1
    return path


_FILELIST_MAX_BYTES = 50 * 1024 * 1024  # 50 MB


def append_to_filelist(folder: str, filename: str) -> None:
    path = os.path.join(folder, "filelist.txt")
    counter = 2
    while True:
        if not os.path.exists(path) or os.path.getsize(path) < _FILELIST_MAX_BYTES:
            try:
                with open(path, "a", encoding="utf-8") as f:
                    f.write(filename + "\n")
                return
            except OSError:
                pass  # file locked or unwritable — fall through to next candidate
        path = os.path.join(folder, f"filelist({counter}).txt")
        counter += 1
