"""Tests for the framing primitives."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest

from sonicake_manager.protocol import (
    Frame,
    PacketReassembler,
    build_frame,
    build_chunked_frames,
    crc8_smbus,
    expand_nibble,
    collapse_nibble,
    nibble_expand,
    nibble_collapse,
    parse_frame,
)
from sonicake_manager.protocol.requests import REQUESTS, request_bytes


def test_crc8_smbus_known_vectors():
    assert (
        crc8_smbus(bytes([0x01, 0x00, 0x07, 0x11, 0x42, 0x01, 0x20, 0x01, 0x00, 0x4A]))
        == 0x0F
    )


def test_expand_and_collapse_roundtrip():
    for byte in (0x00, 0x01, 0x0F, 0x42, 0xA5, 0xFF):
        hi, lo = expand_nibble(byte)
        assert collapse_nibble(hi, lo) == byte


def test_nibble_expand_collapse_roundtrip():
    data = bytes([0x11, 0x42, 0x9C, 0x00, 0xFF])
    assert nibble_collapse(nibble_expand(data)) == data


def test_build_frame_request_state_roundtrip():
    payload = bytes([0x01, 0x02, 0x04, 0x01])
    frame = build_frame(payload)
    parsed = parse_frame(frame)
    assert parsed.total == 1
    assert parsed.seq == 0
    assert parsed.payload == payload


def test_build_frame_write_roundtrip():
    payload = bytes([0x11, 0x42, 0x01, 0x20, 0x01, 0x00, 0x4A, 0x00])
    frame = build_frame(payload)
    assert frame.startswith(b"\x80\x80\xf0")
    assert frame.endswith(b"\xf7")
    parsed = parse_frame(frame)
    assert parsed.payload == payload


def test_build_chunked_frames_roundtrip():
    blob = bytes(range(256 % 220, 220))
    frames = build_chunked_frames(blob, chunk_size=19)
    parsed = [parse_frame(f) for f in frames]
    assert [p.total for p in parsed] == [len(frames)] * len(frames)
    assert [p.seq for p in parsed] == list(range(len(frames)))
    assert b"".join(p.payload for p in parsed) == blob


def test_parse_multi_packet_roundtrip():
    payload1 = bytes(range(19))
    payload2 = bytes([0xAA, 0xBB, 0xCC, 0xDD, 0xEE])
    frames = build_chunked_frames(payload1 + payload2, chunk_size=19)

    reassembler = PacketReassembler()
    assert reassembler.add(parse_frame(frames[0])) is None
    result = reassembler.add(parse_frame(frames[1]))
    assert result == payload1 + payload2


def test_parse_bad_crc():
    frame = bytearray(build_frame(bytes([0x11, 0x42])))
    frame[10] ^= 0x01
    with pytest.raises(ValueError):
        parse_frame(bytes(frame))


def test_frame_invalid_header():
    with pytest.raises(ValueError):
        parse_frame(b"\x00\x00\xf0\x00\x00\x00\x00\x00\x00\x01\x01\x01\x02\xf7")


def test_requests_constants_roundtrip():
    # Documented request constants: parse must succeed and re-encoding must
    # reproduce the exact documented bytes.
    for name, hex_frame in REQUESTS.items():
        parsed = parse_frame(bytes.fromhex(hex_frame))
        assert parsed.total == 1
        assert parsed.seq == 0
        assert build_frame(parsed.payload) == bytes.fromhex(hex_frame)
        assert request_bytes(name) == bytes.fromhex(hex_frame)
