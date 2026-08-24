"""
CustomTkinter graphical user interface for the Media Downloader application.
Supports single video media and YouTube playlists.
"""

import io
import logging
import threading
from typing import Dict, List, Optional
from pathlib import Path

import customtkinter as ctk
import requests
from PIL import Image, ImageTk

from app.config import (
    APP_TITLE,
    COLORS,
    DOWNLOADS_DIR,
    MIN_HEIGHT,
    MIN_WIDTH,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
)
from app.downloader import Downloader
from app.metadata import fetch_video_info, fetch_playlist_info, is_playlist_url
from app.models import DownloadProgress, FormatOption, VideoInfo, PlaylistInfo, PlaylistItem
from app.utils import (
    find_ffmpeg,
    format_bytes,
    format_count,
    format_date,
    format_duration,
    open_folder,
    sanitize_filename,
)

logger = logging.getLogger(__name__)


class MediaDownloaderApp(ctk.CTk):
    """Main application window managing UI layout, threads, and user interaction."""

    def __init__(self):
        super().__init__()

        # Window Configuration
        self.title(APP_TITLE)
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.minsize(MIN_WIDTH, MIN_HEIGHT)

        # Center Window on Screen
        self._center_window()

        # State Variables
        self._has_ffmpeg = find_ffmpeg() is not None
        self._current_video_info: Optional[VideoInfo] = None
        self._current_playlist_info: Optional[PlaylistInfo] = None
        self._is_playlist = False
        self._selected_format: Optional[FormatOption] = None
        self._downloader = Downloader()
        self._is_fetching = False
        self._pill_buttons: List[tuple] = []
        self._playlist_item_widgets: Dict[int, Dict] = {}
        self._last_download_path: str = str(DOWNLOADS_DIR)

        # Build UI Components
        self._setup_layout()
        self._setup_header()
        self._setup_url_input_section()
        self._setup_status_banner()
        self._setup_video_info_card()
        self._setup_playlist_card()
        self._setup_download_section()
        self._setup_ffmpeg_notice()

        logger.info("MediaDownloaderApp initialized successfully.")

    def _center_window(self):
        """Center the application window on screen."""
        self.update_idletasks()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - WINDOW_WIDTH) // 2
        y = (screen_height - WINDOW_HEIGHT) // 2
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}+{x}+{y}")

    def _setup_layout(self):
        """Configure main scrollable container layout grid."""
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.main_container = ctk.CTkScrollableFrame(
            self,
            fg_color=COLORS["bg_dark"],
            corner_radius=0,
        )
        self.main_container.grid(row=0, column=0, sticky="nsew")
        self.main_container.grid_columnconfigure(0, weight=1)

    def _setup_header(self):
        """Create application header with title and subtitle."""
        header_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        header_frame.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")

        title_label = ctk.CTkLabel(
            header_frame,
            text=APP_TITLE,
            font=ctk.CTkFont(size=26, weight="bold"),
            text_color=COLORS["text_main"],
            anchor="w",
        )
        title_label.pack(anchor="w")

        subtitle_label = ctk.CTkLabel(
            header_frame,
            text="Download your permitted media and playlists in the quality you choose",
            font=ctk.CTkFont(size=14),
            text_color=COLORS["text_muted"],
            anchor="w",
        )
        subtitle_label.pack(anchor="w", pady=(2, 0))

    def _setup_url_input_section(self):
        """Create URL entry box, clear button, and Fetch button."""
        input_card = ctk.CTkFrame(
            self.main_container,
            fg_color=COLORS["card_bg"],
            border_color=COLORS["card_border"],
            border_width=1,
            corner_radius=12,
        )
        input_card.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        input_card.grid_columnconfigure(0, weight=1)

        entry_container = ctk.CTkFrame(input_card, fg_color="transparent")
        entry_container.grid(row=0, column=0, padx=15, pady=15, sticky="ew")
        entry_container.grid_columnconfigure(0, weight=1)

        self.url_entry = ctk.CTkEntry(
            entry_container,
            placeholder_text="Paste YouTube video or playlist URL, or Instagram Reel link here...",
            height=44,
            font=ctk.CTkFont(size=13),
            fg_color=COLORS["input_bg"],
            border_color=COLORS["card_border"],
            border_width=1,
            corner_radius=10,
        )
        self.url_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.url_entry.bind("<Return>", lambda event: self._on_fetch_clicked())

        self.clear_btn = ctk.CTkButton(
            entry_container,
            text="✕",
            width=40,
            height=44,
            fg_color=COLORS["input_bg"],
            hover_color=COLORS["card_border"],
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._on_clear_url,
            corner_radius=10,
        )
        self.clear_btn.grid(row=0, column=1, padx=(0, 10))

        self.fetch_btn = ctk.CTkButton(
            entry_container,
            text="Fetch Media",
            height=44,
            width=135,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=COLORS["accent_primary"],
            hover_color=COLORS["accent_hover"],
            command=self._on_fetch_clicked,
            corner_radius=10,
        )
        self.fetch_btn.grid(row=0, column=2)

    def _setup_status_banner(self):
        """Create banner displaying application status and user feedback."""
        self.status_banner = ctk.CTkFrame(
            self.main_container,
            fg_color="#181B22",
            border_color=COLORS["card_border"],
            border_width=1,
            corner_radius=8,
            height=40,
        )
        self.status_banner.grid(row=2, column=0, padx=20, pady=(0, 15), sticky="ew")
        self.status_banner.grid_columnconfigure(0, weight=1)

        self.status_label = ctk.CTkLabel(
            self.status_banner,
            text="Ready — Paste a URL and click 'Fetch Media'",
            font=ctk.CTkFont(size=13),
            text_color=COLORS["text_muted"],
            anchor="w",
        )
        self.status_label.grid(row=0, column=0, padx=15, pady=8, sticky="w")

    def _setup_video_info_card(self):
        """Create single video metadata card with thumbnail preview and format selection."""
        self.info_card = ctk.CTkFrame(
            self.main_container,
            fg_color=COLORS["card_bg"],
            border_color=COLORS["card_border"],
            border_width=1,
            corner_radius=12,
        )
        self.info_card.grid(row=3, column=0, padx=20, pady=(0, 15), sticky="ew")
        self.info_card.grid_columnconfigure(1, weight=1)

        # 1. Thumbnail Container
        self.thumb_frame = ctk.CTkFrame(
            self.info_card,
            width=240,
            height=135,
            fg_color=COLORS["bg_dark"],
            corner_radius=8,
        )
        self.thumb_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nw")
        self.thumb_frame.grid_propagate(False)

        self.thumb_label = ctk.CTkLabel(
            self.thumb_frame,
            text="No Video Loaded",
            text_color=COLORS["text_muted"],
            font=ctk.CTkFont(size=12),
        )
        self.thumb_label.place(relx=0.5, rely=0.5, anchor="center")

        # 2. Video Details Container
        details_frame = ctk.CTkFrame(self.info_card, fg_color="transparent")
        details_frame.grid(row=0, column=1, padx=(0, 20), pady=20, sticky="nsew")
        details_frame.grid_columnconfigure(0, weight=1)

        self.title_label = ctk.CTkLabel(
            details_frame,
            text="Media title will appear here...",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=COLORS["text_main"],
            anchor="w",
            wraplength=650,
            justify="left",
        )
        self.title_label.pack(anchor="w", pady=(0, 4))

        self.uploader_label = ctk.CTkLabel(
            details_frame,
            text="Channel: --",
            font=ctk.CTkFont(size=13),
            text_color=COLORS["text_muted"],
            anchor="w",
        )
        self.uploader_label.pack(anchor="w", pady=(0, 4))

        self.meta_row = ctk.CTkLabel(
            details_frame,
            text="Duration: --:--   •   Views: --   •   Uploaded: --",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_muted"],
            anchor="w",
        )
        self.meta_row.pack(anchor="w")

        # 3. Quality Selection Sub-section
        quality_frame = ctk.CTkFrame(self.info_card, fg_color="transparent")
        quality_frame.grid(row=1, column=0, columnspan=2, padx=20, pady=(0, 20), sticky="ew")
        quality_frame.grid_columnconfigure(0, weight=1)

        self.quality_title_label = ctk.CTkLabel(
            quality_frame,
            text="Select Download Quality:",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLORS["text_main"],
            anchor="w",
        )
        self.quality_title_label.pack(anchor="w", pady=(0, 8))

        self.quality_dropdown = ctk.CTkOptionMenu(
            quality_frame,
            values=["Fetch video to populate qualities"],
            command=self._on_quality_selected,
            height=36,
            font=ctk.CTkFont(size=13),
            fg_color="#262A34",
            button_color=COLORS["accent_primary"],
            button_hover_color=COLORS["accent_hover"],
            corner_radius=8,
        )
        self.quality_dropdown.pack(fill="x", pady=(0, 10))

        # Quick Quality Pills Container
        self.pills_frame = ctk.CTkFrame(quality_frame, fg_color="transparent")
        self.pills_frame.pack(fill="x")

    def _setup_playlist_card(self):
        """Create UI container frame for YouTube playlist view."""
        self.playlist_card = ctk.CTkFrame(
            self.main_container,
            fg_color=COLORS["card_bg"],
            border_color=COLORS["card_border"],
            border_width=1,
            corner_radius=12,
        )

        # 1. Playlist Header Frame
        header_frame = ctk.CTkFrame(self.playlist_card, fg_color="transparent")
        header_frame.pack(fill="x", padx=20, pady=(20, 10))

        self.playlist_thumb_frame = ctk.CTkFrame(
            header_frame,
            width=200,
            height=115,
            fg_color=COLORS["bg_dark"],
            corner_radius=8,
        )
        self.playlist_thumb_frame.pack(side="left", padx=(0, 15))
        self.playlist_thumb_frame.pack_propagate(False)

        self.playlist_thumb_label = ctk.CTkLabel(
            self.playlist_thumb_frame,
            text="Playlist",
            text_color=COLORS["text_muted"],
            font=ctk.CTkFont(size=12),
        )
        self.playlist_thumb_label.place(relx=0.5, rely=0.5, anchor="center")

        details_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        details_frame.pack(side="left", fill="both", expand=True)

        self.playlist_title_label = ctk.CTkLabel(
            details_frame,
            text="Playlist Title",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=COLORS["text_main"],
            anchor="w",
            wraplength=600,
            justify="left",
        )
        self.playlist_title_label.pack(anchor="w", pady=(0, 4))

        self.playlist_channel_label = ctk.CTkLabel(
            details_frame,
            text="Channel: Unknown Channel",
            font=ctk.CTkFont(size=13),
            text_color=COLORS["text_muted"],
            anchor="w",
        )
        self.playlist_channel_label.pack(anchor="w", pady=(0, 4))

        self.playlist_meta_label = ctk.CTkLabel(
            details_frame,
            text="Playlist • 0 Videos",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLORS["status_info"],
            anchor="w",
        )
        self.playlist_meta_label.pack(anchor="w")

        # 2. Master Batch Quality & Controls Frame
        batch_bar = ctk.CTkFrame(self.playlist_card, fg_color=COLORS["bg_dark"], corner_radius=8)
        batch_bar.pack(fill="x", padx=20, pady=(5, 10))

        self.playlist_select_all_var = ctk.BooleanVar(value=True)
        self.playlist_select_all_cb = ctk.CTkCheckBox(
            batch_bar,
            text="Select All Videos",
            variable=self.playlist_select_all_var,
            command=self._on_playlist_toggle_all,
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLORS["text_main"],
        )
        self.playlist_select_all_cb.pack(side="left", padx=15, pady=10)

        global_q_label = ctk.CTkLabel(
            batch_bar,
            text="Global Quality (1-Click All):",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_muted"],
        )
        global_q_label.pack(side="left", padx=(15, 5), pady=10)

        self.playlist_global_quality_dropdown = ctk.CTkOptionMenu(
            batch_bar,
            values=["1080p Full HD", "720p HD", "480p", "360p", "Audio Only (M4A)", "Audio Only (MP3)"],
            command=self._on_playlist_global_quality_change,
            width=180,
            fg_color=COLORS["accent_primary"],
            button_color=COLORS["accent_hover"],
        )
        self.playlist_global_quality_dropdown.pack(side="left", padx=5, pady=10)

        # 3. Scrollable Table for Playlist Videos
        self.playlist_scroll_frame = ctk.CTkScrollableFrame(
            self.playlist_card,
            height=280,
            fg_color="transparent",
        )
        self.playlist_scroll_frame.pack(fill="both", expand=True, padx=15, pady=(0, 15))

    def _setup_download_section(self):
        """Create Download button, Cancel button, Open Folder button, and Progress Bar."""
        download_card = ctk.CTkFrame(
            self.main_container,
            fg_color=COLORS["card_bg"],
            border_color=COLORS["card_border"],
            border_width=1,
            corner_radius=12,
        )
        download_card.grid(row=4, column=0, padx=20, pady=(0, 15), sticky="ew")
        download_card.grid_columnconfigure(0, weight=1)

        # Buttons Control Row
        btn_row = ctk.CTkFrame(download_card, fg_color="transparent")
        btn_row.grid(row=0, column=0, padx=20, pady=(20, 15), sticky="ew")

        self.download_btn = ctk.CTkButton(
            btn_row,
            text="Start Download",
            height=44,
            width=160,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=COLORS["accent_primary"],
            hover_color=COLORS["accent_hover"],
            state="disabled",
            command=self._on_download_clicked,
            corner_radius=8,
        )
        self.download_btn.pack(side="left", padx=(0, 10))

        self.cancel_btn = ctk.CTkButton(
            btn_row,
            text="Cancel",
            height=44,
            width=110,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=COLORS["accent_danger"],
            hover_color=COLORS["accent_danger_hover"],
            state="disabled",
            command=self._on_cancel_clicked,
            corner_radius=8,
        )
        self.cancel_btn.pack(side="left", padx=(0, 10))

        self.open_folder_btn = ctk.CTkButton(
            btn_row,
            text="Open Folder 📁",
            height=44,
            width=135,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=COLORS["status_success"],
            hover_color="#27AE60",
            command=self._on_open_folder_clicked,
            corner_radius=8,
        )
        # Initially hidden until download finishes
        self.open_folder_btn.pack_forget()

        # Download Progress Bar & Statistics
        progress_container = ctk.CTkFrame(download_card, fg_color="transparent")
        progress_container.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="ew")
        progress_container.grid_columnconfigure(0, weight=1)

        self.progress_bar = ctk.CTkProgressBar(
            progress_container,
            height=12,
            corner_radius=6,
            progress_color=COLORS["accent_primary"],
            fg_color="#262A34",
        )
        self.progress_bar.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        self.progress_bar.set(0.0)

        self.progress_stats_label = ctk.CTkLabel(
            progress_container,
            text="Ready to download",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_muted"],
            anchor="w",
        )
        self.progress_stats_label.grid(row=1, column=0, sticky="w")

    def _setup_ffmpeg_notice(self):
        """Create notice if FFmpeg is missing."""
        self.ffmpeg_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.ffmpeg_frame.grid(row=5, column=0, padx=20, pady=(0, 20), sticky="ew")

        if not self._has_ffmpeg:
            notice_label = ctk.CTkLabel(
                self.ffmpeg_frame,
                text="⚠️ FFmpeg binary not detected locally. High-definition 1080p+ downloads will automatically fall back to progressive qualities.",
                font=ctk.CTkFont(size=11),
                text_color=COLORS["status_warning"],
                anchor="center",
            )
            notice_label.pack()

    def _set_status(self, text: str, mode: str = "info"):
        """Update status banner text and colors dynamically."""
        color_map = {
            "info": (COLORS["text_muted"], "#12151D"),
            "working": (COLORS["status_info"], "#111C2E"),
            "success": (COLORS["status_success"], "#0E241B"),
            "warning": (COLORS["status_warning"], "#261D0F"),
            "error": (COLORS["status_error"], "#281214"),
        }
        text_color, bg_color = color_map.get(mode, color_map["info"])
        self.status_label.configure(text=text, text_color=text_color)
        self.status_banner.configure(fg_color=bg_color)

    def _on_clear_url(self):
        """Clear URL entry and reset UI state."""
        self.url_entry.delete(0, "end")
        self._reset_video_display()
        self._set_status("Ready — Paste a URL and click 'Fetch Media'")

    def _on_fetch_clicked(self):
        """Trigger background metadata extraction for single video or playlist."""
        if self._is_fetching or self._downloader.is_downloading:
            return

        url = self.url_entry.get().strip()
        if not url:
            self._set_status("Please enter a valid media URL", mode="error")
            return

        self._has_ffmpeg = find_ffmpeg() is not None

        # UI Loading State
        self._is_fetching = True
        self.fetch_btn.configure(state="disabled", text="Fetching...")
        self.url_entry.configure(state="disabled")
        self.download_btn.configure(state="disabled")
        self._set_status("Fetching media information...", mode="working")

        # Run extraction in background thread
        threading.Thread(
            target=self._fetch_metadata_worker,
            args=(url,),
            daemon=True,
        ).start()

    def _fetch_metadata_worker(self, url: str):
        """Worker thread executing yt-dlp metadata extraction."""
        try:
            if is_playlist_url(url):
                playlist_info = fetch_playlist_info(url, has_ffmpeg=self._has_ffmpeg)
                self.after(0, self._on_fetch_playlist_success, playlist_info)
            else:
                video_info = fetch_video_info(url, has_ffmpeg=self._has_ffmpeg)
                self.after(0, self._on_fetch_success, video_info)
        except Exception as e:
            err_msg = str(e)
            self.after(0, self._on_fetch_error, err_msg)

    def _on_fetch_success(self, video_info: VideoInfo):
        """Handle successful single video metadata extraction on main thread."""
        self._is_fetching = False
        self._is_playlist = False
        self.fetch_btn.configure(state="normal", text="Fetch Media")
        self.url_entry.configure(state="normal")

        self._current_video_info = video_info
        self._current_playlist_info = None
        self._render_video_metadata(video_info)
        self._set_status("Video information loaded successfully", mode="success")

        if video_info.thumbnail_url:
            threading.Thread(
                target=self._load_thumbnail_worker,
                args=(video_info.thumbnail_url,),
                daemon=True,
            ).start()
        else:
            self._render_thumbnail_placeholder()

    def _on_fetch_playlist_success(self, playlist_info: PlaylistInfo):
        """Handle successful playlist metadata extraction on main thread."""
        self._is_fetching = False
        self._is_playlist = True
        self.fetch_btn.configure(state="normal", text="Fetch Media")
        self.url_entry.configure(state="normal")

        self._current_playlist_info = playlist_info
        self._current_video_info = None
        self._render_playlist_metadata(playlist_info)
        self._set_status(f"Playlist loaded: '{playlist_info.title}' ({playlist_info.total_count} videos)", mode="success")

        if playlist_info.thumbnail_url:
            threading.Thread(
                target=self._load_playlist_thumbnail_worker,
                args=(playlist_info.thumbnail_url,),
                daemon=True,
            ).start()
        else:
            self._render_playlist_thumbnail_placeholder()

    def _on_fetch_error(self, error_message: str):
        """Handle metadata extraction failure on main thread."""
        self._is_fetching = False
        self.fetch_btn.configure(state="normal", text="Fetch Media")
        self.url_entry.configure(state="normal")

        self._reset_video_display()
        self._set_status(error_message, mode="error")

    def _load_thumbnail_worker(self, thumbnail_url: str):
        """Worker thread fetching remote thumbnail image."""
        try:
            response = requests.get(thumbnail_url, timeout=6)
            if response.status_code == 200:
                image_data = io.BytesIO(response.content)
                pil_image = Image.open(image_data)
                self.after(0, self._render_thumbnail, pil_image)
            else:
                self.after(0, self._render_thumbnail_placeholder)
        except Exception as e:
            logger.warning(f"Failed to fetch thumbnail image: {e}")
            self.after(0, self._render_thumbnail_placeholder)

    def _load_playlist_thumbnail_worker(self, thumbnail_url: str):
        """Worker thread fetching remote playlist thumbnail image."""
        try:
            response = requests.get(thumbnail_url, timeout=6)
            if response.status_code == 200:
                image_data = io.BytesIO(response.content)
                pil_image = Image.open(image_data)
                self.after(0, self._render_playlist_thumbnail, pil_image)
            else:
                self.after(0, self._render_playlist_thumbnail_placeholder)
        except Exception as e:
            logger.warning(f"Failed to fetch playlist thumbnail image: {e}")
            self.after(0, self._render_playlist_thumbnail_placeholder)

    def _load_playlist_item_thumbnails_worker(self, items: List[PlaylistItem]):
        """Worker thread asynchronously fetching small video thumbnails for playlist rows."""
        for item in items:
            if not item.thumbnail_url:
                continue
            try:
                response = requests.get(item.thumbnail_url, timeout=5)
                if response.status_code == 200:
                    image_data = io.BytesIO(response.content)
                    pil_image = Image.open(image_data)
                    self.after(0, self._render_playlist_item_thumbnail, item.index, pil_image)
            except Exception as e:
                logger.warning(f"Could not load thumbnail for playlist item {item.index}: {e}")

    def _render_playlist_item_thumbnail(self, item_index: int, pil_image: Image.Image):
        """Render small 64x36 video thumbnail in playlist item row."""
        try:
            if item_index in self._playlist_item_widgets:
                w = self._playlist_item_widgets[item_index]["thumb_label"]
                target_w, target_h = 64, 36
                pil_image.thumbnail((target_w, target_h), Image.Resampling.LANCZOS)
                ctk_img = ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=(pil_image.width, pil_image.height))
                w.configure(image=ctk_img, text="")
                w.image = ctk_img
        except Exception as e:
            logger.error(f"Error rendering item thumbnail for index {item_index}: {e}")

    def _render_thumbnail(self, pil_image: Image.Image):
        """Render thumbnail Image inside thumb_frame maintaining aspect ratio."""
        try:
            target_w, target_h = 240, 135
            pil_image.thumbnail((target_w, target_h), Image.Resampling.LANCZOS)
            ctk_img = ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=(pil_image.width, pil_image.height))

            self.thumb_label.configure(image=ctk_img, text="")
            self.thumb_label.image = ctk_img
        except Exception as e:
            logger.error(f"Error rendering thumbnail: {e}")
            self._render_thumbnail_placeholder()

    def _render_playlist_thumbnail(self, pil_image: Image.Image):
        """Render playlist thumbnail Image inside playlist_thumb_frame."""
        try:
            target_w, target_h = 200, 115
            pil_image.thumbnail((target_w, target_h), Image.Resampling.LANCZOS)
            ctk_img = ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=(pil_image.width, pil_image.height))

            self.playlist_thumb_label.configure(image=ctk_img, text="")
            self.playlist_thumb_label.image = ctk_img
        except Exception as e:
            logger.error(f"Error rendering playlist thumbnail: {e}")
            self._render_playlist_thumbnail_placeholder()

    def _render_thumbnail_placeholder(self):
        """Display neutral thumbnail placeholder when image fails."""
        self.thumb_label.configure(image="", text="Thumbnail Unavailable")

    def _render_playlist_thumbnail_placeholder(self):
        """Display neutral playlist thumbnail placeholder."""
        self.playlist_thumb_label.configure(image="", text="Playlist Thumbnail")

    def _render_video_metadata(self, info: VideoInfo):
        """Populate single video metadata card."""
        self.playlist_card.grid_remove()
        self.info_card.grid(row=3, column=0, padx=20, pady=(0, 15), sticky="ew")

        self.title_label.configure(text=info.title)
        self.uploader_label.configure(text=f"Channel: {info.uploader}")

        dur_str = format_duration(info.duration)
        views_str = format_count(info.view_count)
        date_str = format_date(info.upload_date)

        meta_parts = [f"Duration: {dur_str}"]
        if views_str:
            meta_parts.append(f"Views: {views_str}")
        if date_str:
            meta_parts.append(f"Uploaded: {date_str}")

        self.meta_row.configure(text="   •   ".join(meta_parts))

        self.quality_title_label.configure(
            text=f"Select Download Quality ({len(info.formats)} options available):"
        )

        dropdown_values = [fmt.display_text for fmt in info.formats]
        self.quality_dropdown.configure(values=dropdown_values)

        self._clear_pills()
        for fmt in info.formats:
            pill_btn = ctk.CTkButton(
                self.pills_frame,
                text=fmt.resolution_label,
                height=28,
                width=85,
                font=ctk.CTkFont(size=11, weight="bold"),
                fg_color="#262A34",
                hover_color="#323745",
                corner_radius=14,
                command=lambda f=fmt: self._on_quality_selected(f.display_text),
            )
            pill_btn.pack(side="left", padx=(0, 6), pady=(4, 0))
            self._pill_buttons.append((fmt.display_text, pill_btn))

        default_idx = min(info.default_format_index, len(info.formats) - 1)
        default_opt = info.formats[default_idx]
        self._on_quality_selected(default_opt.display_text)

        self.download_btn.configure(state="normal")
        self.open_folder_btn.pack_forget()

    def _render_playlist_metadata(self, playlist: PlaylistInfo):
        """Populate playlist view with scrollable item table."""
        self.info_card.grid_remove()
        self.playlist_card.grid(row=3, column=0, padx=20, pady=(0, 15), sticky="ew")

        self.playlist_title_label.configure(text=playlist.title)
        self.playlist_channel_label.configure(text=f"Channel: {playlist.uploader}")
        self.playlist_meta_label.configure(text=f"Playlist • {playlist.total_count} Videos")

        for widget in self.playlist_scroll_frame.winfo_children():
            widget.destroy()

        self._playlist_item_widgets.clear()
        self.playlist_select_all_var.set(True)

        for item in playlist.items:
            row_frame = ctk.CTkFrame(
                self.playlist_scroll_frame,
                fg_color=COLORS["card_bg"],
                border_color=COLORS["card_border"],
                border_width=1,
                corner_radius=6,
            )
            row_frame.pack(fill="x", pady=4, padx=5)

            # Checkbox
            var = ctk.BooleanVar(value=item.is_selected)
            cb = ctk.CTkCheckBox(
                row_frame,
                text="",
                variable=var,
                width=24,
                command=lambda it=item, v=var: self._on_playlist_item_toggled(it, v),
            )
            cb.pack(side="left", padx=(10, 5), pady=8)

            # Order Index
            idx_label = ctk.CTkLabel(
                row_frame,
                text=f"#{item.index:02d}",
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=COLORS["text_muted"],
                width=35,
            )
            idx_label.pack(side="left", padx=(2, 5), pady=8)

            # Item Small Thumbnail Frame
            item_thumb_frame = ctk.CTkFrame(
                row_frame,
                width=64,
                height=36,
                fg_color=COLORS["bg_dark"],
                corner_radius=4,
            )
            item_thumb_frame.pack(side="left", padx=5, pady=6)
            item_thumb_frame.pack_propagate(False)

            item_thumb_label = ctk.CTkLabel(
                item_thumb_frame,
                text="🎬",
                font=ctk.CTkFont(size=11),
                text_color=COLORS["text_muted"],
            )
            item_thumb_label.place(relx=0.5, rely=0.5, anchor="center")

            # Title & Duration
            dur_str = format_duration(item.duration)
            title_text = f"{item.title} ({dur_str})" if dur_str else item.title
            t_label = ctk.CTkLabel(
                row_frame,
                text=title_text,
                font=ctk.CTkFont(size=13),
                text_color=COLORS["text_main"],
                anchor="w",
                justify="left",
                wraplength=340,
            )
            t_label.pack(side="left", fill="x", expand=True, padx=10, pady=8)

            # Per-video Quality Dropdown
            opts = [fmt.display_text for fmt in item.formats]
            def_idx = item.selected_format_index if (0 <= item.selected_format_index < len(opts)) else 0
            def_val = opts[def_idx] if opts else "1080p Full HD"

            opt_menu = ctk.CTkOptionMenu(
                row_frame,
                values=opts if opts else ["1080p Full HD"],
                command=lambda val, it=item: self._on_playlist_item_quality_change(it, val),
                width=170,
                height=28,
                font=ctk.CTkFont(size=11),
                fg_color="#262A34",
                button_color=COLORS["accent_primary"],
            )
            opt_menu.set(def_val)
            opt_menu.pack(side="left", padx=10, pady=8)

            # Status Badge
            status_label = ctk.CTkLabel(
                row_frame,
                text="Pending",
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=COLORS["text_muted"],
                width=90,
            )
            status_label.pack(side="left", padx=(5, 10), pady=8)

            self._playlist_item_widgets[item.index] = {
                "checkbox": cb,
                "var": var,
                "dropdown": opt_menu,
                "status": status_label,
                "thumb_label": item_thumb_label,
            }

        self.download_btn.configure(state="normal")
        self.open_folder_btn.pack_forget()

        # Load small item thumbnails in background thread
        threading.Thread(
            target=self._load_playlist_item_thumbnails_worker,
            args=(playlist.items,),
            daemon=True,
        ).start()

    def _on_playlist_toggle_all(self):
        """Toggle select/deselect all playlist video items."""
        if not self._current_playlist_info:
            return
        state = self.playlist_select_all_var.get()
        for item in self._current_playlist_info.items:
            item.is_selected = state
            if item.index in self._playlist_item_widgets:
                self._playlist_item_widgets[item.index]["var"].set(state)

    def _on_playlist_item_toggled(self, item: PlaylistItem, var: ctk.BooleanVar):
        """Toggle selection state for an individual playlist video item."""
        item.is_selected = var.get()

    def _on_playlist_global_quality_change(self, target_quality_prefix: str):
        """Apply selected master quality across all playlist videos in 1 click."""
        if not self._current_playlist_info:
            return

        target_clean = target_quality_prefix.split("(")[0].strip().lower()

        for item in self._current_playlist_info.items:
            best_match_idx = 0
            for idx, fmt in enumerate(item.formats):
                disp_lower = fmt.display_text.lower()
                res_lower = fmt.resolution_label.lower()
                if target_clean in disp_lower or target_clean in res_lower:
                    best_match_idx = idx
                    break
            item.selected_format_index = best_match_idx
            if item.index in self._playlist_item_widgets and item.formats:
                selected_text = item.formats[best_match_idx].display_text
                self._playlist_item_widgets[item.index]["dropdown"].set(selected_text)

    def _on_playlist_item_quality_change(self, item: PlaylistItem, selected_text: str):
        """Update format choice for an individual playlist item."""
        for idx, fmt in enumerate(item.formats):
            if fmt.display_text == selected_text:
                item.selected_format_index = idx
                break

    def _clear_pills(self):
        """Remove existing quality pill buttons."""
        for _, btn in self._pill_buttons:
            btn.destroy()
        self._pill_buttons = []

    def _on_quality_selected(self, selected_display_text: str):
        """Handle format selection change from dropdown or pill button."""
        if not self._current_video_info:
            return

        for fmt in self._current_video_info.formats:
            if fmt.display_text == selected_display_text:
                self._selected_format = fmt
                self.quality_dropdown.set(fmt.display_text)
                logger.info(f"User selected format: {fmt.display_text} (ID: {fmt.format_id})")

                for text, btn in self._pill_buttons:
                    if text == selected_display_text:
                        btn.configure(fg_color=COLORS["accent_primary"], hover_color=COLORS["accent_hover"])
                    else:
                        btn.configure(fg_color="#262A34", hover_color="#323745")
                break

    def _reset_video_display(self):
        """Reset video metadata card to empty state."""
        self._current_video_info = None
        self._current_playlist_info = None
        self._is_playlist = False
        self._selected_format = None
        self._clear_pills()

        self.playlist_card.grid_remove()
        self.info_card.grid(row=3, column=0, padx=20, pady=(0, 15), sticky="ew")

        self.thumb_label.configure(image="", text="No Video Loaded")
        self.title_label.configure(text="Media title will appear here...")
        self.uploader_label.configure(text="Channel: --")
        self.meta_row.configure(text="Duration: --:--   •   Views: --   •   Uploaded: --")
        self.quality_title_label.configure(text="Select Download Quality:")
        
        self.quality_dropdown.configure(values=["Fetch video to populate qualities"])
        self.quality_dropdown.set("Fetch video to populate qualities")

        self.download_btn.configure(state="disabled")
        self.cancel_btn.configure(state="disabled")
        self.open_folder_btn.pack_forget()

        self.progress_bar.set(0.0)
        self.progress_stats_label.configure(text="Ready to download")

    def _on_download_clicked(self):
        """Start asynchronous media download for single video or playlist."""
        if self._downloader.is_downloading:
            return

        self._has_ffmpeg = find_ffmpeg() is not None

        if self._is_playlist and self._current_playlist_info:
            selected_items = [it for it in self._current_playlist_info.items if it.is_selected]
            if not selected_items:
                self._set_status("Please select at least one video to download", mode="error")
                return

            self.download_btn.configure(state="disabled")
            self.fetch_btn.configure(state="disabled")
            self.url_entry.configure(state="disabled")
            self.cancel_btn.configure(state="normal")
            self.open_folder_btn.pack_forget()

            self.progress_bar.set(0.0)
            self.progress_stats_label.configure(text="Preparing playlist download...")
            self._set_status("Preparing playlist download...", mode="working")

            self._downloader.download_playlist_async(
                playlist_info=self._current_playlist_info,
                on_progress=lambda p: self.after(0, self._on_download_progress, p),
                on_complete=lambda path: self.after(0, self._on_playlist_download_complete, path),
                on_error=lambda err: self.after(0, self._on_download_error, err),
                on_item_status_change=self._on_playlist_item_status_change,
            )

        elif self._current_video_info and self._selected_format:
            if self._selected_format.requires_ffmpeg and not self._has_ffmpeg:
                self._set_status(
                    "FFmpeg is required to download this video quality. Please install FFmpeg or select a progressive quality.",
                    mode="warning",
                )
                return

            self.download_btn.configure(state="disabled")
            self.fetch_btn.configure(state="disabled")
            self.url_entry.configure(state="disabled")
            self.cancel_btn.configure(state="normal")
            self.open_folder_btn.pack_forget()

            self.progress_bar.set(0.0)
            self.progress_stats_label.configure(text="Preparing download...")
            self._set_status("Preparing download...", mode="working")

            self._downloader.download_async(
                video_info=self._current_video_info,
                selected_format=self._selected_format,
                on_progress=lambda p: self.after(0, self._on_download_progress, p),
                on_complete=lambda path: self.after(0, self._on_download_complete, path),
                on_error=lambda err: self.after(0, self._on_download_error, err),
            )

    def _on_playlist_item_status_change(self, item_index: int, status_text: str):
        """Update individual video item status badge in playlist table."""
        if item_index in self._playlist_item_widgets:
            w = self._playlist_item_widgets[item_index]["status"]
            w.configure(text=status_text)
            if "Completed" in status_text:
                w.configure(text_color=COLORS["status_success"])
            elif "Downloading" in status_text:
                w.configure(text_color=COLORS["status_info"])
            elif "Failed" in status_text:
                w.configure(text_color=COLORS["status_error"])

    def _on_cancel_clicked(self):
        """Trigger download cancellation."""
        if self._downloader.is_downloading:
            self.cancel_btn.configure(state="disabled")
            self._set_status("Cancelling download...", mode="warning")
            self._downloader.cancel()

    def _on_download_progress(self, progress: DownloadProgress):
        """Update progress bar and statistics on main GUI thread."""
        self.progress_bar.set(progress.percentage / 100.0)
        self._set_status(progress.status, mode="working" if not progress.is_cancelled else "warning")

        if progress.is_cancelled:
            self.progress_stats_label.configure(text="Download cancelled by user.")
            self._reset_download_controls()
            return

        pct_fmt = f"{progress.percentage:.1f}%"
        downloaded_fmt = format_bytes(progress.downloaded_bytes) or "0 B"
        total_fmt = format_bytes(progress.total_bytes) or "-- MB"

        stats_parts = [f"{progress.status} ({pct_fmt})", f"{downloaded_fmt} / {total_fmt}"]
        if progress.speed_str:
            stats_parts.append(progress.speed_str)
        if progress.eta_str:
            stats_parts.append(progress.eta_str)

        stats_text = "   •   ".join(stats_parts)
        self.progress_stats_label.configure(text=stats_text)

    def _on_download_complete(self, output_filepath: str):
        """Handle single video download completion."""
        self._last_download_path = str(Path(output_filepath).parent)
        self.progress_bar.set(1.0)
        self.progress_stats_label.configure(text=f"Completed: {Path(output_filepath).name}")
        self._set_status("Download completed successfully!", mode="success")

        self._reset_download_controls()
        self.open_folder_btn.pack(side="left", padx=(0, 10))

    def _on_playlist_download_complete(self, playlist_dir_path: str):
        """Handle playlist download completion."""
        self._last_download_path = playlist_dir_path
        self.progress_bar.set(1.0)
        self.progress_stats_label.configure(text=f"Playlist Download Completed: {Path(playlist_dir_path).name}")
        self._set_status("Playlist download completed successfully!", mode="success")

        self._reset_download_controls()
        self.open_folder_btn.pack(side="left", padx=(0, 10))

    def _on_download_error(self, error_message: str):
        """Handle download error on main GUI thread."""
        self.progress_bar.set(0.0)
        self.progress_stats_label.configure(text="Download failed.")
        self._set_status(error_message, mode="error")

        self._reset_download_controls()

    def _reset_download_controls(self):
        """Reset button operational states after download finish/cancel/error."""
        self.download_btn.configure(state="normal")
        self.fetch_btn.configure(state="normal")
        self.url_entry.configure(state="normal")
        self.cancel_btn.configure(state="disabled")

    def _on_open_folder_clicked(self):
        """Open target downloads directory in Windows Explorer."""
        target_dir = Path(self._last_download_path) if hasattr(self, "_last_download_path") else DOWNLOADS_DIR
        if not target_dir.exists():
            target_dir = DOWNLOADS_DIR
        success, msg = open_folder(target_dir)
        if not success:
            self._set_status(msg, mode="error")
