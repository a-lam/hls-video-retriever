# URL of the page containing the HLS video player.
TARGET_URL = "https://example.com/your-video-post/"

# If non-empty, enables listing-page mode: extract all video-page URLs from
# this page and process each one through the normal pipeline.
LISTING_URL = ""

VIDEOS_DIR = "videos"

# Domains to skip when intercepting network requests (e.g. ad or tracker CDNs).
# Add any CDN hostnames here that serve ads/tracking rather than the main video.
BLOCKED_DOMAINS = ()

SEGMENT_THRESHOLD = 100
FALLBACK_PLAYLIST = "index-f1-v1-a1"
