import shutil
import sys


def _fmt_bytes(n: int) -> str:
    if n >= 1_073_741_824:
        return f"{n / 1_073_741_824:.2f} GB"
    if n >= 1_048_576:
        return f"{n / 1_048_576:.1f} MB"
    return f"{n / 1024:.1f} KB"


def format_elapsed(seconds: float) -> str:
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


class Logger:
    """Logging helper. Only progress and success output reach the console."""

    def print(self, *args, **kwargs) -> None:
        pass  # silent — retained for callers

    def info(self, msg: str) -> None:
        """Informational output — always shown."""
        print(msg)

    def warning(self, msg: str) -> None:
        """Warning output — always shown."""
        print(msg)

    def progress(self, current: int, total: int, total_bytes: int) -> None:
        """Update an inline progress bar."""
        width = shutil.get_terminal_size(fallback=(80, 24)).columns - 2
        bar_width = 30
        filled = int(bar_width * current / total) if total else 0
        arrow = ">" if filled < bar_width else ""
        bar = "=" * filled + arrow + " " * (bar_width - filled - len(arrow))
        line = f"\r  Downloading  [{bar}] {current}/{total}  {_fmt_bytes(total_bytes)}"
        sys.stdout.write(f"{line:<{width}}")
        sys.stdout.flush()

    def finish_progress(self) -> None:
        """Clear the progress bar line so the next print starts clean."""
        width = shutil.get_terminal_size(fallback=(80, 24)).columns - 2
        sys.stdout.write(f"\r{' ' * width}\r")
        sys.stdout.flush()

    def success(self, msg: str) -> None:
        """Write a line to stdout — for final per-video and summary messages."""
        print(msg)
