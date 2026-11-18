"""Tests for name encoding/decoding."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sonicake_manager.decode import collapse_hex, decode_preset_names
from sonicake_manager.names import decode_name, encode_name


def test_name_roundtrip():
    assert decode_name(encode_name("MEU TOM")) == "MEU TOM"


def test_decode_stops_at_padding():
    codes = encode_name("AB") + "020C" + "0000" * 6
    assert decode_name(codes) == "AB"


def test_encode_unknown_chars_become_padding():
    assert encode_name('"$?\x01\x7f') == "0000" * 5 + "0000" * 5


def test_decode_names_dump_layout():
    # decode_preset_names expects the payload whose expanded form holds
    # 100 slots of 40 hex chars starting at hex offset 24, stride 80 chars.
    expanded = bytearray((12 + 40 * 99) * 2 + 40)
    for idx, _ in enumerate(expanded):
        expanded[idx] = ord("0")
    expanded[12 * 2 : 12 * 2 + 40] = encode_name("FIRST").encode("ascii")
    base = (12 + 40 * 99) * 2
    expanded[base : base + 40] = encode_name("LAST").encode("ascii")
    payload = collapse_hex(expanded.decode("ascii"))

    names = decode_preset_names(payload)
    assert len(names) == 100
    assert names[0] == "FIRST"
    assert names[99] == "LAST"
    assert names[1] == ""
