"""Protocol-level primitives for the Sonicake SysEx protocol."""

from .framing import (
    Frame,
    PacketReassembler,
    collapse_nibble,
    crc8_smbus,
    encode_request,
    encode_write,
    expand_nibble,
    nibble_collapse,
    nibble_expand,
    parse_frame,
)

__all__ = [
    "Frame",
    "PacketReassembler",
    "collapse_nibble",
    "crc8_smbus",
    "encode_request",
    "encode_write",
    "expand_nibble",
    "nibble_collapse",
    "nibble_expand",
    "parse_frame",
]
