import os
import re
from urllib.parse import unquote

from config import FILENAME_SLUG_MAX_LEN


def slug_from_url(url: str) -> str:
    """Extract the last path segment from url and sanitise it for use as a filename."""
    segment = unquote(url.rstrip("/").split("/")[-1])
    return re.sub(r"[^A-Za-z0-9\-_]", "_", segment)[:FILENAME_SLUG_MAX_LEN]


def unique_path(folder: str, filename: str) -> str:
    """Return a path inside folder that doesn't exist, appending (1), (2), … as needed."""
    base, ext = os.path.splitext(filename)
    path = os.path.join(folder, filename)
    counter = 1
    while os.path.exists(path):
        path = os.path.join(folder, f"{base} ({counter}){ext}")
        counter += 1
    return path
