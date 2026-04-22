import argparse
import os
import sys

VIDEO_EXTENSIONS = {
    ".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm",
    ".m4v", ".mpg", ".mpeg", ".ts", ".m2ts", ".mts", ".vob",
    ".3gp", ".3g2", ".ogv", ".rm", ".rmvb", ".divx", ".xvid",
}


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


def collect_video_filenames(root: str) -> list[str]:
    seen = set()
    for dirpath, dirnames, filenames_in_dir in os.walk(root, followlinks=False):
        for name in filenames_in_dir:
            ext = os.path.splitext(name)[1].lower()
            if ext in VIDEO_EXTENSIONS:
                seen.add(name)
    return sorted(seen)


def main():
    parser = argparse.ArgumentParser(description="List video files in a folder and write them to a text file.")
    parser.add_argument("folder", nargs="?", default=None, help="Folder to scan (default: current directory)")
    args = parser.parse_args()

    root = args.folder if args.folder else os.getcwd()

    if not os.path.isdir(root):
        print(f"Error: '{root}' is not a directory.", file=sys.stderr)
        sys.exit(1)

    print(f"Scanning: {root}")

    filenames = collect_video_filenames(root)

    if not filenames:
        print("No video files found.")
        sys.exit(0)

    output_path = find_output_path(root)
    with open(output_path, "w", encoding="utf-8") as f:
        for name in filenames:
            f.write(name + "\n")

    print(f"Found {len(filenames)} video file(s).")
    print(f"Written to: {output_path}")


if __name__ == "__main__":
    main()
