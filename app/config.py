"""
Application configuration and path constants.
"""

from pathlib import Path

# Application Base Directories
# Path(__file__).resolve().parent is 'app', parent.parent is project root
BASE_DIR = Path(__file__).resolve().parent.parent
DOWNLOADS_DIR = BASE_DIR / "downloads"
LOGS_DIR = BASE_DIR / "logs"
ASSETS_DIR = BASE_DIR / "assets"
LOG_FILE = LOGS_DIR / "app.log"

# Window Geometry
APP_TITLE = "Media Downloader"
WINDOW_WIDTH = 1140
WINDOW_HEIGHT = 760
MIN_WIDTH = 920
MIN_HEIGHT = 620

# CustomTkinter Theme Settings
APPEARANCE_MODE = "Dark"
COLOR_THEME = "blue"

# UI Theme Color Palette
COLORS = {
    "bg_dark": "#121417",
    "card_bg": "#1A1D24",
    "card_border": "#2A2E39",
    "accent_primary": "#1F6AA5",
    "accent_hover": "#144D7A",
    "accent_danger": "#C0392B",
    "accent_danger_hover": "#962D22",
    "text_main": "#F0F3F6",
    "text_muted": "#8A94A6",
    "status_success": "#2ECC71",
    "status_warning": "#F39C12",
    "status_error": "#E74C3C",
    "status_info": "#3498DB",
}

def setup_app_directories():
    """Ensure all required directories exist on application startup."""
    DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
