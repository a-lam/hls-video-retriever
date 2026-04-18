import os
import sys


def _fmt_bytes(n):
    if n >= 1_073_741_824:
        return f"{n / 1_073_741_824:.2f} GB"
    if n >= 1_048_576:
        return f"{n / 1_048_576:.1f} MB"
    return f"{n / 1024:.1f} KB"


class Logger:
    """Logging helper. Only progress and success output reach the console."""

    def print(self, *args, **kwargs):
        pass  # silent — retained for callers

    def progress(self, current, total, total_bytes):
        """Update an inline progress bar."""
        bar_width = 30
        filled = int(bar_width * current / total) if total else 0
        arrow = ">" if filled < bar_width else ""
        bar = "=" * filled + arrow + " " * (bar_width - filled - len(arrow))
        line = f"\r  Downloading  [{bar}] {current}/{total}  {_fmt_bytes(total_bytes)}"
        sys.stdout.write(f"{line:<78}")
        sys.stdout.flush()

    def finish_progress(self, total_bytes, out_path):
        """Replace the progress bar with a final completion line."""
        name = os.path.basename(out_path)
        line = f"\r  Downloaded   {name}  ({_fmt_bytes(total_bytes)})"
        sys.stdout.write(f"{line:<79}\n")
        sys.stdout.flush()

    def success(self, msg):
        """Write a line to stdout — for final per-video and summary messages."""
        print(msg)
