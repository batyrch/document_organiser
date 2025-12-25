#!/usr/bin/env python3
"""
Build a native macOS .app bundle for Document Organizer.

This approach does NOT use PyInstaller. Instead, it creates a simple .app bundle
that uses the system Python (or Homebrew Python) and manages its own venv.

Benefits:
- No PyInstaller bundling issues with Streamlit/multiprocessing
- Smaller app size (dependencies installed on first run)
- Auto-updates dependencies when requirements.txt changes
- Uses native system Python (more reliable)

Usage:
    python build_macos_native.py
"""

import os
import shutil
import stat
from pathlib import Path

# Configuration
APP_NAME = "Document Organizer"
BUNDLE_ID = "com.documentorganizer.app"
VERSION = "1.0.0"

# Files to include in the app bundle
APP_FILES = [
    "ui.py",
    "document_organizer.py",
    "ai_providers.py",
    "settings.py",
    "device_auth.py",
    "config.yaml",
    "requirements.txt",
]

# Optional files (include if they exist)
OPTIONAL_FILES = [
    ".env.example",
]


def create_info_plist(app_path: Path) -> None:
    """Create the Info.plist file for the app bundle."""
    plist_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleDevelopmentRegion</key>
    <string>en</string>
    <key>CFBundleExecutable</key>
    <string>launch.sh</string>
    <key>CFBundleIconFile</key>
    <string>AppIcon</string>
    <key>CFBundleIdentifier</key>
    <string>{BUNDLE_ID}</string>
    <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>
    <key>CFBundleName</key>
    <string>{APP_NAME}</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>{VERSION}</string>
    <key>CFBundleVersion</key>
    <string>{VERSION}</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.15</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>NSHumanReadableCopyright</key>
    <string>Copyright 2024. All rights reserved.</string>
    <key>LSUIElement</key>
    <false/>
    <key>NSDocumentsFolderUsageDescription</key>
    <string>Document Organizer needs access to your Documents folder to organize your files.</string>
    <key>NSDesktopFolderUsageDescription</key>
    <string>Document Organizer needs access to your Desktop to organize files stored there.</string>
    <key>NSDownloadsFolderUsageDescription</key>
    <string>Document Organizer needs access to your Downloads folder to organize downloaded documents.</string>
</dict>
</plist>
'''
    plist_path = app_path / "Contents" / "Info.plist"
    plist_path.write_text(plist_content)
    print(f"  Created: {plist_path}")


def create_pkginfo(app_path: Path) -> None:
    """Create the PkgInfo file."""
    pkginfo_path = app_path / "Contents" / "PkgInfo"
    pkginfo_path.write_text("APPL????")
    print(f"  Created: {pkginfo_path}")


def create_app_icon(resources_path: Path) -> None:
    """Create a simple app icon (placeholder - can be replaced with real icon)."""
    # For now, we'll create a minimal iconset
    # Users can replace AppIcon.icns with their own
    iconset_path = resources_path / "AppIcon.iconset"
    iconset_path.mkdir(exist_ok=True)

    # Create a simple PNG icon using Python (requires PIL for real icons)
    # For now, just note that icon should be added
    print("  Note: Add your own AppIcon.icns to Resources/ for a custom icon")


def build_app() -> None:
    """Build the macOS .app bundle."""
    project_dir = Path(__file__).parent
    dist_dir = project_dir / "dist"
    app_path = dist_dir / f"{APP_NAME}.app"

    print(f"Building {APP_NAME}.app...")
    print(f"Project directory: {project_dir}")

    # Clean previous build
    if app_path.exists():
        print(f"Removing existing app bundle...")
        shutil.rmtree(app_path)

    # Create directory structure
    contents_path = app_path / "Contents"
    macos_path = contents_path / "MacOS"
    resources_path = contents_path / "Resources"

    for path in [contents_path, macos_path, resources_path]:
        path.mkdir(parents=True, exist_ok=True)
        print(f"  Created: {path}")

    # Create Info.plist and PkgInfo
    create_info_plist(app_path)
    create_pkginfo(app_path)

    # Copy launcher script to MacOS directory
    launcher_src = project_dir / "desktop" / "launch.sh"
    launcher_dst = macos_path / "launch.sh"

    if not launcher_src.exists():
        print(f"ERROR: Launcher script not found: {launcher_src}")
        return

    shutil.copy2(launcher_src, launcher_dst)
    # Ensure executable
    launcher_dst.chmod(launcher_dst.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    print(f"  Copied: {launcher_dst}")

    # Copy application files to Resources
    print("\nCopying application files...")
    for filename in APP_FILES:
        src = project_dir / filename
        dst = resources_path / filename
        if src.exists():
            shutil.copy2(src, dst)
            print(f"  Copied: {filename}")
        else:
            print(f"  WARNING: Missing required file: {filename}")

    # Copy optional files
    for filename in OPTIONAL_FILES:
        src = project_dir / filename
        dst = resources_path / filename
        if src.exists():
            shutil.copy2(src, dst)
            print(f"  Copied: {filename} (optional)")

    # Create icon placeholder
    create_app_icon(resources_path)

    print(f"\n{'='*50}")
    print(f"Build complete!")
    print(f"App bundle: {app_path}")
    print(f"\nTo test, run:")
    print(f"  open \"{app_path}\"")
    print(f"\nTo distribute:")
    print(f"  1. Add your AppIcon.icns to {resources_path}/")
    print(f"  2. Code sign: codesign --deep --force --sign - \"{app_path}\"")
    print(f"  3. Create DMG: hdiutil create -volname \"{APP_NAME}\" -srcfolder \"{app_path}\" -ov \"{dist_dir}/{APP_NAME}.dmg\"")


if __name__ == "__main__":
    build_app()
