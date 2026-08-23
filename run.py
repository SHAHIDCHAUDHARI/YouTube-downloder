"""
Main application entry point for the Media Downloader desktop application.
"""

import sys
import logging
import customtkinter as ctk

from app.config import (
    APPEARANCE_MODE,
    COLOR_THEME,
    setup_app_directories,
)
from app.gui import MediaDownloaderApp


def setup_logging():
    """Configure console logging to stdout."""
    setup_app_directories()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )
    logging.info("Starting Media Downloader Application...")


def handle_uncaught_exception(exc_type, exc_value, exc_traceback):
    """Log any unhandled exceptions to prevent silent crashes."""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logging.critical("Uncaught exception encountered:", exc_info=(exc_type, exc_value, exc_traceback))


def main():
    # Set exception handler
    sys.excepthook = handle_uncaught_exception

    # Configure logging and directories
    setup_logging()

    # Configure CustomTkinter Theme
    ctk.set_appearance_mode(APPEARANCE_MODE)
    ctk.set_default_color_theme(COLOR_THEME)

    # Launch Application Main Loop
    app = MediaDownloaderApp()
    app.mainloop()


if __name__ == "__main__":
    main()
