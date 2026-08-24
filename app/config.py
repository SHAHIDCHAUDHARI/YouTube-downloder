"""
Application configuration and path constants.
"""

from pathlib import Path

# Application Base Directories
# Path(__file__).resolve().parent is 'app', parent.parent is project root
BASE_DIR = Path(__file__).resolve().parent.parent
DOWNLOADS_DIR = BASE_DIR / "downloads"
ASSETS_DIR = BASE_DIR / "assets"

# Window Geometry
APP_TITLE = "Media Downloader"
WINDOW_WIDTH = 1140
WINDOW_HEIGHT = 760
MIN_WIDTH = 920
MIN_HEIGHT = 620

# CustomTkinter Theme Settings
APPEARANCE_MODE = "Dark"
COLOR_THEME = "blue"

# UI Theme Color Palette (Premium Dark Theme)
COLORS = {
    "bg_dark": "#0D0F12",
    "card_bg": "#151821",
    "card_border": "#222736",
    "input_bg": "#1A1D28",
    "accent_primary": "#2563EB",
    "accent_hover": "#1D4ED8",
    "accent_danger": "#DC2626",
    "accent_danger_hover": "#B91C1C",
    "text_main": "#F9FAFB",
    "text_muted": "#9CA3AF",
    "text_dim": "#6B7280",
    "status_success": "#10B981",
    "status_warning": "#F59E0B",
    "status_error": "#EF4444",
    "status_info": "#3B82F6",
    "pill_bg": "#1F2330",
    "pill_hover": "#2B3042",
}

def setup_app_directories():
    """Ensure required downloads directory exists on application startup."""
    DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
