# =============================================================================
# Site profile — copy this file and rename it to <root-domain>.py
# (e.g. domain_com.py for domain.com or sub.domain.com).
# Only settings relevant to the site need to be present; everything else
# falls back to the values defined in config.py.
# =============================================================================

# CSS selector that matches the link elements on a listing/index page.
# Each matched element is read for the attribute named by LISTING_URL_ATTR.
# Leave empty ("") to run in single-video mode — the URL is treated as a
# direct video page and no listing extraction is performed.
LISTING_PAGE_SELECTOR = ""

# The HTML attribute to read from each element matched by LISTING_PAGE_SELECTOR
# in order to obtain the video-page URL.
# Use "href" for standard anchor links.
# Use a data attribute name (e.g. "data-video") when the URL is stored there.
LISTING_URL_ATTR = "href"

# Optional regex to extract a sub-folder name from the URL (captured group 1
# becomes the output directory name under VIDEOS_DIR).
# Set to "" to save all downloads flat into VIDEOS_DIR.
LISTING_SUBDIR_PATTERN = r"/show/([^/]+)/"

# Hostnames to skip when intercepting network requests (e.g. ad or tracker CDNs).
# Example: ("ads.example.com", "tracker.example.net")
BLOCKED_DOMAINS: tuple[str, ...] = ()

# Glob patterns matched against the filename of each intercepted request URL.
# A request is captured as a master playlist if ANY pattern matches (case-insensitive).
MASTER_PLAYLIST_PATTERNS: tuple[str, ...] = ("master.*", "index.*", "*.m3u8")

# CSS selectors tried in order to close popups/cookie banners.
# First visible match is clicked. Order matters.
OVERLAY_DISMISS_SELECTORS: list[str] = [
    "button[aria-label*='close' i]",
    "button[aria-label*='dismiss' i]",
    "[class*='close' i][role='button']",
    "[class*='popup' i] [class*='close' i]",
    "[class*='modal' i] [class*='close' i]",
    "[class*='overlay' i] [class*='close' i]",
    "button[class*='accept' i]",
    "button[id*='accept' i]",
    ".cc-btn.cc-dismiss",
]

# Quality tier when a master playlist offers multiple streams (sorted by bandwidth):
#   0 = lowest bandwidth / smallest file
#   1 = medium (middle stream)
#   2 = highest bandwidth / largest file
STREAM_QUALITY = 2

# Controls how many videos are downloaded when running in listing mode.
#   "all"   — download every video found across all listing pages (default)
#   "first" — stop after the first video is successfully downloaded
DOWNLOAD_MODE = "all"
