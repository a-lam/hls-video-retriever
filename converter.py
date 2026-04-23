import os
import shutil
import subprocess


def convert_ts_to_mp4(ts_path: str, mp4_path: str, log) -> bool:
    """
    Remux ts_path into mp4_path using ffmpeg.
    Returns True on success, False on failure.
    Does not delete ts_path — cleanup is the caller's responsibility.
    """
    if not shutil.which("ffmpeg"):
        log.warning("[-] ffmpeg not found in PATH — install ffmpeg and ensure it is on your PATH.")
        return False

    result = subprocess.run(
        ["ffmpeg", "-f", "mpegts", "-i", ts_path, "-c", "copy", mp4_path],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        log.info(f"[+] Conversion complete: {mp4_path}")
        return True

    log.warning(f"[-] ffmpeg failed (exit {result.returncode}):\n{result.stderr[-2000:]}")
    if os.path.exists(mp4_path):
        try:
            os.remove(mp4_path)
        except OSError as e:
            log.warning(f"[-] Could not remove partial output {mp4_path}: {e}")
    return False
