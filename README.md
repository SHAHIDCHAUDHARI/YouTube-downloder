# Media Downloader

A modern desktop media downloader built with Python, CustomTkinter, yt-dlp, and FFmpeg. Supports downloading single videos, YouTube Shorts, Instagram Reels, Pinterest videos, and full YouTube Playlists in high quality.

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![CustomTkinter](https://img.shields.io/badge/UI-CustomTkinter-blue)](https://github.com/TomSchimansky/CustomTkinter)
[![yt-dlp](https://img.shields.io/badge/Engine-yt--dlp-red)](https://github.com/yt-dlp/yt-dlp)
[![curl-cffi](https://img.shields.io/badge/Impersonation-curl--cffi-purple)](https://github.com/lexiforest/curl_cffi)
[![FFmpeg](https://img.shields.io/badge/Media-FFmpeg-green)](https://ffmpeg.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows-blue)](https://microsoft.com)

[**Installation Steps**](#quick-start-guide)

---

## Table of Contents
- [Quick Start Guide (How to Install)](#quick-start-guide)
- [Features](#features)
- [Supported Platforms](#supported-platforms)
- [Screenshots](#screenshots)

---

## Quick Start Guide

### Method 1: Double-Click Setup (Recommended / Easy Setup)

Recommended for most users and beginners downloading the ZIP release:

1. Extract the downloaded project ZIP file on your computer.
2. Double-click **`setup.py`** to automatically install required packages and set up runtime folders.
3. Double-click **`run.py`** to launch Media Downloader!

---

### Method 2: Command Line (Advanced / Developers)

For developers and command line users:

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd <repository-folder>
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Launch the application**:
   ```bash
   python run.py
   ```

---

## Features

- **Full YouTube Playlist Support**: Download entire playlists with interactive video selection, item checkboxes, and per-video quality choices.
- **1-Click Master Quality Selector**: Set desired resolution (`1080p Full HD`, `720p HD`, `480p`, `Audio MP3`) across all playlist videos at once.
- **Dedicated Playlist Folders**: Automatically organizes downloads into named playlist subfolders (`downloads/Playlist Title/`) with chronological index prefixes (`01 - Intro.mp4`, `02 - Variables.mp4`).
- **Pinterest Video & Pin Support**: Download high-definition Pinterest videos, Idea Pins, and pins from both `pin.it` short links and `pinterest.com` URLs.
- **Original Audio Preservation**: Intelligent audio track selection prioritizes native creator voice tracks (such as Hindi Original) over AI-generated dubbed audio.
- **Universal Player Compatibility**: Automatically pairs H.264 Video + AAC Audio for smooth playback on Windows Media Player, QuickTime, mobile devices, and TVs.
- **Standalone Thumbnail Download**: Dedicated 1-click button to download high-resolution video thumbnail images (`.jpg` / `.webp`) directly to `downloads/`.
- **Visual Thumbnail Previews**: Real-time thumbnail previews for single videos and visual row thumbnails in the playlist table.
- **Audio & MP3 Extraction**: Download standalone audio streams or convert directly to high-bitrate MP3 files.
- **Per-Video Progress Bar**: Individual 0% to 100% progress tracking per video item with download speed and ETA.
- **Responsive Dark Theme**: Built on CustomTkinter with a scrollable container for all screen resolutions.

---

## Supported Platforms

| Platform | Supported Content | Available Qualities |
| :--- | :--- | :--- |
| **YouTube** | Long-form Videos, YouTube Shorts, & Full Playlists | 1440p QHD, 1080p Full HD, 720p HD, 480p, 360p, 240p, M4A, MP3 |
| **Instagram** | Reels & Video Posts | HD MP4 (H.264 + AAC) |
| **Pinterest** | Videos, Idea Pins, & Pin Media (`pin.it` / `pinterest.com`) | HD MP4, 720p, 480p, 360p, Original Thumbnails |

---

## Screenshots

### Main Application Interface
![Media Downloader Main Window](assets/main-window.png)

*Main application interface showing video metadata, quality selection badges, and live progress.*

### Compact Responsive Layout
![Media Downloader Compact Window](assets/compact-window.png)

*Responsive scrollable layout for smaller display resolutions.*
