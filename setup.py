"""
Auto-installer script to install dependencies and set up runtime directories.
Can be executed via terminal or double-clicked.
"""

import sys
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def setup():
    print("==========================================")
    print("      Media Downloader Auto Setup         ")
    print("==========================================")
    print("\n[1/2] Installing required Python packages...")

    requirements_file = BASE_DIR / "requirements.txt"
    if not requirements_file.exists():
        print("Error: requirements.txt not found!")
        input("\nPress Enter to exit...")
        sys.exit(1)

    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", str(requirements_file)])
        print("✓ Dependencies installed successfully.")
    except Exception as e:
        print(f"❌ Error installing dependencies: {e}")
        input("\nPress Enter to exit...")
        sys.exit(1)

    print("\n[2/2] Creating runtime directories...")
    (BASE_DIR / "downloads").mkdir(exist_ok=True)
    (BASE_DIR / "assets").mkdir(exist_ok=True)
    print("✓ Runtime directories ready.")

    print("\n==========================================")
    print(" Setup Complete!")
    print(" Now run 'python run.py' or double-click run.py to start.")
    print("==========================================\n")

    input("Press Enter to finish...")


if __name__ == "__main__":
    setup()
