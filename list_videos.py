import argparse
import os
import sys

from config import VIDEO_EXTENSIONS
from rename_videos import parse_reversed_filename, build_original_name


def find_output_path(folder: str) -> str:
    base = os.path.join(folder, "filelist.txt")
    if not os.path.exists(base):
        return base
    n = 2
    while True:
        candidate = os.path.join(folder, f"filelist ({n}).txt")
        if not os.path.exists(candidate):
            return candidate
        n += 1


def find_named_output_path(folder: str) -> str:
    name = os.path.basename(folder.rstrip("/\\"))
    base = os.path.join(folder, f"{name}.txt")
    if not os.path.exists(base):
        return base
    n = 2
    while True:
        candidate = os.path.join(folder, f"{name} ({n}).txt")
        if not os.path.exists(candidate):
            return candidate
        n += 1


def collect_video_filenames(root: str) -> list[str]:
    seen = set()
    for dirpath, dirnames, filenames_in_dir in os.walk(root, followlinks=False):
        for name in filenames_in_dir:
            ext = os.path.splitext(name)[1].lower()
            if ext in VIDEO_EXTENSIONS:
                seen.add(name)
    return sorted(seen)


def _normalize_to_original(filename: str) -> str:
    parsed = parse_reversed_filename(filename)
    if parsed is None:
        return filename
    return build_original_name(*parsed)


def list_dir(folder: str) -> str | None:
    """Scan folder recursively for videos, write <foldername>.txt inside it. Returns output path or None."""
    filenames = collect_video_filenames(folder)
    if not filenames:
        return None
    output_path = find_named_output_path(folder)
    with open(output_path, "w", encoding="utf-8") as f:
        for name in filenames:
            f.write(_normalize_to_original(name) + "\n")
    return output_path


def list_root_videos(root: str) -> str | None:
    """Write a filelist.txt for video files sitting directly in root (non-recursive). Returns output path or None."""
    root_videos = sorted(
        f for f in os.listdir(root)
        if os.path.isfile(os.path.join(root, f))
        and os.path.splitext(f)[1].lower() in VIDEO_EXTENSIONS
    )
    if not root_videos:
        return None
    out = find_output_path(root)
    with open(out, "w", encoding="utf-8") as fh:
        for name in root_videos:
            fh.write(_normalize_to_original(name) + "\n")
    return out


def main():
    parser = argparse.ArgumentParser(description="List video files in a folder and write them to a text file.")
    parser.add_argument("folder", nargs="?", default=None, help="Folder to scan (default: current directory)")
    args = parser.parse_args()

    root = args.folder if args.folder else os.getcwd()

    if not os.path.isdir(root):
        print(f"Error: '{root}' is not a directory.", file=sys.stderr)
        sys.exit(1)

    print(f"Scanning: {root}")

    subdirs = [
        os.path.join(root, d) for d in sorted(os.listdir(root))
        if os.path.isdir(os.path.join(root, d))
    ]

    if subdirs:
        any_output = False
        for folder in subdirs:
            out = list_dir(folder)
            if out:
                print(f"Written to: {out}")
                any_output = True
            else:
                print(f"No videos found in: {folder}")

        out = list_root_videos(root)
        if out:
            print(f"Written to: {out}")
            any_output = True

        if not any_output:
            print("No videos found.")
    else:
        out = list_dir(root)
        if out:
            print(f"Written to: {out}")
        else:
            print("No videos found.")
            sys.exit(0)


if __name__ == "__main__":
    main()
