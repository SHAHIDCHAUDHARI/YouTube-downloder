"""
Auto-installer script to clean non-essential GitHub files, set up runtime directories,
and install dependencies. Can be executed via terminal or double-clicked.
"""

import sys
import shutil
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def setup():
    print("==========================================")
    print("      Media Downloader Auto Setup         ")
    print("==========================================")

    # Step 1: Clean up extra GitHub files (assets, .gitignore, README.md)
    print("\n[1/4] Cleaning up extra files...")
    files_to_remove = [
        BASE_DIR / ".gitignore",
        BASE_DIR / "README.md",
    ]
    for file_path in files_to_remove:
        if file_path.exists():
            try:
                file_path.unlink()
            except Exception:
                pass

    assets_dir = BASE_DIR / "assets"
    if assets_dir.exists():
        try:
            shutil.rmtree(assets_dir, ignore_errors=True)
        except Exception:
            pass
    print("✓ Extra files cleaned up.")

    # Step 2: Create downloads folder
    print("\n[2/4] Creating downloads folder...")
    (BASE_DIR / "downloads").mkdir(exist_ok=True)
    print("✓ Downloads folder ready.")

    # Step 3: Download & install dependencies
    print("\n[3/4] Installing required Python packages...")
    requirements_file = BASE_DIR / "requirements.txt"

    if requirements_file.exists():
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", str(requirements_file)])
            print("✓ Dependencies installed successfully.")
        except Exception as e:
            print(f"❌ Error installing dependencies: {e}")
            input("\nPress Enter to exit...")
            sys.exit(1)
    else:
        print("Note: requirements.txt already processed or missing.")

    # Step 4: Remove requirements.txt after successful installation
    print("\n[4/4] Finalizing setup...")
    if requirements_file.exists():
        try:
            requirements_file.unlink()
        except Exception:
            pass
    print("✓ Setup finalized.")

    print("\n==========================================")
    print(" Setup Complete!")
    print(" Now run 'python run.py' or double-click run.py to start.")
    print("==========================================\n")

    input("Press Enter to finish...")


if __name__ == "__main__":
    setup()
