<div align="center">

# 🎬 Media Downloader

**A modern, high-performance desktop media downloader built with Python, CustomTkinter, yt-dlp, and FFmpeg.**  
*Download single videos, YouTube Shorts, Instagram Reels, and full YouTube Playlists in crystal-clear quality.*

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![CustomTkinter](https://img.shields.io/badge/UI-CustomTkinter-blue?style=for-the-badge)](https://github.com/TomSchimansky/CustomTkinter)
[![yt-dlp](https://img.shields.io/badge/Engine-yt--dlp-red?style=for-the-badge)](https://github.com/yt-dlp/yt-dlp)
[![FFmpeg](https://img.shields.io/badge/Media-FFmpeg-green?style=for-the-badge&logo=ffmpeg&logoColor=white)](https://ffmpeg.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows-0078D6?style=for-the-badge&logo=windows&logoColor=white)](https://microsoft.com)

</div>

---

## 📌 Table of Contents
- [✨ Features](#-features)
- [🌐 Supported Platforms](#-supported-platforms)
- [📸 Screenshots](#-screenshots)
- [🚀 Quick Start Guide](#-quick-start-guide)
- [📁 Project Structure](#-project-structure)
- [⚙️ How It Works](#-how-it-works)

---

## ✨ Features

- 📺 **Full YouTube Playlist Downloader**: Download entire YouTube playlists with interactive line-by-line video selection, item checkboxes, and per-video quality choices.
- ⚡ **1-Click Master Quality Selector**: Set desired resolution (`1080p Full HD`, `720p HD`, `480p`, `Audio MP3`) across all playlist videos in 1 click.
- 📁 **Dedicated Playlist Folders**: Automatically organizes downloads into named playlist subfolders (`downloads/Playlist Title/`) with chronological index prefixes (`01 - Intro.mp4`, `02 - Variables.mp4`).
- 🎙️ **Original Voice Track Preservation**: Intelligent audio track selection prioritizes native creator voice tracks (Hindi Original) over AI-generated dubbed audio.
- 🎬 **Universal H.264 Playback**: Automatically pairs H.264 Video + AAC Audio for 100% smooth playback on Windows Media Player, Movies & TV, QuickTime, mobile devices, and TVs without requiring third-party players like VLC.
- 🖼️ **Visual Thumbnail Previews**: Real-time thumbnail previews for single videos as well as small `64x36` visual row thumbnails in the playlist table.
- 🎧 **Audio & MP3 Conversion**: Extract standalone audio streams or convert audio directly to high-bitrate MP3s.
- 🔄 **Per-Video Progress Bar**: Individual 0% to 100% progress tracking per video, live MB downloaded, transfer speed, and ETA.
- 🎨 **Premium Dark Slate Interface**: Built on CustomTkinter with responsive scrolling layout for all screen sizes.

---

## 🌐 Supported Platforms

| Platform | Supported Content | Formats & Qualities |
| :--- | :--- | :--- |
| **YouTube** | Long-form Videos, YouTube Shorts, & Full Playlists | 1440p QHD, 1080p Full HD, 720p HD, 480p, 360p, 240p, M4A, MP3 |
| **Instagram** | Reels & Video Posts | HD MP4 (H.264 + AAC) |

---

## 📸 Screenshots

### 🖼️ Main Application Interface
![Media Downloader Main Window](assets/main-window.png)
*Main application interface displaying video metadata, quality selection badges, and live download progress.*

### 📱 Compact Responsive Layout
![Media Downloader Compact Window](assets/compact-window.png)
*Responsive scrollable container for compact display resolutions.*

---

## 🚀 Quick Start Guide

### Method 1: Command Line (Recommended for Developers)

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd <repository-folder>
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Launch the app**:
   ```bash
   python run.py
   ```

---

### Method 2: Double-Click Setup (Beginner Friendly)

1. **Extract ZIP**: Extract the project ZIP folder on your computer.
2. **Setup**: Double-click **`setup.py`** to automatically install required Python packages and set up runtime folders.
3. **Launch**: Double-click **`run.py`** to launch Media Downloader!

---

## 📁 Project Structure

```text
media-downloader/
├── run.py                 # Main entry point & application launcher
├── setup.py               # One-click installer & dependency setup script
├── requirements.txt       # Python package dependencies (yt-dlp, customtkinter, Pillow, imageio-ffmpeg)
├── README.md              # Project documentation
├── .gitignore             # Git ignore rules
│
├── app/                   # Application source code
│   ├── config.py          # Paths, window dimensions, and UI theme colors
│   ├── downloader.py      # Multi-threaded download runner & progress hooks
│   ├── gui.py             # CustomTkinter graphical user interface & views
│   ├── metadata.py        # Metadata extraction & format normalization engine
│   ├── models.py          # Data models (VideoInfo, PlaylistInfo, PlaylistItem, FormatOption)
│   └── utils.py           # FFmpeg locator, bytes formatter, folder opener
│
└── assets/                # README screenshots & branding assets
```

---

## ⚙️ How It Works

1. **Metadata Engine**: `yt-dlp` extracts format information without downloading the media file.
2. **Quality Normalization**: `metadata.py` filters duplicate streams, enforces H.264 video + AAC audio, and ranks streams by resolution.
3. **Multi-Threading**: Downloads execute in background worker threads to keep the CustomTkinter GUI 100% smooth and responsive.
4. **FFmpeg Stream Merging**: High-definition DASH video and audio streams are merged into universally compatible `.mp4` files using FFmpeg.
