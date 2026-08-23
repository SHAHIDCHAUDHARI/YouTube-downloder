"""
General utility functions for formatting, file operations, system checks, and FFmpeg detection.
"""

import os
import re
import sys
import shutil
import logging
import subprocess
from pathlib import Path
from typing import Optional, Tuple

from app.config import BASE_DIR

logger = logging.getLogger(__name__)


def format_duration(seconds: Optional[int]) -> str:
    """Format seconds into readable HH:MM:SS or MM:SS format."""
    if not seconds or seconds < 0:
        return "00:00"

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def format_bytes(bytes_val: Optional[float]) -> str:
    """Format byte count into human readable MB, GB, KB string."""
    if not bytes_val or bytes_val <= 0:
        return ""

    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(bytes_val)
    unit_idx = 0

    while size >= 1024.0 and unit_idx < len(units) - 1:
        size /= 1024.0
        unit_idx += 1

    if unit_idx == 0:
        return f"{int(size)} B"
    elif unit_idx == 1:
        return f"{size:.1f} KB"
    elif unit_idx == 2:
        return f"{size:.1f} MB"
    else:
        return f"{size:.2f} {units[unit_idx]}"


def format_speed(bytes_per_sec: Optional[float]) -> str:
    """Format speed in bytes per second to readable string."""
    if not bytes_per_sec or bytes_per_sec <= 0:
        return "0 KB/s"
    formatted = format_bytes(bytes_per_sec)
    return f"{formatted}/s" if formatted else "0 KB/s"


def format_eta(seconds: Optional[float]) -> str:
    """Format ETA in seconds into ETA MM:SS or HH:MM:SS."""
    if seconds is None or seconds < 0:
        return "ETA --:--"
    
    sec_int = int(seconds)
    hours = sec_int // 3600
    minutes = (sec_int % 3600) // 60
    secs = sec_int % 60

    if hours > 0:
        return f"ETA {hours:02d}:{minutes:02d}:{secs:02d}"
    return f"ETA {minutes:02d}:{secs:02d}"


def format_count(count: Optional[int]) -> str:
    """Format view counts into readable K/M/B numbers."""
    if count is None or count < 0:
        return ""
    if count >= 1_000_000_000:
        return f"{count / 1_000_000_000:.1f}B"
    if count >= 1_000_000:
        return f"{count / 1_000_000:.1f}M"
    if count >= 1_000:
        return f"{count / 1_000:.1f}K"
    return str(count)


def format_date(date_str: Optional[str]) -> str:
    """Format YYYYMMDD string to YYYY-MM-DD."""
    if not date_str or len(date_str) != 8:
        return date_str or ""
    return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"


def sanitize_filename(filename: str) -> str:
    """Strip invalid Windows filename characters."""
    # Replace illegal characters on Windows
    sanitized = re.sub(r'[\\/*?:"<>|]', "", filename)
    # Strip leading/trailing dots and spaces
    sanitized = sanitized.strip(". ")
    return sanitized or "downloaded_media"


def find_ffmpeg() -> Optional[str]:
    """
    Locate FFmpeg executable in order of priority:
    1. Project-local directory (./ffmpeg/bin, ./ffmpeg, ./bin)
    2. System PATH (installed system-wide)
    3. imageio-ffmpeg Python package fallback
    4. Standard Windows installation locations
    """
    # Priority 1: Project-local directory
    local_candidates = [
        BASE_DIR / "ffmpeg" / "bin",
        BASE_DIR / "ffmpeg",
        BASE_DIR / "ffmpeg_bin",
        BASE_DIR / "bin",
    ]
    for candidate in local_candidates:
        ffmpeg_exe = candidate / ("ffmpeg.exe" if sys.platform == "win32" else "ffmpeg")
        if ffmpeg_exe.is_file():
            logger.info(f"FFmpeg source: project-local ({candidate})")
            return str(candidate)

    # Priority 2: System PATH check
    ffmpeg_in_path = shutil.which("ffmpeg")
    if ffmpeg_in_path:
        ffmpeg_dir = str(Path(ffmpeg_in_path).parent)
        logger.info(f"FFmpeg source: system PATH ({ffmpeg_dir})")
        return ffmpeg_dir

    # Priority 3: imageio-ffmpeg package fallback
    try:
        import imageio_ffmpeg
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        if ffmpeg_exe and Path(ffmpeg_exe).is_file():
            logger.info(f"FFmpeg source: imageio-ffmpeg ({ffmpeg_exe})")
            return str(ffmpeg_exe)
    except Exception as e:
        logger.debug(f"imageio-ffmpeg lookup skipped: {e}")

    # Priority 4: Standard Windows install paths
    if sys.platform == "win32":
        win_paths = [
            Path(r"C:\ffmpeg\bin"),
            Path(r"C:\Program Files\ffmpeg\bin"),
            Path(r"C:\Program Files (x86)\ffmpeg\bin"),
            Path(os.path.expanduser(r"~\ffmpeg\bin")),
        ]
        for path in win_paths:
            if (path / "ffmpeg.exe").is_file():
                logger.info(f"FFmpeg source: system PATH ({path})")
                return str(path)

    logger.warning("FFmpeg executable not found in project, system PATH, or fallback packages.")
    return None


def open_folder(folder_path: Path) -> Tuple[bool, str]:
    """
    Open target directory in system file manager (Windows Explorer).
    Returns (success: bool, message: str).
    """
    try:
        abs_path = folder_path.resolve()
        if not abs_path.exists():
            abs_path.mkdir(parents=True, exist_ok=True)

        if sys.platform == "win32":
            os.startfile(abs_path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(abs_path)])
        else:
            subprocess.Popen(["xdg-open", str(abs_path)])
        return True, "Folder opened successfully"
    except Exception as e:
        logger.error(f"Failed to open folder {folder_path}: {e}", exc_info=True)
        return False, f"Could not open folder: {str(e)}"
