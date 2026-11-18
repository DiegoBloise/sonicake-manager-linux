"""Framing for the Sonicake SysEx protocol.

Wire format:

    8080 F0 <crc> <total> <seq> <len> <payload> F7

Where each logical byte (including CRC/total/seq/len) is transmitted as two
nibble-expanded bytes (hi, lo) and the payload is the nibble-expansion of its
logical bytes.

The CRC is CRC-8/SMBUS over the "seed" bytes plus the logical payload:

    seed = [0x01, 0x00, len]      (single packet / commands)
    seed = [total, seq, len]      (multi-packet uploads, total != 1)
"""

from __future__ import annotations

import struct

BLE_HEADER = 0x8080
SYSEX_START = 0xF0
SYSEX_END = 0xF7

MAX_PAYLOAD = 0xFF


def crc8_smbus(data: bytes | list[int]) -> int:
    """CRC-8/SMBUS (poly 0x07, init 0x00, no reflection, no xor-out)."""
    crc = 0x00
    for byte in data:
        crc ^= byte & 0xFF
        for _ in range(8):
            if crc & 0x80:
                crc = ((crc << 1) ^ 0x07) & 0xFF
            else:
                crc = (crc << 1) & 0xFF
    return crc


def expand_nibble(byte: int) -> bytes:
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


def _unwrap(data: bytes) -> bytes:
    """Strip the optional ``8080`` prefix and the F0..F7 wrappers."""
    body = data
    if body.startswith(b"\x80\x80"):
        body = body[2:]
    if not body.startswith(b"\xF0"):
        raise ValueError("missing F0 start byte")
    if not body.endswith(b"\xF7"):
        raise ValueError("missing F7 terminator")
    return body[1:-1]


def build_frame(payload: bytes, *, total: int = 1, seq: int = 0) -> bytes:
    """Build a full frame. CRC is over [tt, ss, len] + payload."""
    if len(payload) > MAX_PAYLOAD:
        raise ValueError("payload too large")
    tt, ss = (0x01, 0x00) if total == 1 else (total, seq)
    body = bytes([tt, ss, len(payload)]) + payload
    crc = crc8_smbus(body)

    frame = bytearray()
    frame += struct.pack(">H", BLE_HEADER)
    frame += bytes([SYSEX_START])
    frame += expand_nibble(crc)
    frame += expand_nibble(total)
    frame += expand_nibble(seq)
    frame += expand_nibble(len(payload))
    frame += nibble_expand(payload)
    frame += bytes([SYSEX_END])
    return bytes(frame)


def build_chunked_frames(blob: bytes, chunk_size: int = 19) -> list[bytes]:
    """Split a blob into ACK-able multi-packet frames (IR/clone upload)."""
    total = (len(blob) + chunk_size - 1) // chunk_size
    frames = []
    for seq in range(total):
        chunk = blob[seq * chunk_size : (seq + 1) * chunk_size]
        frames.append(build_frame(chunk, total=total, seq=seq))
    return frames


class Frame:
    """Parsed inbound frame."""

    def __init__(self, *, total: int, seq: int, len_field: int, payload: bytes) -> None:
        self.total = total
        self.seq = seq
        self.len = len_field
        self.payload = payload

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return (
            f"Frame(total={self.total}, seq={self.seq}, "
            f"len={self.len}, payload={self.payload.hex()})"
        )


def parse_frame(data: bytes) -> Frame:
    """Parse a full frame. Raises ValueError on malformed data.

    The ``8080`` prefix is a transport-level artifact and is accepted
    optionally; responses from the device do not carry it.
    """
    body = _unwrap(data)
    if len(body) < 8 or len(body) % 2 != 0:
        raise ValueError("frame too short or odd-length body")

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
    tt, ss = (0x01, 0x00) if total == 1 else (total, seq)
    if crc8_smbus(bytes([tt, ss, len_field]) + payload) != crc:
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
            payload = b"".join(self._packets[i] for i in range(self._total))
            self.reset()
            return payload
        return None

    def reset(self) -> None:
        self._total = None
        self._packets = {}
