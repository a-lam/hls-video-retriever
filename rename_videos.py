import argparse
import os
import re
import sys


def unique_path(folder: str, filename: str) -> str:
    base, ext = os.path.splitext(filename)
    candidate = os.path.join(folder, filename)
    counter = 1
    while os.path.exists(candidate):
        candidate = os.path.join(folder, f"{base} ({counter}){ext}")
        counter += 1
    return candidate


def _find_date_index(parts: list) -> int | None:
    return next((i for i, p in enumerate(parts) if re.fullmatch(r"\d{8}", p)), None)


def parse_filename(filename: str):
    if not filename.lower().endswith(".mp4"):
        return None
    stem = filename[:-4]
    parts = stem.split("_")
    date_idx = _find_date_index(parts)
    if date_idx is None or date_idx < 2:
        return None
    code = parts[0]
    name = "_".join(parts[1:date_idx])
    date = parts[date_idx]
    other = "_".join(parts[date_idx + 1:]) or None
    return code, name, date, other


def build_new_name(code: str, name: str, date: str, other) -> str:
    if other:
        return f"{name} {date} {code} ({other}).mp4"
    return f"{name} {date} {code}.mp4"


def parse_reversed_filename(filename: str):
    if not filename.lower().endswith(".mp4"):
        return None
    stem = filename[:-4]
    other = None
    m = re.search(r" \(([^)]+)\)$", stem)
    if m:
        other = m.group(1)
        stem = stem[:m.start()]
    tokens = stem.split(" ")
    date_idx = _find_date_index(tokens)
    if date_idx is None or date_idx < 1 or date_idx >= len(tokens) - 1:
        return None
    name = " ".join(tokens[:date_idx])
    date = tokens[date_idx]
    code = " ".join(tokens[date_idx + 1:])
    return code, name, date, other


def build_original_name(code: str, name: str, date: str, other) -> str:
    if other:
        return f"{code}_{name}_{date}_{other}.mp4"
    return f"{code}_{name}_{date}.mp4"


def rename_files(folder: str, reverse: bool = False) -> tuple[int, int]:
    """Rename MP4 files in folder without prompting. Returns (renamed_count, skipped_count)."""
    mp4_files = sorted(f for f in os.listdir(folder) if f.lower().endswith(".mp4"))
    parse_fn = parse_reversed_filename if reverse else parse_filename
    build_fn = build_original_name if reverse else build_new_name
    renames, skipped = [], 0
    for filename in mp4_files:
        parsed = parse_fn(filename)
        if parsed is None:
            skipped += 1
            continue
        code, name, date, other = parsed
        new_name = build_fn(code, name, date, other)
        if new_name != filename:
            renames.append((filename, new_name))
    for filename, new_name in renames:
        target = unique_path(folder, new_name)
        os.rename(os.path.join(folder, filename), target)
    return len(renames), skipped


def main():
    parser = argparse.ArgumentParser(description="Rename MP4 files in a folder to a readable format.")
    parser.add_argument("folder", nargs="?", default=None, help="Folder containing MP4 files (default: current directory)")
    parser.add_argument("--reverse", action="store_true", help="Reconstruct original filenames from renamed files")
    args = parser.parse_args()

    folder = args.folder if args.folder else os.getcwd()

    if not os.path.isdir(folder):
        print(f"Error: '{folder}' is not a directory.", file=sys.stderr)
        sys.exit(1)

    mp4_files = sorted(f for f in os.listdir(folder) if f.lower().endswith(".mp4"))

    if not mp4_files:
        print("No MP4 files found.")
        return

    parse_fn = parse_reversed_filename if args.reverse else parse_filename
    build_fn = build_original_name if args.reverse else build_new_name

    renames = []
    skips = []
    for filename in mp4_files:
        parsed = parse_fn(filename)
        if parsed is None:
            skips.append(filename)
            continue
        code, name, date, other = parsed
        new_name = build_fn(code, name, date, other)
        if new_name != filename:
            renames.append((filename, new_name))

    all_sources = [f for f, _ in renames] + skips
    col_width = max((len(f) for f in all_sources), default=0) + 2

    for filename, new_name in renames:
        print(f"  {filename:<{col_width}}→  {new_name}")

    for filename in skips:
        print(f"  {filename:<{col_width}}→  {filename} [SKIP]")

    print(f"\nSummary: {len(renames)} to rename, {len(skips)} skipped")

    if not renames:
        return

    print("\nDo you want to proceed with renaming these files? [Y/n] ", end="", flush=True)
    confirmation = input().strip()
    if confirmation != "Y":
        print("Did not receive user confirmation. Aborting.")
        return

    for filename, new_name in renames:
        target = unique_path(folder, new_name)
        os.rename(os.path.join(folder, filename), target)

    print(f"{len(renames)} files renamed.")


if __name__ == "__main__":
    main()
