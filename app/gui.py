"""
CustomTkinter graphical user interface for the Media Downloader application.
"""

import io
import logging
import threading
from typing import Optional
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
from app.metadata import fetch_video_info
from app.models import DownloadProgress, FormatOption, VideoInfo
from app.utils import (
    find_ffmpeg,
    format_bytes,
    format_count,
    format_date,
    format_duration,
    open_folder,
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
        self._selected_format: Optional[FormatOption] = None
        self._downloader = Downloader()
        self._is_fetching = False

        # Build UI Components
        self._setup_layout()
        self._setup_header()
        self._setup_url_input_section()
        self._setup_status_banner()
        self._setup_video_info_card()
        self._setup_download_section()
        self._setup_ffmpeg_notice()

        logger.info("MediaDownloaderApp initialized successfully.")

    def _center_window(self):
        """Center the window on the screen."""
        self.update_idletasks()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - WINDOW_WIDTH) // 2
        y = (screen_height - WINDOW_HEIGHT) // 2
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}+{x}+{y}")

    def _setup_layout(self):
        """Configure responsive grid layout inside scrollable main container."""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Scrollable container prevents content clipping on smaller displays
        self.main_container = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.main_container.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        self.main_container.grid_columnconfigure(0, weight=1)

    # -------------------------------------------------------------------
    # 1. App Header
    # -------------------------------------------------------------------
    def _setup_header(self):
        header_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        header_frame.grid(row=0, column=0, padx=25, pady=(20, 10), sticky="ew")

        title_label = ctk.CTkLabel(
            header_frame,
            text=APP_TITLE,
            font=ctk.CTkFont(family="Segoe UI", size=26, weight="bold"),
            text_color=COLORS["text_main"],
        )
        title_label.pack(anchor="w")

        subtitle_label = ctk.CTkLabel(
            header_frame,
            text="Download your permitted media in the quality you choose",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color=COLORS["text_muted"],
        )
        subtitle_label.pack(anchor="w", pady=(2, 0))

    # -------------------------------------------------------------------
    # 2. URL Input Section
    # -------------------------------------------------------------------
    def _setup_url_input_section(self):
        input_card = ctk.CTkFrame(
            self.main_container,
            fg_color=COLORS["card_bg"],
            corner_radius=12,
            border_width=1,
            border_color=COLORS["card_border"],
        )
        input_card.grid(row=1, column=0, padx=25, pady=10, sticky="ew")
        input_card.grid_columnconfigure(0, weight=1)

        input_inner_frame = ctk.CTkFrame(input_card, fg_color="transparent")
        input_inner_frame.pack(fill="x", padx=15, pady=15)
        input_inner_frame.grid_columnconfigure(0, weight=1)

        # URL Entry Field
        self.url_entry = ctk.CTkEntry(
            input_inner_frame,
            placeholder_text="Paste video URL here...",
            height=44,
            font=ctk.CTkFont(size=14),
            border_width=1,
            corner_radius=8,
        )
        self.url_entry.grid(row=0, column=0, padx=(0, 10), sticky="ew")
        self.url_entry.bind("<Return>", lambda event: self._on_fetch_clicked())

        # Clear Button
        self.clear_btn = ctk.CTkButton(
            input_inner_frame,
            text="✕",
            width=36,
            height=44,
            fg_color="#262A34",
            hover_color="#323745",
            text_color=COLORS["text_muted"],
            font=ctk.CTkFont(size=14, weight="bold"),
            corner_radius=8,
            command=self._on_clear_url,
        )
        self.clear_btn.grid(row=0, column=1, padx=(0, 10))

        # Fetch Video Button
        self.fetch_btn = ctk.CTkButton(
            input_inner_frame,
            text="Fetch Video",
            height=44,
            width=130,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=COLORS["accent_primary"],
            hover_color=COLORS["accent_hover"],
            corner_radius=8,
            command=self._on_fetch_clicked,
        )
        self.fetch_btn.grid(row=0, column=2)

    # -------------------------------------------------------------------
    # 3. Status Banner
    # -------------------------------------------------------------------
    def _setup_status_banner(self):
        self.status_banner = ctk.CTkFrame(
            self.main_container,
            fg_color="#1E222A",
            corner_radius=8,
            height=38,
        )
        self.status_banner.grid(row=2, column=0, padx=25, pady=(5, 10), sticky="ew")
        self.status_banner.pack_propagate(False)

        self.status_label = ctk.CTkLabel(
            self.status_banner,
            text="Ready — Paste a URL and click 'Fetch Video'",
            font=ctk.CTkFont(size=13),
            text_color=COLORS["text_muted"],
        )
        self.status_label.pack(side="left", padx=15)

    def _set_status(self, text: str, mode: str = "info"):
        """Update status banner with appropriate text color."""
        color_map = {
            "info": COLORS["text_muted"],
            "working": COLORS["status_info"],
            "success": COLORS["status_success"],
            "warning": COLORS["status_warning"],
            "error": COLORS["status_error"],
        }
        self.status_label.configure(text=text, text_color=color_map.get(mode, COLORS["text_muted"]))

    # -------------------------------------------------------------------
    # 4. Video Information Card
    # -------------------------------------------------------------------
    def _setup_video_info_card(self):
        self.info_card = ctk.CTkFrame(
            self.main_container,
            fg_color=COLORS["card_bg"],
            corner_radius=12,
            border_width=1,
            border_color=COLORS["card_border"],
        )
        self.info_card.grid(row=3, column=0, padx=25, pady=10, sticky="ew")
        self.info_card.grid_columnconfigure(1, weight=1)
        self.info_card.grid_rowconfigure(0, weight=0)
        self.info_card.grid_rowconfigure(1, weight=0)

        # Row 0, Col 0: Thumbnail Container (240x135 16:9 ratio)
        self.thumb_frame = ctk.CTkFrame(
            self.info_card,
            width=240,
            height=135,
            fg_color="#121417",
            corner_radius=8,
        )
        self.thumb_frame.grid(row=0, column=0, padx=15, pady=15, sticky="n")
        self.thumb_frame.pack_propagate(False)

        self.thumb_label = ctk.CTkLabel(
            self.thumb_frame,
            text="No Video Loaded",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_muted"],
        )
        self.thumb_label.pack(expand=True)

        # Row 0, Col 1: Metadata Details
        self.details_frame = ctk.CTkFrame(self.info_card, fg_color="transparent")
        self.details_frame.grid(row=0, column=1, padx=(0, 15), pady=15, sticky="nsew")
        self.details_frame.grid_columnconfigure(0, weight=1)

        # Video Title
        self.title_label = ctk.CTkLabel(
            self.details_frame,
            text="Media title will appear here...",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color=COLORS["text_main"],
            anchor="w",
            justify="left",
            wraplength=580,
        )
        self.title_label.pack(anchor="w", pady=(0, 4))

        # Channel / Uploader
        self.uploader_label = ctk.CTkLabel(
            self.details_frame,
            text="Channel: --",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_muted"],
            anchor="w",
        )
        self.uploader_label.pack(anchor="w", pady=(0, 2))

        # Duration & Metadata Row
        self.meta_row = ctk.CTkLabel(
            self.details_frame,
            text="Duration: --:--   •   Views: --   •   Uploaded: --",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_muted"],
            anchor="w",
        )
        self.meta_row.pack(anchor="w", pady=(0, 5))

        # Row 1, Columnspan 2: Full-Width Quality Selector Section
        self.quality_frame = ctk.CTkFrame(self.info_card, fg_color="transparent")
        self.quality_frame.grid(row=1, column=0, columnspan=2, padx=15, pady=(0, 15), sticky="ew")

        self.quality_title_label = ctk.CTkLabel(
            self.quality_frame,
            text="Select Download Quality:",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLORS["text_main"],
        )
        self.quality_title_label.pack(anchor="w", pady=(0, 4))

        self.quality_dropdown = ctk.CTkOptionMenu(
            self.quality_frame,
            values=["Fetch video to populate qualities"],
            height=38,
            font=ctk.CTkFont(size=13),
            dropdown_font=ctk.CTkFont(size=13),
            corner_radius=8,
            fg_color="#262A34",
            button_color="#323745",
            button_hover_color="#3E4556",
            command=self._on_quality_selected,
        )
        self.quality_dropdown.pack(anchor="w", fill="x")

        # Quick Quality Pills Container
        self.pills_frame = ctk.CTkFrame(self.quality_frame, fg_color="transparent")
        self.pills_frame.pack(anchor="w", fill="x", pady=(6, 0))
        self._pill_buttons = []

    # -------------------------------------------------------------------
    # 5. Download Controls & Real-Time Progress Section
    # -------------------------------------------------------------------
    def _setup_download_section(self):
        download_card = ctk.CTkFrame(
            self.main_container,
            fg_color=COLORS["card_bg"],
            corner_radius=12,
            border_width=1,
            border_color=COLORS["card_border"],
        )
        download_card.grid(row=4, column=0, padx=25, pady=10, sticky="ew")
        download_card.grid_columnconfigure(0, weight=1)

        inner_frame = ctk.CTkFrame(download_card, fg_color="transparent")
        inner_frame.pack(fill="x", padx=20, pady=15)
        inner_frame.grid_columnconfigure(0, weight=1)

        # Real-time Progress Bar
        self.progress_bar = ctk.CTkProgressBar(
            inner_frame,
            height=12,
            corner_radius=6,
            fg_color="#262A34",
            progress_color=COLORS["accent_primary"],
        )
        self.progress_bar.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 8))
        self.progress_bar.set(0.0)

        # Progress Details Label
        self.progress_stats_label = ctk.CTkLabel(
            inner_frame,
            text="Ready to download",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_muted"],
            anchor="w",
        )
        self.progress_stats_label.grid(row=1, column=0, sticky="w")

        # Buttons Container
        btn_box = ctk.CTkFrame(inner_frame, fg_color="transparent")
        btn_box.grid(row=1, column=2, sticky="e")

        # Open Folder Button
        self.open_folder_btn = ctk.CTkButton(
            btn_box,
            text="Open Folder",
            height=40,
            width=120,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#2ECC71",
            hover_color="#27AE60",
            corner_radius=8,
            command=self._on_open_folder_clicked,
        )
        self.open_folder_btn.pack(side="left", padx=(0, 10))
        self.open_folder_btn.pack_forget()  # Hidden initially

        # Cancel Button
        self.cancel_btn = ctk.CTkButton(
            btn_box,
            text="Cancel",
            height=40,
            width=100,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=COLORS["accent_danger"],
            hover_color=COLORS["accent_danger_hover"],
            corner_radius=8,
            state="disabled",
            command=self._on_cancel_clicked,
        )
        self.cancel_btn.pack(side="left", padx=(0, 10))

        # Download Button
        self.download_btn = ctk.CTkButton(
            btn_box,
            text="Download",
            height=40,
            width=140,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=COLORS["accent_primary"],
            hover_color=COLORS["accent_hover"],
            corner_radius=8,
            state="disabled",
            command=self._on_download_clicked,
        )
        self.download_btn.pack(side="left")

    # -------------------------------------------------------------------
    # 6. FFmpeg Notice Section
    # -------------------------------------------------------------------
    def _setup_ffmpeg_notice(self):
        self.ffmpeg_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.ffmpeg_frame.grid(row=5, column=0, padx=25, pady=(0, 15), sticky="ew")

        if not self._has_ffmpeg:
            notice_label = ctk.CTkLabel(
                self.ffmpeg_frame,
                text="⚠️ FFmpeg is not detected. High-res qualities requiring video+audio merging will be unavailable until FFmpeg is added.",
                font=ctk.CTkFont(size=11),
                text_color=COLORS["status_warning"],
                anchor="center",
            )
            notice_label.pack()

    # -------------------------------------------------------------------
    # Event Handlers & Business Logic
    # -------------------------------------------------------------------
    def _on_clear_url(self):
        """Clear URL entry and reset UI state."""
        self.url_entry.delete(0, "end")
        self._reset_video_display()
        self._set_status("Ready — Paste a URL and click 'Fetch Video'")

    def _on_fetch_clicked(self):
        """Trigger background metadata extraction."""
        if self._is_fetching or self._downloader.is_downloading:
            return

        url = self.url_entry.get().strip()
        if not url:
            self._set_status("Please enter a valid media URL", mode="error")
            return

        # Dynamically re-scan FFmpeg availability
        self._has_ffmpeg = find_ffmpeg() is not None
        if self._has_ffmpeg and hasattr(self, "ffmpeg_frame"):
            for widget in self.ffmpeg_frame.winfo_children():
                widget.destroy()

        # UI Loading State
        self._is_fetching = True
        self.fetch_btn.configure(state="disabled", text="Fetching...")
        self.url_entry.configure(state="disabled")
        self.download_btn.configure(state="disabled")
        self._set_status("Fetching video information...", mode="working")

        # Run extraction in background thread
        threading.Thread(
            target=self._fetch_metadata_worker,
            args=(url,),
            daemon=True,
        ).start()

    def _fetch_metadata_worker(self, url: str):
        """Worker thread executing yt-dlp metadata extraction."""
        try:
            video_info = fetch_video_info(url, has_ffmpeg=self._has_ffmpeg)
            self.after(0, self._on_fetch_success, video_info)
        except Exception as e:
            err_msg = str(e)
            self.after(0, self._on_fetch_error, err_msg)

    def _on_fetch_success(self, video_info: VideoInfo):
        """Handle successful metadata extraction on main thread."""
        self._is_fetching = False
        self.fetch_btn.configure(state="normal", text="Fetch Video")
        self.url_entry.configure(state="normal")

        self._current_video_info = video_info
        self._render_video_metadata(video_info)
        self._set_status("Video information loaded successfully", mode="success")

        # Fetch thumbnail asynchronously
        if video_info.thumbnail_url:
            threading.Thread(
                target=self._load_thumbnail_worker,
                args=(video_info.thumbnail_url,),
                daemon=True,
            ).start()
        else:
            self._render_thumbnail_placeholder()

    def _on_fetch_error(self, error_message: str):
        """Handle metadata extraction failure on main thread."""
        self._is_fetching = False
        self.fetch_btn.configure(state="normal", text="Fetch Video")
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

    def _render_thumbnail(self, pil_image: Image.Image):
        """Render thumbnail Image inside thumb_frame maintaining aspect ratio."""
        try:
            # Resize image to fit 240x135 thumbnail card
            target_w, target_h = 240, 135
            pil_image.thumbnail((target_w, target_h), Image.Resampling.LANCZOS)
            ctk_img = ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=(pil_image.width, pil_image.height))

            self.thumb_label.configure(image=ctk_img, text="")
            self.thumb_label.image = ctk_img  # Prevent garbage collection
        except Exception as e:
            logger.error(f"Error rendering thumbnail: {e}")
            self._render_thumbnail_placeholder()

    def _render_thumbnail_placeholder(self):
        """Display neutral thumbnail placeholder when image fails."""
        self.thumb_label.configure(image="", text="Thumbnail Unavailable")

    def _render_video_metadata(self, info: VideoInfo):
        """Populate metadata fields, format selection dropdown, and quality pills."""
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

        # Update Quality Section Header
        self.quality_title_label.configure(
            text=f"Select Download Quality ({len(info.formats)} options available):"
        )

        # Populate Quality Selector Dropdown
        dropdown_values = [fmt.display_text for fmt in info.formats]
        self.quality_dropdown.configure(values=dropdown_values)

        # Render Quick Quality Pills Buttons
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

        # Preselect default quality index
        default_idx = min(info.default_format_index, len(info.formats) - 1)
        default_opt = info.formats[default_idx]
        self._on_quality_selected(default_opt.display_text)

        # Enable Download Button
        self.download_btn.configure(state="normal")
        self.open_folder_btn.pack_forget()

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

                # Highlight corresponding pill button
                for text, btn in self._pill_buttons:
                    if text == selected_display_text:
                        btn.configure(fg_color=COLORS["accent_primary"], hover_color=COLORS["accent_hover"])
                    else:
                        btn.configure(fg_color="#262A34", hover_color="#323745")
                break

    def _reset_video_display(self):
        """Reset video metadata card to empty state."""
        self._current_video_info = None
        self._selected_format = None
        self._clear_pills()

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

    # -------------------------------------------------------------------
    # Download Execution & Thread Synchronization
    # -------------------------------------------------------------------
    def _on_download_clicked(self):
        """Start asynchronous media download."""
        if not self._current_video_info or not self._selected_format or self._downloader.is_downloading:
            return

        # Dynamically re-scan FFmpeg availability
        self._has_ffmpeg = find_ffmpeg() is not None

        # Check FFmpeg requirement
        if self._selected_format.requires_ffmpeg and not self._has_ffmpeg:
            self._set_status(
                "FFmpeg is required to download this video quality. Please install FFmpeg or select a progressive quality.",
                mode="warning",
            )
            return

        # Prepare UI states
        self.download_btn.configure(state="disabled")
        self.fetch_btn.configure(state="disabled")
        self.url_entry.configure(state="disabled")
        self.cancel_btn.configure(state="normal")
        self.open_folder_btn.pack_forget()

        self.progress_bar.set(0.0)
        self.progress_stats_label.configure(text="Preparing download...")
        self._set_status("Preparing download...", mode="working")

        # Launch download runner
        self._downloader.download_async(
            video_info=self._current_video_info,
            selected_format=self._selected_format,
            on_progress=lambda p: self.after(0, self._on_download_progress, p),
            on_complete=lambda path: self.after(0, self._on_download_complete, path),
            on_error=lambda err: self.after(0, self._on_download_error, err),
        )

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
        """Handle successful download completion on main GUI thread."""
        self.progress_bar.set(1.0)
        self.progress_stats_label.configure(text=f"Completed: {Path(output_filepath).name}")
        self._set_status("Download completed successfully!", mode="success")

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
        """Open downloads directory in Windows Explorer."""
        success, msg = open_folder(DOWNLOADS_DIR)
        if not success:
            self._set_status(msg, mode="error")
