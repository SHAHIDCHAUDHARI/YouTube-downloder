# Contributing to Media Downloader

Thank you for your interest in contributing to Media Downloader.

## Development Setup

1. Fork the repository and clone your fork locally:
   ```bash
   git clone https://github.com/<your-username>/<repository-name>.git
   cd <repository-name>
   ```

2. Set up a virtual environment:
   ```bash
   python -m venv .venv
   ```

   - **Windows**: `.venv\Scripts\activate`
   - **macOS / Linux**: `source .venv/bin/activate`

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Run the application:
   ```bash
   python app.py
   ```

## Pull Request Guidelines

- Keep changes focused and clear.
- Ensure the application launches and downloads test URLs without errors before submitting.
- Avoid committing downloaded media files or personal log files.
- Follow existing formatting and naming conventions across `app/` modules.
