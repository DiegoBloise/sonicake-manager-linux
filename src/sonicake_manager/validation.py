"""Validation helpers for preset names."""

from __future__ import annotations

from .names import encodable_chars, MAX_NAME_LENGTH


def is_valid_name(name: str) -> bool:
    """True if every character can be encoded and the name fits the device."""
    if not name:
        return False
    ok = encodable_chars()
    return len(name) <= MAX_NAME_LENGTH and all(ch in ok for ch in name)


def name_filter_hint() -> str:
    """Human-readable hint of the encodable character set size."""
    return f"at most {MAX_NAME_LENGTH} characters from the device character set"
