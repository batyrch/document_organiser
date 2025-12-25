#!/usr/bin/env python3
"""
Settings management for Document Organizer.

Handles persistent user configuration stored in a JSON file.
Settings are stored in the user's config directory:
- macOS: ~/Library/Application Support/DocumentOrganizer/settings.json
- Linux: ~/.config/DocumentOrganizer/settings.json
- Windows: %APPDATA%/DocumentOrganizer/settings.json
"""

import os
import sys
import json
from pathlib import Path
from typing import Optional


def get_config_dir() -> Path:
    """Get the platform-appropriate config directory."""
    if sys.platform == "darwin":
        config_dir = Path.home() / "Library" / "Application Support" / "DocumentOrganizer"
    elif sys.platform == "win32":
        appdata = os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))
        config_dir = Path(appdata) / "DocumentOrganizer"
    else:
        # Linux and others - follow XDG spec
        xdg_config = os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))
        config_dir = Path(xdg_config) / "DocumentOrganizer"

    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_settings_path() -> Path:
    """Get path to the settings file."""
    return get_config_dir() / "settings.json"


# Default settings
DEFAULT_SETTINGS = {
    # Directory paths
    "output_dir": str(Path.home() / "Documents" / "jd_documents"),
    "inbox_dir": "",  # Will be derived from output_dir if empty

    # AI Provider settings
    "ai_provider": "auto",  # auto, anthropic, openai, ollama, claude-code, keywords
    "anthropic_api_key": "",
    "anthropic_model": "claude-sonnet-4-20250514",
    "openai_api_key": "",
    "openai_model": "gpt-4o",
    "ollama_url": "http://localhost:11434",
    "ollama_model": "llama3.2",

    # UI settings
    "theme": "system",  # system, light, dark
    "show_advanced": False,

    # First run flag
    "setup_complete": False,
}


class Settings:
    """Manage application settings with persistence."""

    def __init__(self):
        self._settings = DEFAULT_SETTINGS.copy()
        self._load()

    def _load(self):
        """Load settings from disk."""
        settings_path = get_settings_path()
        if settings_path.exists():
            try:
                with open(settings_path, 'r') as f:
                    saved = json.load(f)
                    # Merge with defaults (in case new settings were added)
                    self._settings.update(saved)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not load settings: {e}")

    def save(self):
        """Save settings to disk."""
        settings_path = get_settings_path()
        try:
            with open(settings_path, 'w') as f:
                json.dump(self._settings, f, indent=2)
        except IOError as e:
            print(f"Warning: Could not save settings: {e}")

    def get(self, key: str, default=None):
        """Get a setting value."""
        return self._settings.get(key, default)

    def set(self, key: str, value):
        """Set a setting value and save."""
        self._settings[key] = value
        self.save()

    def update(self, updates: dict):
        """Update multiple settings at once and save."""
        self._settings.update(updates)
        self.save()

    def reset(self):
        """Reset all settings to defaults."""
        self._settings = DEFAULT_SETTINGS.copy()
        self.save()

    @property
    def output_dir(self) -> str:
        """Get the output directory, with fallback to default."""
        return self._settings.get("output_dir") or DEFAULT_SETTINGS["output_dir"]

    @property
    def inbox_dir(self) -> str:
        """Get the inbox directory, deriving from output_dir if not set."""
        inbox = self._settings.get("inbox_dir")
        if inbox:
            return inbox
        # Default: output_dir/00-09 System/01 Inbox
        return str(Path(self.output_dir) / "00-09 System" / "01 Inbox")

    @property
    def ai_provider(self) -> str:
        """Get the configured AI provider."""
        return self._settings.get("ai_provider", "auto")

    @property
    def setup_complete(self) -> bool:
        """Check if initial setup has been completed."""
        return self._settings.get("setup_complete", False)

    def get_effective_provider(self) -> str:
        """Determine which AI provider to use based on settings and available credentials."""
        provider = self.ai_provider

        if provider != "auto":
            return provider

        # Auto-detect based on available credentials
        if self._settings.get("anthropic_api_key"):
            return "anthropic"
        if self._settings.get("openai_api_key"):
            return "openai"
        if os.environ.get("ANTHROPIC_API_KEY"):
            return "anthropic"
        if os.environ.get("OPENAI_API_KEY"):
            return "openai"

        # Check if Claude Code CLI is available
        import shutil
        if shutil.which("claude"):
            return "claude-code"

        # Check if Ollama is running
        try:
            import requests
            response = requests.get(f"{self._settings.get('ollama_url', 'http://localhost:11434')}/api/tags", timeout=2)
            if response.status_code == 200:
                return "ollama"
        except (ImportError, OSError, Exception):
            pass

        # Fallback to keywords
        return "keywords"

    def validate_directories(self) -> tuple[bool, list[str]]:
        """Validate that configured directories exist or can be created.

        Returns (is_valid, list_of_errors)
        """
        errors = []

        output_path = Path(self.output_dir)
        inbox_path = Path(self.inbox_dir)

        # Check output directory
        if output_path.exists():
            if not output_path.is_dir():
                errors.append(f"Output path exists but is not a directory: {output_path}")
            elif not os.access(output_path, os.W_OK):
                errors.append(f"Output directory is not writable: {output_path}")
        else:
            # Check if parent exists and is writable
            parent = output_path.parent
            if parent.exists() and not os.access(parent, os.W_OK):
                errors.append(f"Cannot create output directory (parent not writable): {output_path}")

        # Check inbox directory (similar logic)
        if inbox_path.exists():
            if not inbox_path.is_dir():
                errors.append(f"Inbox path exists but is not a directory: {inbox_path}")
            elif not os.access(inbox_path, os.W_OK):
                errors.append(f"Inbox directory is not writable: {inbox_path}")

        return len(errors) == 0, errors

    def create_directories(self) -> tuple[bool, Optional[str]]:
        """Create the configured directories if they don't exist.

        Returns (success, error_message)
        """
        try:
            output_path = Path(self.output_dir)
            inbox_path = Path(self.inbox_dir)

            output_path.mkdir(parents=True, exist_ok=True)
            inbox_path.mkdir(parents=True, exist_ok=True)

            return True, None
        except Exception as e:
            return False, str(e)

    def to_dict(self) -> dict:
        """Export settings as a dictionary."""
        return self._settings.copy()


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get the global settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reload_settings():
    """Force reload settings from disk."""
    global _settings
    _settings = Settings()
    return _settings
