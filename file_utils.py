import os
import re
from urllib.parse import unquote


def slug_from_url(url):
    """Extract the last path segment from url and sanitise it for use as a filename."""
    segment = unquote(url.rstrip("/").split("/")[-1])
    return re.sub(r"[^\w\-]", "_", segment)[:60]


def unique_path(folder, filename):
    """Return a path inside folder that doesn't exist, appending (1), (2), … as needed."""
    base, ext = os.path.splitext(filename)
    path = os.path.join(folder, filename)
    counter = 1
    while os.path.exists(path):
        path = os.path.join(folder, f"{base} ({counter}){ext}")
        counter += 1
    return path
