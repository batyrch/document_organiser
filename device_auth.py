#!/usr/bin/env python3
"""
Device Authentication Module - Mullvad-style device identification.

Generates and stores a unique device ID for billing/licensing purposes.
No accounts, no emails - just a device number that maps to payment status.

Device ID format: XXXX-XXXX-XXXX-XXXX (16 hex characters, grouped)
Example: a1b2-c3d4-e5f6-7890

Storage: OS keychain (secure, persists across reinstalls)
"""

import uuid
import hashlib
import platform
from typing import Optional

# Keychain configuration
KEYCHAIN_SERVICE = "DocumentOrganizer"
DEVICE_ID_KEY = "device_id"
DEVICE_FINGERPRINT_KEY = "device_fingerprint"


def _get_keyring():
    """Get keyring module, return None if not available."""
    try:
        import keyring
        return keyring
    except ImportError:
        return None


def generate_device_id() -> str:
    """Generate a new Mullvad-style device ID.

    Format: XXXX-XXXX-XXXX-XXXX (16 hex characters)
    Example: a1b2-c3d4-e5f6-7890
    """
    raw_uuid = uuid.uuid4().hex[:16]  # 16 hex characters
    return "-".join([raw_uuid[i:i+4] for i in range(0, 16, 4)])


def generate_device_fingerprint() -> str:
    """Generate a hardware fingerprint to identify this device.

    Used to detect if the device ID was copied to another machine.
    This is a hash of system identifiers, not reversible.
    """
    data_parts = [
        platform.node(),           # Hostname
        platform.machine(),        # Machine type (x86_64, arm64, etc.)
        str(uuid.getnode()),       # MAC address as integer
        platform.system(),         # OS name
    ]
    data = "-".join(data_parts)
    return hashlib.sha256(data.encode()).hexdigest()[:32]


def get_device_id() -> Optional[str]:
    """Get the stored device ID from keychain."""
    keyring = _get_keyring()
    if keyring is None:
        return None
    try:
        return keyring.get_password(KEYCHAIN_SERVICE, DEVICE_ID_KEY)
    except Exception:
        return None


def get_device_fingerprint() -> Optional[str]:
    """Get the stored device fingerprint from keychain."""
    keyring = _get_keyring()
    if keyring is None:
        return None
    try:
        return keyring.get_password(KEYCHAIN_SERVICE, DEVICE_FINGERPRINT_KEY)
    except Exception:
        return None


def store_device_id(device_id: str) -> bool:
    """Store device ID in keychain. Returns True on success."""
    keyring = _get_keyring()
    if keyring is None:
        return False
    try:
        keyring.set_password(KEYCHAIN_SERVICE, DEVICE_ID_KEY, device_id)
        return True
    except Exception:
        return False


def store_device_fingerprint(fingerprint: str) -> bool:
    """Store device fingerprint in keychain. Returns True on success."""
    keyring = _get_keyring()
    if keyring is None:
        return False
    try:
        keyring.set_password(KEYCHAIN_SERVICE, DEVICE_FINGERPRINT_KEY, fingerprint)
        return True
    except Exception:
        return False


def get_or_create_device_id() -> tuple[str, bool]:
    """Get existing device ID or create a new one.

    Returns:
        Tuple of (device_id, is_new)
        - device_id: The device identifier
        - is_new: True if this was newly generated, False if existing
    """
    existing_id = get_device_id()

    if existing_id:
        # Verify fingerprint matches (optional security check)
        stored_fp = get_device_fingerprint()
        current_fp = generate_device_fingerprint()

        if stored_fp and stored_fp != current_fp:
            # Fingerprint mismatch - device ID may have been copied
            # For now, just log a warning but still use the ID
            # A stricter implementation could reject the ID
            pass

        return existing_id, False

    # Generate new device ID and fingerprint
    new_id = generate_device_id()
    new_fp = generate_device_fingerprint()

    # Store both
    id_stored = store_device_id(new_id)
    fp_stored = store_device_fingerprint(new_fp)

    if not id_stored:
        # Keychain not available, return ID but it won't persist
        return new_id, True

    return new_id, True


def has_keychain_support() -> bool:
    """Check if keychain is available for secure storage."""
    return _get_keyring() is not None


def get_device_info() -> dict:
    """Get full device information for display/debugging.

    Returns dict with:
        - device_id: The device identifier (or None)
        - fingerprint: Current device fingerprint
        - keychain_available: Whether keychain storage is available
        - fingerprint_match: Whether stored fingerprint matches current
    """
    device_id = get_device_id()
    stored_fp = get_device_fingerprint()
    current_fp = generate_device_fingerprint()

    return {
        "device_id": device_id,
        "fingerprint": current_fp[:8] + "..." if current_fp else None,  # Truncated for display
        "keychain_available": has_keychain_support(),
        "fingerprint_match": stored_fp == current_fp if stored_fp else None,
    }


# Convenience function for app initialization
def initialize_device() -> str:
    """Initialize device authentication on app startup.

    Call this once during app initialization.
    Returns the device ID.
    """
    device_id, is_new = get_or_create_device_id()

    if is_new:
        print(f"New device registered: {device_id}")

    return device_id
