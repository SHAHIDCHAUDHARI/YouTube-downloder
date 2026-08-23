"""
Data models representing video metadata, download formats, and progress states.
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class FormatOption:
    """Represents a normalized user-selectable quality format option."""
    format_id: str
    video_format_id: str = ""
    audio_format_id: str = ""
    resolution_label: str = "720p"
    height: int = 0
    width: int = 0
    ext: str = "mp4"
    fps: float = 0.0
    vcodec: str = ""
    acodec: str = ""
    filesize: Optional[int] = None
    filesize_approx: Optional[int] = None
    is_audio_only: bool = False
    is_mp3_convert: bool = False
    requires_ffmpeg: bool = False
    display_text: str = ""

    def get_estimated_bytes(self) -> Optional[int]:
        """Returns exact filesize if available, else approximate filesize."""
        if self.filesize and self.filesize > 0:
            return self.filesize
        if self.filesize_approx and self.filesize_approx > 0:
            return self.filesize_approx
        return None


@dataclass
class VideoInfo:
    """Represents complete metadata for a fetched video."""
    url: str
    id: str
    title: str
    uploader: str = "Unknown Channel"
    duration: Optional[int] = 0
    view_count: Optional[int] = None
    upload_date: Optional[str] = None
    thumbnail_url: Optional[str] = None
    formats: List[FormatOption] = field(default_factory=list)
    default_format_index: int = 0


@dataclass
class DownloadProgress:
    """Represents real-time download progress and status updates."""
    status: str = "Preparing..."
    downloaded_bytes: int = 0
    total_bytes: int = 0
    percentage: float = 0.0
    speed_str: str = "-- KB/s"
    eta_str: str = "--:--"
    filename: str = ""
    is_finished: bool = False
    is_cancelled: bool = False
    error_message: Optional[str] = None
