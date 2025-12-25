#!/usr/bin/env python3
"""
Build script for creating a macOS .app bundle using PyInstaller.

Usage:
    python build_macos.py

This creates:
    dist/Document Organizer.app

To distribute:
    1. cd dist
    2. zip -r "Document-Organizer-macOS.zip" "Document Organizer.app"
    3. Upload to GitHub Releases or your website
"""

import subprocess
import sys
from pathlib import Path

# Ensure we're in the project root
PROJECT_ROOT = Path(__file__).parent
APP_NAME = "Document Organizer"


def check_pyinstaller():
    """Ensure PyInstaller is installed."""
    try:
        import PyInstaller
        print(f"PyInstaller version: {PyInstaller.__version__}")
    except ImportError:
        print("PyInstaller not found. Installing...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)


def build():
    """Build the macOS app bundle."""
    check_pyinstaller()

    # Files to bundle with the app
    data_files = [
        "ui.py",
        "document_organizer.py",
        "ai_providers.py",
        "settings.py",
        "config.yaml",
        "pwa/app.html",  # Local HTML wrapper to avoid HTTPS/localhost issues
    ]

    # Build the PyInstaller command
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", APP_NAME,
        "--windowed",  # No console window on macOS
        "--onedir",    # Create a directory bundle (smaller than --onefile)
        "--noconfirm", # Overwrite existing build
        "--clean",     # Clean cache before building
    ]

    # Add data files
    for f in data_files:
        file_path = PROJECT_ROOT / f
        if file_path.exists():
            # Format: source:destination (destination is relative to bundle)
            cmd.extend(["--add-data", f"{file_path}:."])
        else:
            print(f"Warning: {f} not found, skipping")

    # Add hidden imports that PyInstaller might miss
    hidden_imports = [
        "streamlit",
        "streamlit.web.cli",
        "streamlit.runtime.scriptrunner",
        "anthropic",
        "openai",
        "PIL",
        "PIL.Image",
        "pdfplumber",
        "yaml",
        "dotenv",
    ]

    for imp in hidden_imports:
        cmd.extend(["--hidden-import", imp])

    # Collect all of streamlit's data files
    cmd.extend(["--collect-all", "streamlit"])

    # Entry point
    cmd.append(str(PROJECT_ROOT / "desktop" / "launcher.py"))

    print(f"\nBuilding {APP_NAME}...")
    print(f"Command: {' '.join(cmd)}\n")

    # Run PyInstaller
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)

    if result.returncode == 0:
        app_path = PROJECT_ROOT / "dist" / f"{APP_NAME}.app"
        print(f"\n{'='*60}")
        print(f"Build successful!")
        print(f"App location: {app_path}")
        print(f"\nTo create distributable zip:")
        print(f"  cd {PROJECT_ROOT / 'dist'}")
        print(f'  zip -r "Document-Organizer-macOS.zip" "{APP_NAME}.app"')
        print(f"{'='*60}")
    else:
        print(f"\nBuild failed with exit code {result.returncode}")
        sys.exit(1)


if __name__ == "__main__":
    build()
