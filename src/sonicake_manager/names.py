"""Preset name encoding/decoding (10 characters, 4 hex chars per character)."""

from __future__ import annotations

from .data import character_map

MAX_NAME_LENGTH = 10


def decode_character_map() -> dict[str, str]:
    return {code: ch for code, ch in character_map().items() if ch}


def encode_name(name: str) -> str:
    """Encode up to 10 characters into 40 hex chars (padding ``0000``)."""
    inverse = {ch: code for code, ch in character_map().items() if ch is not None}
    codes = []
    for i in range(MAX_NAME_LENGTH):
        if i >= len(name):
            codes.append("0000")
        else:
            codes.append(inverse.get(name[i], "0000"))
    return "".join(codes)


def decode_name(hex40: str) -> str:
    """Decode 10 4-char codes into text, stopping at padding."""
    cmap = decode_character_map()
    out = []
    for i in range(0, min(len(hex40), 40), 4):
        code = hex40[i : i + 4].upper()
        if code == "0000":
            break
        ch = cmap.get(code)
        if ch is None:
            break
        out.append(ch)
    return "".join(out)
