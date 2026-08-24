# Media Downloaders

A clean desktop media downloader built with Python, CustomTkinter, yt-dlp, and FFmpeg.

---

## Quick Start (How to Run)

### Method 1: Command Line

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd <repository-folder>
   ```

2. **Install requirements**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Start the application**:
   ```bash
   python run.py
   ```

---

### Method 2: Beginner / Double-Click Setup (No Command Line Required)

If you downloaded the project ZIP file or prefer not to use terminal commands:

1. Extract the downloaded ZIP folder on your computer.
2. Double-click **`setup.py`** to automatically install all dependencies and create required runtime folders.
3. Double-click **`run.py`** to launch the Media Downloader application!

---

## Features

- **Metadata Extraction**: Paste a video URL to view title, channel, duration, and thumbnail preview.
- **Quality Options**: Select resolutions from 1080p Full HD down to 144p, with estimated file sizes.
- **Audio & MP3 Download**: Download standalone audio files or convert audio directly to MP3.
- **FFmpeg Integration**: Automatic detection and fallback to merge video + audio streams cleanly.
- **Real-Time Progress**: Live MB downloaded, percentage, download speed, and ETA.
- **Responsive Interface**: Scrollable main window ensures controls remain accessible at all window sizes.
- **Local Downloads Folder**: Downloads are automatically saved to `downloads/` with an **Open Folder** button.

## Supported Platforms

- **YouTube**: Long-form videos & YouTube Shorts
- **Instagram**: Reels & video posts

---

## Screenshots

![Media Downloader Compact Window](assets/compact-window.png)

*Responsive scrollable interface on compact displays.*

![Media Downloader Main Window](assets/main-window.png)

*Main application interface with video metadata, quality selection badges, and live progress.*


