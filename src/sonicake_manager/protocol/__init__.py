"""Protocol-level primitives for the Sonicake SysEx protocol."""

from .framing import (
    Frame,
    PacketReassembler,
    build_chunked_frames,
    build_frame,
    collapse_nibble,
    crc8_smbus,
    expand_nibble,
    nibble_collapse,
    nibble_expand,
    parse_frame,
)
from .requests import REQUESTS, request_bytes

__all__ = [
    "Frame",
    "PacketReassembler",
    "REQUESTS",
    "build_chunked_frames",
    "build_frame",
    "collapse_nibble",
    "crc8_smbus",
    "expand_nibble",
    "nibble_collapse",
    "nibble_expand",
    "parse_frame",
    "request_bytes",
]
