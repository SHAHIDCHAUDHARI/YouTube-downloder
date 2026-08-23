"""
Metadata extraction and format normalization engine using yt-dlp Python API.
"""

import logging
from typing import Any, Dict, List, Optional
import yt_dlp

from app.models import FormatOption, VideoInfo
from app.utils import format_bytes

logger = logging.getLogger(__name__)


def _get_resolution_label(height: int, fps: float = 0.0) -> str:
    """Map vertical resolution height and fps to YouTube-style quality string (e.g., 1080p60 HD, 720p HD)."""
    is_60fps = fps >= 45
    fps_tag = "60" if is_60fps else ""

    if height >= 2160:
        return f"2160p{fps_tag} 4K"
    elif height >= 1440:
        return f"1440p{fps_tag} QHD"
    elif height >= 1080:
        return f"1080p{fps_tag} Full HD"
    elif height >= 720:
        return f"720p{fps_tag} HD"
    elif height >= 480:
        return f"480p{fps_tag}"
    elif height >= 360:
        return f"360p{fps_tag}"
    elif height >= 240:
        return f"240p{fps_tag}"
    else:
        return f"{height}p{fps_tag}"


def _format_sort_key(fmt: Dict[str, Any]) -> tuple:
    """Sorting key to pick the optimal format for a given resolution & fps group."""
    ext = fmt.get("ext", "").lower()
    vcodec = fmt.get("vcodec", "").lower()
    acodec = fmt.get("acodec", "").lower()
    filesize = fmt.get("filesize") or fmt.get("filesize_approx") or 0
    tbr = fmt.get("tbr") or 0.0

    # Progressive format (has both video & audio) bonus
    is_progressive = 1 if (vcodec != "none" and acodec != "none") else 0
    # Preference for mp4 container
    is_mp4 = 1 if ext == "mp4" else 0
    # Preference for standard H.264 (avc1) or modern compatible codecs
    is_common_codec = 1 if ("avc" in vcodec or "av01" in vcodec or "vp09" in vcodec) else 0
    has_explicit_size = 1 if filesize > 0 else 0

    return (is_mp4, is_progressive, has_explicit_size, is_common_codec, filesize or tbr)


def _estimate_format_bytes(fmt: Optional[Dict[str, Any]], duration: Optional[int]) -> int:
    """Return explicit filesize if present, else estimate from bitrate (tbr/vbr) and duration."""
    if not fmt:
        return 0
    filesize = fmt.get("filesize") or fmt.get("filesize_approx")
    if filesize and filesize > 0:
        return filesize

    tbr = fmt.get("tbr") or fmt.get("vbr") or fmt.get("abr")
    if tbr and tbr > 0 and duration and duration > 0:
        return int((tbr * 1000.0 * duration) / 8.0)

    return 0


def parse_and_normalize_formats(info_dict: Dict[str, Any], has_ffmpeg: bool, duration: Optional[int] = 0) -> List[FormatOption]:
    """
    Parse raw yt-dlp format dictionaries into a clean, normalized list of FormatOptions.
    Groups formats by height and frame rate (e.g. 1080p60 vs 1080p30).
    """
    raw_formats = info_dict.get("formats", [])
    if not raw_formats:
        raw_formats = [info_dict]

    # Group video formats by (height, fps_bucket)
    # fps_bucket: 60 if fps >= 45 else 30
    quality_groups: Dict[tuple, List[Dict[str, Any]]] = {}
    best_audio_format: Optional[Dict[str, Any]] = None

    for fmt in raw_formats:
        vcodec = fmt.get("vcodec", "none")
        acodec = fmt.get("acodec", "none")
        height = fmt.get("height")
        fps = fmt.get("fps") or 0.0
        format_id = fmt.get("format_id", "")

        # Skip storyboards or invalid items
        if not format_id or "storyboard" in format_id or (vcodec == "none" and acodec == "none"):
            continue

        # Audio-only format tracking
        if vcodec == "none" and acodec != "none":
            if not best_audio_format or (fmt.get("tbr") or 0) > (best_audio_format.get("tbr") or 0):
                best_audio_format = fmt
            continue

        # Video format (must have valid height)
        if height and height > 0:
            fps_bucket = 60 if fps >= 45 else 30
            group_key = (height, fps_bucket)
            if group_key not in quality_groups:
                quality_groups[group_key] = []
            quality_groups[group_key].append(fmt)

    options: List[FormatOption] = []

    # Sort available (height, fps_bucket) groups descending
    sorted_keys = sorted(quality_groups.keys(), key=lambda k: (k[0], k[1]), reverse=True)

    for group_key in sorted_keys:
        h, fps_b = group_key
        fmts = quality_groups[group_key]
        best_fmt = max(fmts, key=_format_sort_key)

        format_id = str(best_fmt.get("format_id", ""))
        ext = best_fmt.get("ext", "mp4").lower()
        width = best_fmt.get("width") or 0
        fps = best_fmt.get("fps") or float(fps_b)
        vcodec = best_fmt.get("vcodec") or ""
        acodec = best_fmt.get("acodec") or ""

        label = _get_resolution_label(h, fps)
        is_progressive = (acodec != "none")
        requires_ffmpeg = not is_progressive

        # Estimate video and audio stream sizes
        v_bytes = _estimate_format_bytes(best_fmt, duration)
        audio_bytes = _estimate_format_bytes(best_audio_format, duration) if (requires_ffmpeg and best_audio_format) else 0

        combined_bytes = (v_bytes + audio_bytes) if (v_bytes > 0 or audio_bytes > 0) else None

        size_str = format_bytes(combined_bytes)
        ext_upper = ext.upper()
        
        if size_str:
            display_text = f"{label} ({size_str}) - {ext_upper}"
            pill_label = f"{label} ({size_str})"
        else:
            display_text = f"{label} - {ext_upper}"
            pill_label = label

        opt = FormatOption(
            format_id=format_id,
            video_format_id=format_id,
            audio_format_id=str(best_audio_format.get("format_id", "")) if best_audio_format else "",
            resolution_label=pill_label,
            height=h,
            width=width,
            ext=ext if is_progressive else "mp4",
            fps=fps,
            vcodec=vcodec,
            acodec=acodec,
            filesize=combined_bytes if combined_bytes else 0,
            filesize_approx=combined_bytes if combined_bytes else 0,
            is_audio_only=False,
            requires_ffmpeg=requires_ffmpeg,
            display_text=display_text
        )
        options.append(opt)

    # Add Audio-Only options
    best_audio_id = str(best_audio_format.get("format_id", "bestaudio")) if best_audio_format else "bestaudio"
    audio_ext = best_audio_format.get("ext", "m4a") if best_audio_format else "m4a"
    audio_bytes_val = _estimate_format_bytes(best_audio_format, duration) if best_audio_format else 0
    audio_size = format_bytes(audio_bytes_val)
    
    if audio_size:
        audio_display = f"Audio Only - {audio_ext.upper()} ({audio_size})"
        audio_pill = f"Audio ({audio_size})"
    else:
        audio_display = f"Audio Only - {audio_ext.upper()}"
        audio_pill = "Audio"

    options.append(FormatOption(
        format_id=best_audio_id,
        audio_format_id=best_audio_id,
        resolution_label=audio_pill,
        ext=audio_ext,
        acodec=best_audio_format.get("acodec", "audio") if best_audio_format else "audio",
        filesize=audio_bytes_val,
        filesize_approx=audio_bytes_val,
        is_audio_only=True,
        is_mp3_convert=False,
        requires_ffmpeg=False,
        display_text=audio_display
    ))

    # Add MP3 conversion option if FFmpeg is available
    if has_ffmpeg:
        options.append(FormatOption(
            format_id=best_audio_id,
            audio_format_id=best_audio_id,
            resolution_label="Audio (MP3)",
            ext="mp3",
            acodec="mp3",
            filesize=audio_bytes_val,
            filesize_approx=audio_bytes_val,
            is_audio_only=True,
            is_mp3_convert=True,
            requires_ffmpeg=True,
            display_text=f"Audio Only - MP3 ({audio_size})" if audio_size else "Audio Only - MP3"
        ))

    return options


def select_default_format_index(options: List[FormatOption]) -> int:
    """
    Select a sensible default format index:
    Prefers 1080p Full HD. If absent, prefers highest resolution <= 1080p.
    """
    if not options:
        return 0

    # 1. Search for exact 1080p
    for idx, opt in enumerate(options):
        if opt.height == 1080:
            return idx

    # 2. Search for highest quality <= 1080p (excluding audio only)
    for idx, opt in enumerate(options):
        if not opt.is_audio_only and 0 < opt.height <= 1080:
            return idx

    # 3. Fall back to first available video option
    for idx, opt in enumerate(options):
        if not opt.is_audio_only:
            return idx

    return 0


def fetch_video_info(url: str, has_ffmpeg: bool) -> VideoInfo:
    """
    Fetch metadata for given URL using yt-dlp Python API without downloading media.
    Raises descriptive exceptions on invalid/unsupported/private URLs.
    """
    clean_url = url.strip()
    if not clean_url:
        raise ValueError("Please enter a valid video URL.")

    ydl_opts = {
        "extract_flat": False,
        "skip_download": True,
        "quiet": True,
        "no_warnings": True,
        "nocheckcertificate": True,
        "ignoreerrors": False,
    }

    logger.info(f"Extracting info for URL: {clean_url}")

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(clean_url, download=False)
            
        if not info_dict:
            raise ValueError("No video metadata could be extracted from this URL.")

        # Extract primary metadata fields
        video_id = info_dict.get("id", "")
        title = info_dict.get("title", "Untitled Video")
        uploader = info_dict.get("uploader") or info_dict.get("channel") or info_dict.get("uploader_id") or "Unknown Uploader"
        duration = info_dict.get("duration")
        view_count = info_dict.get("view_count")
        upload_date = info_dict.get("upload_date")
        thumbnail_url = info_dict.get("thumbnail")

        # Parse normalized options
        options = parse_and_normalize_formats(info_dict, has_ffmpeg=has_ffmpeg, duration=duration)
        if not options:
            raise ValueError("No downloadable video or audio streams were found for this URL.")

        default_idx = select_default_format_index(options)

        video_info = VideoInfo(
            url=clean_url,
            id=video_id,
            title=title,
            uploader=uploader,
            duration=duration,
            view_count=view_count,
            upload_date=upload_date,
            thumbnail_url=thumbnail_url,
            formats=options,
            default_format_index=default_idx
        )
        return video_info

    except yt_dlp.utils.DownloadError as e:
        err_msg = str(e)
        logger.error(f"yt-dlp DownloadError: {err_msg}")
        if "Sign in to confirm" in err_msg or "private" in err_msg.lower():
            raise ValueError("This video is private, age-restricted, or requires account authentication.")
        elif "is not a valid URL" in err_msg or "Unsupported URL" in err_msg:
            raise ValueError("The provided URL is invalid or unsupported.")
        elif "Video unavailable" in err_msg:
            raise ValueError("This video is unavailable or has been removed.")
        else:
            raise ValueError(f"Failed to access video: {err_msg.split(';')[-1].strip()}")
    except Exception as e:
        logger.error(f"Unexpected error in metadata extraction: {e}", exc_info=True)
        if isinstance(e, ValueError):
            raise e
        raise ValueError(f"Could not fetch video information: {str(e)}")
