"""
Download runner executing yt-dlp downloads on background threads with real-time progress & post-processing hooks.
"""

import os
import logging
import threading
from pathlib import Path
from typing import Callable, Optional
import requests
import yt_dlp

from app.config import DOWNLOADS_DIR
from app.models import DownloadProgress, FormatOption, VideoInfo, PlaylistInfo, PlaylistItem
from app.utils import find_ffmpeg, format_bytes, format_eta, format_speed, sanitize_filename

logger = logging.getLogger(__name__)


class Downloader:
    """Manages threaded media downloading using yt-dlp with cancel support."""

    def __init__(self):
        self._cancel_event = threading.Event()
        self._is_downloading = False
        self._worker_thread: Optional[threading.Thread] = None

    @property
    def is_downloading(self) -> bool:
        return self._is_downloading

    def cancel(self):
        """Signal cancellation for active download."""
        if self._is_downloading:
            logger.info("Cancel requested by user.")
            self._cancel_event.set()

    def download_async(
        self,
        video_info: VideoInfo,
        selected_format: FormatOption,
        on_progress: Callable[[DownloadProgress], None],
        on_complete: Callable[[str], None],
        on_error: Callable[[str], None],
    ):
        """Launch download in a separate worker thread."""
        if self._is_downloading:
            logger.warning("Download already in progress.")
            return

        self._cancel_event.clear()
        self._is_downloading = True

        self._worker_thread = threading.Thread(
            target=self._run_download,
            args=(video_info, selected_format, on_progress, on_complete, on_error),
            daemon=True,
        )
        self._worker_thread.start()

    def _run_download(
        self,
        video_info: VideoInfo,
        selected_format: FormatOption,
        on_progress: Callable[[DownloadProgress], None],
        on_complete: Callable[[str], None],
        on_error: Callable[[str], None],
    ):
        output_filepath = ""
        ffmpeg_dir = find_ffmpeg()

        # Build format selector string
        if selected_format.is_audio_only:
            format_spec = selected_format.format_id or "bestaudio/best"
        elif selected_format.requires_ffmpeg:
            format_spec = f"{selected_format.video_format_id}+bestaudio/best"
        else:
            format_spec = selected_format.format_id or "best"

        out_template = str(DOWNLOADS_DIR / "%(title)s.%(ext)s")

        ydl_opts = {
            "format": format_spec,
            "outtmpl": out_template,
            "quiet": True,
            "no_warnings": True,
            "no_color": True,
            "nocheckcertificate": True,
            "ignoreerrors": False,
            "restrictfilenames": False,
            "concurrent_fragment_downloads": 8,
            "buffersize": 1024 * 1024,
            "http_chunk_size": 10485760,
            "retries": 10,
            "fragment_retries": 10,
            "progress_hooks": [lambda d: self._progress_hook(d, on_progress)],
            "postprocessor_hooks": [lambda d: self._postprocessor_hook(d, on_progress)],
        }

        if ffmpeg_dir:
            ydl_opts["ffmpeg_location"] = ffmpeg_dir

        # Handle postprocessor configuration for MP3 conversion
        if selected_format.is_audio_only and selected_format.is_mp3_convert:
            ydl_opts["postprocessors"] = [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ]
        elif selected_format.requires_ffmpeg:
            # Force MP4 container output when merging video + audio
            ydl_opts["merge_output_format"] = "mp4"

        logger.info(f"Starting download for {video_info.url} with format string: {format_spec}")
        self._expected_total_bytes = selected_format.get_estimated_bytes() or 0
        self._stream1_bytes = 0
        self._stream1_total = 0

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_info.url, download=True)
                
                if info:
                    if "requested_downloads" in info and len(info["requested_downloads"]) > 0:
                        output_filepath = info["requested_downloads"][0].get("filepath", "")
                    if not output_filepath:
                        output_filepath = ydl.prepare_filename(info)

            if self._cancel_event.is_set():
                logger.info("Download was cancelled during execution.")
                on_progress(DownloadProgress(status="Download cancelled", is_cancelled=True))
                return

            if output_filepath and Path(output_filepath).exists():
                final_path_str = str(Path(output_filepath).resolve())
                logger.info(f"Download completed successfully: {final_path_str}")
                on_complete(final_path_str)
            else:
                # Find recent file in downloads directory matching title
                latest_files = list(DOWNLOADS_DIR.glob("*"))
                if latest_files:
                    newest = max(latest_files, key=os.path.getmtime)
                    on_complete(str(newest.resolve()))
                else:
                    on_complete(str(DOWNLOADS_DIR.resolve()))

        except yt_dlp.utils.DownloadCancelled:
            logger.info("Caught DownloadCancelled exception from yt-dlp.")
            on_progress(DownloadProgress(status="Download cancelled", is_cancelled=True))
        except Exception as e:
            if self._cancel_event.is_set():
                logger.info("Exception raised during cancel flow.")
                on_progress(DownloadProgress(status="Download cancelled", is_cancelled=True))
            else:
                err_msg = str(e)
                logger.error(f"Download error: {err_msg}", exc_info=True)
                
                # Friendly error transformation
                if "FFmpeg" in err_msg or "ffmpeg" in err_msg:
                    friendly_error = "FFmpeg is required to combine video and audio streams for this quality option."
                elif "Permission denied" in err_msg:
                    friendly_error = "Permission denied while writing output file. Please check folder write permissions."
                else:
                    friendly_error = f"Download failed: {err_msg.split(';')[-1].strip()}"
                
                on_error(friendly_error)
        finally:
            self._is_downloading = False

    def _progress_hook(self, d: dict, on_progress: Callable[[DownloadProgress], None]):
        """Callback invoked periodically by yt-dlp during file download."""
        if self._cancel_event.is_set():
            raise yt_dlp.utils.DownloadCancelled("Download cancelled by user.")

        status_code = d.get("status")

        if status_code == "downloading":
            raw_downloaded = d.get("downloaded_bytes", 0)
            raw_total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0

            stream1_bytes = getattr(self, "_stream1_bytes", 0)
            stream1_total = getattr(self, "_stream1_total", 0)

            downloaded = stream1_bytes + raw_downloaded
            if stream1_total > 0 and raw_total > 0:
                total = stream1_total + raw_total
            else:
                total = max(getattr(self, "_expected_total_bytes", 0), raw_total + stream1_bytes)

            speed = d.get("speed") or 0.0
            eta = d.get("eta")

            pct = (downloaded / total * 100.0) if total > 0 else 0.0
            speed_str = format_speed(speed)
            eta_str = format_eta(eta)
            filename = Path(d.get("filename", "")).name

            progress = DownloadProgress(
                status="Downloading...",
                downloaded_bytes=downloaded,
                total_bytes=total,
                percentage=min(pct, 99.9),
                speed_str=speed_str,
                eta_str=eta_str,
                filename=filename,
            )
            on_progress(progress)

        elif status_code == "finished":
            filename = Path(d.get("filename", "")).name
            finished_bytes = d.get("downloaded_bytes") or d.get("total_bytes") or 0
            finished_total = d.get("total_bytes") or d.get("total_bytes_estimate") or finished_bytes

            if getattr(self, "_stream1_bytes", 0) == 0:
                self._stream1_bytes = finished_bytes
                self._stream1_total = finished_total
                current_total = max(getattr(self, "_expected_total_bytes", 0), finished_total)
                pct = (finished_bytes / current_total * 100.0) if current_total > 0 else 50.0

                progress = DownloadProgress(
                    status="Downloading audio stream...",
                    downloaded_bytes=finished_bytes,
                    total_bytes=current_total,
                    percentage=min(pct, 95.0),
                    filename=filename,
                )
                on_progress(progress)

    def _postprocessor_hook(self, d: dict, on_progress: Callable[[DownloadProgress], None]):
        """Callback invoked by yt-dlp during FFmpeg postprocessing operations."""
        if self._cancel_event.is_set():
            raise yt_dlp.utils.DownloadCancelled("Download cancelled by user.")

        pp_status = d.get("status")
        pp_name = d.get("postprocessor", "")

        if pp_status == "started":
            status_text = "Merging video and audio..." if "Merger" in pp_name or "FFmpeg" in pp_name else "Processing media..."
            progress = DownloadProgress(
                status=status_text,
                percentage=99.0,
            )
            on_progress(progress)
        elif pp_status == "finished":
            progress = DownloadProgress(
                status="Finalizing output file...",
                percentage=99.9,
            )
            on_progress(progress)

    def download_playlist_async(
        self,
        playlist_info: PlaylistInfo,
        on_progress: Callable[[DownloadProgress], None],
        on_complete: Callable[[str], None],
        on_error: Callable[[str], None],
        on_item_status_change: Optional[Callable[[int, str], None]] = None,
    ):
        """Launch playlist download queue in a separate worker thread."""
        if self._is_downloading:
            logger.warning("Download already in progress.")
            return

        self._cancel_event.clear()
        self._is_downloading = True

        self._worker_thread = threading.Thread(
            target=self._run_playlist_download,
            args=(playlist_info, on_progress, on_complete, on_error, on_item_status_change),
            daemon=True,
        )
        self._worker_thread.start()

    def _run_playlist_download(
        self,
        playlist_info: PlaylistInfo,
        on_progress: Callable[[DownloadProgress], None],
        on_complete: Callable[[str], None],
        on_error: Callable[[str], None],
        on_item_status_change: Optional[Callable[[int, str], None]] = None,
    ):
        ffmpeg_dir = find_ffmpeg()
        selected_items = [item for item in playlist_info.items if item.is_selected]

        if not selected_items:
            self._is_downloading = False
            on_error("No videos selected for playlist download.")
            return

        # Dedicated playlist folder: downloads/Playlist Title/
        clean_folder_name = sanitize_filename(playlist_info.title)
        playlist_dir = DOWNLOADS_DIR / clean_folder_name
        playlist_dir.mkdir(parents=True, exist_ok=True)

        total_selected = len(selected_items)
        logger.info(f"Starting playlist download ({total_selected} videos) to folder: {playlist_dir}")

        for idx, item in enumerate(selected_items, start=1):
            if self._cancel_event.is_set():
                logger.info("Playlist download cancelled.")
                on_progress(DownloadProgress(status="Playlist download cancelled", is_cancelled=True))
                self._is_downloading = False
                return

            if on_item_status_change:
                on_item_status_change(item.index, "Downloading...")

            on_progress(
                DownloadProgress(
                    status=f"Downloading Video {idx} of {total_selected}: {item.title[:28]}...",
                    percentage=0.0,
                    current_item_index=idx,
                    total_items=total_selected,
                )
            )

            selected_format = item.get_selected_format()
            if not selected_format:
                if on_item_status_change:
                    on_item_status_change(item.index, "Skipped")
                continue

            format_spec = selected_format.format_id
            if selected_format.requires_ffmpeg and selected_format.video_format_id and selected_format.audio_format_id:
                format_spec = f"{selected_format.video_format_id}+{selected_format.audio_format_id}"

            padded_index = f"{item.index:02d}"
            clean_item_title = sanitize_filename(item.title)
            out_template = str(playlist_dir / f"{padded_index} - {clean_item_title}.%(ext)s")

            ydl_opts = {
                "format": format_spec,
                "outtmpl": out_template,
                "quiet": True,
                "no_warnings": True,
                "no_color": True,
                "nocheckcertificate": True,
                "ignoreerrors": False,
                "restrictfilenames": False,
                "concurrent_fragment_downloads": 8,
                "buffersize": 1024 * 1024,
                "http_chunk_size": 10485760,
                "retries": 10,
                "fragment_retries": 10,
                "progress_hooks": [
                    lambda d, item_idx=idx, t=item.title: self._playlist_item_progress_hook(d, item_idx, total_selected, t, on_progress)
                ],
            }

            if ffmpeg_dir:
                ydl_opts["ffmpeg_location"] = ffmpeg_dir

            if selected_format.is_audio_only and selected_format.is_mp3_convert:
                ydl_opts["postprocessors"] = [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "192",
                    }
                ]
            elif selected_format.requires_ffmpeg:
                ydl_opts["merge_output_format"] = "mp4"

            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([item.url])

                if on_item_status_change:
                    on_item_status_change(item.index, "Completed ✓")
            except Exception as e:
                logger.error(f"Error downloading playlist item {item.index} ({item.title}): {e}")
                if on_item_status_change:
                    on_item_status_change(item.index, "Failed")

        self._is_downloading = False
        if not self._cancel_event.is_set():
            on_complete(str(playlist_dir.resolve()))

    def _playlist_item_progress_hook(
        self,
        d: dict,
        current_idx: int,
        total_items: int,
        title: str,
        on_progress: Callable[[DownloadProgress], None],
    ):
        if self._cancel_event.is_set():
            raise yt_dlp.utils.DownloadCancelled("Playlist download cancelled by user.")

        status_code = d.get("status")
        if status_code == "downloading":
            raw_downloaded = d.get("downloaded_bytes", 0)
            raw_total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0

            speed = d.get("speed") or 0.0
            eta = d.get("eta")

            item_pct = (raw_downloaded / raw_total * 100.0) if raw_total > 0 else 0.0

            progress = DownloadProgress(
                status=f"Downloading Video {current_idx} of {total_items}: {title[:28]}...",
                downloaded_bytes=raw_downloaded,
                total_bytes=raw_total,
                percentage=min(item_pct, 99.9),
                speed_str=format_speed(speed),
                eta_str=format_eta(eta),
                filename=title,
                current_item_index=current_idx,
                total_items=total_items,
            )
            on_progress(progress)

    def download_thumbnail_async(
        self,
        title: str,
        thumbnail_url: str,
        video_id: str = "",
        output_dir: Optional[Path] = None,
        on_complete: Optional[Callable[[str], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
    ):
        """Launch high resolution thumbnail download in a background worker thread."""
        if not thumbnail_url and not video_id:
            if on_error:
                on_error("No thumbnail image available for this video.")
            return

        threading.Thread(
            target=self._run_thumbnail_download,
            args=(title, thumbnail_url, video_id, output_dir or DOWNLOADS_DIR, on_complete, on_error),
            daemon=True,
        ).start()

    def _run_thumbnail_download(
        self,
        title: str,
        thumbnail_url: str,
        video_id: str,
        target_dir: Path,
        on_complete: Optional[Callable[[str], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
    ):
        try:
            target_dir.mkdir(parents=True, exist_ok=True)

            best_url = thumbnail_url
            if video_id:
                candidates = [
                    f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg",
                    f"https://img.youtube.com/vi_webp/{video_id}/maxresdefault.webp",
                    f"https://img.youtube.com/vi/{video_id}/sddefault.jpg",
                ]
                for candidate in candidates:
                    try:
                        res_head = requests.head(candidate, timeout=3)
                        if res_head.status_code == 200 and int(res_head.headers.get("Content-Length", 0) or 0) > 5000:
                            best_url = candidate
                            break
                    except Exception:
                        pass

            response = requests.get(best_url, timeout=10)
            if response.status_code == 200:
                clean_title = sanitize_filename(title)
                ext = ".jpg"
                if ".webp" in best_url.lower():
                    ext = ".webp"
                elif ".png" in best_url.lower():
                    ext = ".png"

                out_path = target_dir / f"{clean_title}_thumbnail{ext}"
                out_path.write_bytes(response.content)

                if on_complete:
                    on_complete(str(out_path.resolve()))
            else:
                if on_error:
                    on_error(f"HTTP Error {response.status_code} fetching thumbnail.")
        except Exception as e:
            logger.error(f"Error downloading thumbnail: {e}")
            if on_error:
                on_error(f"Could not download thumbnail image: {str(e)}")
