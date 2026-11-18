"""Tests for user IR / clone slot name dumps."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest

from sonicake_manager.decode import decode_clone_names, decode_ir_names


def make_dump(magic: bytes, names: list[str]) -> bytes:
    assert len(names) == 5
    records = []
    for name in names:
        raw = name.encode("ascii")
        records.append(raw[:16].ljust(16, b"\x00"))
    return magic + b"\x01" * 5 + b"".join(records)


def test_decode_ir_names():
    dump = make_dump(bytes([0x12, 0x20]), ["User IR 1", "Bright cab", "Vox 4x12", "", "Empty-ish"])
    assert decode_ir_names(dump) == ["User IR 1", "Bright cab", "Vox 4x12", "", "Empty-ish"]


def test_decode_clone_names():
    dump = make_dump(bytes([0x12, 0x24]), ["Empty", "My profile", "", "Profile 4", "Last slot"])
    assert decode_clone_names(dump) == ["Empty", "My profile", "", "Profile 4", "Last slot"]


def test_decode_slot_names_rejects_bad_dump():
    with pytest.raises(ValueError):
        decode_ir_names(b"\x00" * 10)
    with pytest.raises(ValueError):
        decode_clone_names(make_dump(bytes([0x12, 0x20]), ["Empty"] * 5))
