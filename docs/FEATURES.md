# Features Overview

This document provides a detailed breakdown of the features implemented in Media Downloader.

## Core Features

### Desktop User Interface
- Built with `CustomTkinter` for a clean dark desktop interface.
- Responsive layout using a scrollable container (`CTkScrollableFrame`), ensuring all controls and quality options remain accessible on smaller screens without content clipping.

### Metadata Extraction
- Fetches video information using `yt-dlp` without downloading media upfront.
- Displays thumbnail preview, title, channel name, video duration, view count, and upload date.
- Normalizes resolution labels into recognizable formats (1080p Full HD, 720p HD, 480p, 360p, 240p, 144p).

### Quality Selection
- Provides both a dropdown menu and quick-select badges (pills) for fast quality switching.
- Calculates dynamic file size estimates for each resolution based on stream headers or bitrate and duration fallback.
- Pre-selects 1080p by default when available.

### Audio Downloads & MP3 Conversion
- Supports standalone audio stream downloads (`Audio Only - M4A / WEBM`).
- Includes an option to convert audio streams directly to MP3 format using FFmpeg.

### Real-Time Download Progress
- Runs downloads asynchronously in a background thread to keep the interface smooth and responsive.
- Reports live download statistics: percentage, downloaded MB vs. total MB, current download speed (KB/s or MB/s), and estimated time remaining (ETA).
- Combines multi-pass video and audio stream progress smoothly without sudden jumps.
- Allows user cancellation at any point during downloading.

### FFmpeg Integration
- Automatically detects FFmpeg in order of priority:
  1. Project-local directory (`./ffmpeg/bin` or `./ffmpeg`)
  2. System `PATH`
  3. `imageio-ffmpeg` Python package fallback
- Automatically handles stream merging when downloading high-resolution YouTube formats (such as 1080p) where video and audio streams are separated.

### File & Directory Management
- Automatically saves downloaded files to a local `downloads/` directory.
- Includes an **Open Folder** button upon completion to open the downloads directory directly in Windows Explorer or your operating system's file manager.
- Logs application events and errors to `logs/app.log` for troubleshooting.
