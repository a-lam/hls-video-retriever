# =============================================================================
# RUN TARGETS — edit these before each run
# =============================================================================

# Single-video mode: URL of the page containing the HLS video player.
# Used when LISTING_URL is empty.
TARGET_URL = "https://example.com/your-video-post/"

# Listing mode: URL of a page that links to multiple video pages.
# When non-empty, the pipeline extracts all video-page URLs from this page
# (and subsequent paginated pages) and processes each one automatically.
# Leave empty to run in single-video mode using TARGET_URL instead.
LISTING_URL = ""

# =============================================================================
# SITE SETTINGS — configure once per target site
# =============================================================================

# CSS selector that finds video-page links on a listing page.
# Change this to match the HTML structure of the target site.
LISTING_PAGE_SELECTOR = ".site-main > div > article a"

# Optional regex to extract a sub-folder name from LISTING_URL (group 1 is used
# as the directory name). Set to "" to save all downloads flat into VIDEOS_DIR.
LISTING_SUBDIR_PATTERN = r"/actor/([^/]+)/"

# Filename stem (without extension) used as a fallback to detect playlists
# when the URL lacks a .m3u8 extension. Adjust to match your video host.
VIDEO_STEM_FALLBACK = "index-f1-v1-a1"

# Domains to skip when intercepting network requests (e.g. ad or tracker CDNs).
# Add any CDN hostnames here that serve ads/tracking rather than the main video.
BLOCKED_DOMAINS: tuple[str, ...] = ()

# CSS selectors tried in order to close popups/cookie banners.
# Edit this list to match your target site. Order matters — first visible match is clicked.
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
#   1 = medium (middle stream; favours higher when stream count is even)
#   2 = highest bandwidth / largest file
STREAM_QUALITY = 1

# =============================================================================
# OUTPUT
# =============================================================================

VIDEOS_DIR = "videos"
FILELIST_DIR = "_filelist"

# =============================================================================
# DOWNLOAD TUNING — adjust if you hit rate limits or slow connections
# =============================================================================

# Number of segments fetched in parallel.
DOWNLOAD_WORKERS = 6

# How many times to retry a failed segment before giving up.
SEGMENT_MAX_RETRIES = 3

# Base delay in seconds between retries; doubles each attempt (0.5s, 1s, 2s).
SEGMENT_RETRY_BACKOFF = 0.5

# =============================================================================
# TIMEOUTS & THRESHOLDS — rarely need changing
# =============================================================================

PAGE_LOAD_TIMEOUT_MS       = 60_000  # ms — full page load before giving up
PLAYER_INIT_WAIT_MS        =  6_000  # ms — wait after load for the video player to start
OVERLAY_DISMISS_TIMEOUT_MS =    500  # ms — per-selector timeout when closing popups
HEAD_REQUEST_TIMEOUT_S     = 10      # seconds — file size probe
GET_REQUEST_TIMEOUT_S      = 15      # seconds — playlist fetch
SEGMENT_FETCH_TIMEOUT_S    = 30      # seconds — individual segment download

# Stop paginating after this many listing pages.
MAX_LISTING_PAGES = 15

# A sub-playlist must contain more than this many segments to be considered valid.
SEGMENT_THRESHOLD = 100

# Max characters kept from the URL slug when building an output filename.
FILENAME_SLUG_MAX_LEN = 60

# =============================================================================
# BROWSER
# =============================================================================

BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/136.0.0.0 Safari/537.36"
)

# =============================================================================
# STATIC DATA
# =============================================================================

VIDEO_EXTENSIONS: frozenset[str] = frozenset({
    ".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm",
    ".m4v", ".mpg", ".mpeg", ".ts", ".m2ts", ".mts", ".vob",
    ".3gp", ".3g2", ".ogv", ".rm", ".rmvb", ".divx", ".xvid",
})
