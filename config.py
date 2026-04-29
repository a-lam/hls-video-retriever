# =============================================================================
# RUN TARGETS — edit before each run
# =============================================================================

# URL of a video page or a listing/index page.
# The site profile is auto-selected from the root domain of this URL.
# If the matched profile has a non-empty LISTING_PAGE_SELECTOR, this URL is
# treated as a listing page (listing mode); otherwise it is treated as a
# direct video page (single-video mode).
URL = "https://example.com/your-video-post/"

# =============================================================================
# SITE SETTINGS — fallback defaults (overridden by site profile when URL is set)
# =============================================================================

# Attribute to read from each matched listing element to obtain the video URL.
LISTING_URL_ATTR = "href"

# Controls how many videos are downloaded in listing mode.
#   "all"   — download every video found (default)
#   "first" — stop after the first successful download
DOWNLOAD_MODE = "all"

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
