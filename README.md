# HLS Video Retriever

Downloads HLS (`.m3u8`) streams from video pages and saves them as `.mp4` files. Uses a headless browser to intercept video requests, selects the best quality stream, and downloads segments in parallel.

## Features

- Headless browser interception via Playwright — handles JavaScript-rendered players and cookie-gated streams
- Automatically selects the highest-bandwidth sub-playlist from master playlists
- Parallel segment downloads with configurable workers and retry/backoff
- Listing-page mode: crawl a multi-page index and batch-download all videos
- Skips already-downloaded files (by filesystem check and a `.txt` skip list)
- Dismisses popups, overlays, and dialogs automatically
- Saves output as `.mp4` via ffmpeg

## Requirements

- Python 3.11+
- [ffmpeg](https://ffmpeg.org/) on your `PATH`

Install Python dependencies:

```bash
pip install playwright requests
playwright install chromium
```

## Configuration

Edit `config.py` before running:

| Setting | Description |
|---|---|
| `TARGET_URL` | URL of a single video page to download |
| `LISTING_URL` | URL of a listing/index page to batch-download (leave empty for single-video mode) |
| `MAX_LISTING_PAGES` | Maximum number of listing pages to paginate through |
| `VIDEOS_DIR` | Output directory for downloaded videos (default: `videos/`) |
| `BLOCKED_DOMAINS` | Tuple of CDN hostnames to ignore (e.g. ad networks) |
| `SEGMENT_THRESHOLD` | Minimum segment count to consider a playlist valid |
| `FALLBACK_PLAYLIST` | Filename stem used as a last-resort playlist match |
| `DOWNLOAD_WORKERS` | Number of parallel segment download threads |
| `SEGMENT_MAX_RETRIES` | Retry attempts per failed segment |
| `SEGMENT_RETRY_BACKOFF` | Base delay in seconds between retries (doubles each attempt) |

## Usage

### Download a single video

Set `TARGET_URL` in `config.py`, leave `LISTING_URL` empty, then run:

```bash
python main.py
```

### Batch download from a listing page

Set `LISTING_URL` in `config.py` to a listing/index page URL, then run:

```bash
python main.py
```

If the URL contains `/actor/<name>/`, videos are saved to `videos/<name>/`. Already-downloaded files are skipped automatically.

## Utility scripts

### `rename_videos.py` — Rename files for date-based sorting

Renames files from `CODE_NAME_YYYYMMDD.mp4` → `NAME YYYYMMDD CODE.mp4` so they sort chronologically in a file browser.

```bash
python rename_videos.py [folder]          # preview and confirm renames
python rename_videos.py [folder] --reverse # restore original filenames
```

### `list_videos.py` — Generate a filelist

Scans a directory recursively for video files and writes their filenames to `filelist.txt`. Useful for building skip lists.

```bash
python list_videos.py
```

## Output

Downloaded videos are saved to `VIDEOS_DIR` (default: `videos/`). In listing mode, videos are grouped into a subdirectory per actor when the URL contains `/actor/<name>/`.

A `filelist.txt` in `VIDEOS_DIR` is updated after each successful download and can be used as a skip list on future runs.
