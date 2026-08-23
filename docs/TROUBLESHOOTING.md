# Troubleshooting Guide

This guide covers solutions to common setup and runtime issues.

---

## Application Does Not Start

Verify your Python version (Python 3.10+ recommended):

```bash
python --version
```

Make sure all dependencies are installed inside your active virtual environment:

```bash
pip install -r requirements.txt
```

Run the application entry point:

```bash
python app.py
```

---

## ModuleNotFoundError

This error indicates that required Python packages are missing or you are running Python outside the virtual environment.

Activate your virtual environment first:

- **Windows**: `.venv\Scripts\activate`
- **macOS / Linux**: `source .venv/bin/activate`

Then reinstall requirements:

```bash
pip install -r requirements.txt
```

---

## yt-dlp Errors or Extraction Failures

Video extraction logic can break when media platforms update their web players. Update `yt-dlp` to the latest release:

```bash
pip install -U yt-dlp
```

---

## Video Information Does Not Load

Possible causes:
- Invalid or unsupported video URL.
- Video is private, age-restricted, or removed.
- Temporary internet connection loss.

Check `logs/app.log` for specific error messages returned by `yt-dlp`.

---

## Quality Option Missing

The application can only display resolutions that `yt-dlp` extracts from the source URL. If a video was only uploaded in 720p, 1080p will not appear in the quality options.

---

## 1080p / High-Resolution Quality Requires FFmpeg

Higher quality formats on YouTube (1080p, 1440p, 4K) serve video and audio as separate streams. `yt-dlp` requires FFmpeg to merge these streams into a single playable MP4 file.

If FFmpeg is missing, high-res qualities may be disabled or download as video-only.

---

## FFmpeg Not Found

The application automatically checks for FFmpeg via `imageio-ffmpeg` (installed via `requirements.txt`), system `PATH`, or a project-local `ffmpeg/` directory.

If FFmpeg is still reported as missing:

1. Reinstall project requirements:
   ```bash
   pip install -r requirements.txt
   ```
2. Verify if system FFmpeg is available:
   ```bash
   ffmpeg -version
   ```
3. Restart the application.

---

## MP3 Conversion Does Not Work

Audio conversion to MP3 uses FFmpeg. Ensure FFmpeg is available using the steps above.

---

## Download Stops Mid-Way or Fails

Possible causes:
- Temporary network interruption.
- Disk space exhausted on the target drive.
- Outdated `yt-dlp` version.

Run `pip install -U yt-dlp` to ensure latest extractor compatibility.

---

## Progress Reaches Completion But Status Says Merging

When downloading 1080p+ formats, video and audio streams finish downloading before FFmpeg combines them into a single file. Processing is complete once the **Open Folder** button appears and status changes to `Download completed successfully!`.

---

## Application Window Controls Cut Off

The application features a responsive layout. If your display resolution is compact, scroll down vertically inside the window to access all controls and quality options.

---

## Where Are Downloaded Files Located?

All downloaded media files are saved to:

```text
downloads/
```

Click the **Open Folder** button in the app to open this directory directly in your file manager.

---

## Where Are Application Logs Located?

Application logs are saved to:

```text
logs/app.log
```

Open this log file to inspect detailed stack traces when troubleshooting errors.
