"""Framing for the Sonicake SysEx protocol.

Wire format:

    8080 F0 <CRC> <total> <seq> <len> <payload> F7

Every logical byte is transmitted as two nibble-expanded bytes (hi, lo).
The CRC is CRC-8/SMBUS over the logical bytes.
"""

from __future__ import annotations

import struct

BLE_HEADER = 0x8080
SYSEX_START = 0xF0
SYSEX_END = 0xF7

MAX_PAYLOAD = 0xFF


def crc8_smbus(data: bytes) -> int:
    """CRC-8/SMBUS (poly 0x07, init 0x00, no reflection, no xor-out)."""
    crc = 0x00
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x80:
                crc = ((crc << 1) ^ 0x07) & 0xFF
            else:
                crc = (crc << 1) & 0xFF
    return crc


def expand_nibble(byte: int) -> bytes:
    """Expand one logical byte into two nibble-expanded bytes."""
    if not 0 <= byte <= 0xFF:
        raise ValueError(f"byte out of range: {byte!r}")
    return bytes([(byte >> 4) & 0x0F, byte & 0x0F])


def collapse_nibble(hi: int, lo: int) -> int:
    if not (0 <= hi <= 0x0F and 0 <= lo <= 0x0F):
        raise ValueError(f"nibble out of range: {hi!r} {lo!r}")
    return (hi << 4) | lo


def nibble_expand(data: bytes) -> bytes:
    return b"".join(expand_nibble(b) for b in data)


def nibble_collapse(data: bytes) -> bytes:
    if len(data) % 2 != 0:
        raise ValueError("nibble-expanded data must have even length")
    return bytes(collapse_nibble(data[i], data[i + 1]) for i in range(0, len(data), 2))


def encode_request(command2: bytes) -> bytes:
    """Encode a read request frame (len=2, raw payload, BLE header)."""
    if len(command2) != 2:
        raise ValueError("request payload must be exactly 2 bytes")
    body = bytes([0x01, 0x00, len(command2)]) + command2
    crc = crc8_smbus(body)
    frame = bytearray()
    frame += struct.pack(">H", BLE_HEADER)
    frame += bytes([SYSEX_START])
    frame += expand_nibble(crc)
    frame += expand_nibble(0x01)  # total = 1
    frame += expand_nibble(0x00)  # seq = 0
    frame += expand_nibble(len(command2))
    frame += command2
    frame += bytes([SYSEX_END])
    return bytes(frame)


def encode_write(payload: bytes) -> bytes:
    """Encode a write frame with nibble-expanded payload, BLE header, CRC-8."""
    if len(payload) > MAX_PAYLOAD:
        raise ValueError("payload too large")
    body = bytes([0x01, 0x00, len(payload)]) + payload
    crc = crc8_smbus(body)
    frame = bytearray()
    frame += struct.pack(">H", BLE_HEADER)
    frame += bytes([SYSEX_START])
    frame += expand_nibble(crc)
    frame += expand_nibble(0x01)  # total = 1
    frame += expand_nibble(0x00)  # seq = 0
    frame += expand_nibble(len(payload))
    frame += nibble_expand(payload)
    frame += bytes([SYSEX_END])
    return bytes(frame)


class Frame:
    """Parsed inbound frame."""

    def __init__(self, *, total: int, seq: int, len_field: int, payload: bytes) -> None:
        self.total = total
        self.seq = seq
        self.len = len_field
        self.payload = payload

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"Frame(total={self.total}, seq={self.seq}, len={self.len}, payload={self.payload.hex()})"


def parse_frame(data: bytes) -> Frame:
    """Parse an inbound frame. Raises ValueError on malformed data."""
    if not data.startswith(b"\x80\x80\xF0"):
        raise ValueError("missing BLE header or F0")
    if not data.endswith(b"\xF7"):
        raise ValueError("missing F7 terminator")

    body = data[3:-1]  # strip 8080 F0 ... F7
    if len(body) < 6:
        raise ValueError("frame too short")

    crc = collapse_nibble(body[0], body[1])
    total = collapse_nibble(body[2], body[3])
    seq = collapse_nibble(body[4], body[5])
    len_field = collapse_nibble(body[6], body[7])

    expanded = body[8:]
    if len(expanded) != len_field * 2:
        raise ValueError(
            f"payload size mismatch: declared {len_field} logical bytes "
            f"(expected {len_field * 2} wired bytes), got {len(expanded)}"
        )

    payload = nibble_collapse(expanded)
    if crc8_smbus(bytes([total, seq, len_field]) + payload) != crc:
        raise ValueError("CRC mismatch")

    return Frame(total=total, seq=seq, len_field=len_field, payload=payload)


class PacketReassembler:
    """Collects multi-packet responses and returns the full logical payload."""

    def __init__(self) -> None:
        self._total: int | None = None
        self._packets: dict[int, bytes] = {}

    def add(self, frame: Frame) -> bytes | None:
        if self._total is None:
            self._total = frame.total
        elif frame.total != self._total:
            raise ValueError(f"inconsistent total: expected {self._total}, got {frame.total}")

        self._packets[frame.seq] = frame.payload

        if len(self._packets) == self._total:
            ordered = [self._packets[i] for i in range(self._total)]
            payload = b"".join(ordered)
            self.reset()
            return payload

        return None

    def reset(self) -> None:
        self._total = None
        self._packets = {}
