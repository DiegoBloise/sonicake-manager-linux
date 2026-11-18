"""High-level device API: read presets, names, globals over a transport."""

from __future__ import annotations

from typing import Any

from .decode import (
    decode_globals,
    decode_preset_names,
    decode_state,
    is_ack,
    is_nack,
    is_preset_modified,
    is_preset_saved,
)
from .protocol import REQUESTS, PacketReassembler, parse_frame


class DeviceError(RuntimeError):
    """Raised when the device does not respond or answers with NACK."""


class SonicakeDevice:
    """Speaks to one Sonicake processor over a transport."""

    def __init__(self, transport) -> None:
        self._transport = transport

    # -- transport plumbing ---------------------------------------------------

    def request_payload(self, request_name: str, *, timeout: float = 5.0, idle_timeout: float = 0.6) -> bytes:
        """Send a documented read request, reassemble any dump, return logical payload."""
        if request_name not in REQUESTS:
            raise KeyError(f"unknown request: {request_name!r}")
        frame = bytes.fromhex(REQUESTS[request_name])
        messages = self._transport.request(frame, timeout=timeout, idle_timeout=idle_timeout)
        if not messages:
            raise DeviceError(f"no response to request {request_name!r}")

        reassembler = PacketReassembler()
        payload: bytes | None = None
        for message in messages:
            try:
                parsed = parse_frame(message)
            except ValueError:
                continue  # ignore non-Sonicake traffic / stray bytes
            result = reassembler.add(parsed)
            if result is not None:
                payload = result
        if payload is None:
            raise DeviceError(f"incomplete dump for request {request_name!r}")
        return payload

    def wait_ack(self, timeout: float = 2.0, idle_timeout: float = 0.3) -> str:
        """Wait for an ACK/NACK/notification and return its kind."""
        messages = self._transport.recv(timeout=timeout, idle_timeout=idle_timeout)
        for message in messages:
            try:
                parsed = parse_frame(message)
            except ValueError:
                continue
            payload = parsed.payload
            if is_ack(payload):
                return "ack"
            if is_nack(payload):
                return "nack"
            if is_preset_modified(payload):
                return "preset-modified"
            if is_preset_saved(payload):
                return "preset-saved"
        return "timeout"

    # -- read-only queries ------------------------------------------------------

    def preset_number_raw(self) -> bytes:
        """Current preset number as reported by the device (echo stripped)."""
        payload = self.request_payload("numero", timeout=2.0, idle_timeout=0.3)
        return payload[2:] if payload[:2] == b"\x12\x43" else payload

    def preset_names(self) -> list[str]:
        payload = self.request_payload("nomes", timeout=10.0, idle_timeout=0.6)
        if len(payload) < 2002:
            # Occasionally the first packet is lost; retry once.
            payload = self.request_payload("nomes", timeout=12.0, idle_timeout=0.8)
        return decode_preset_names(payload)

    def state(self) -> dict[str, Any]:
        payload = self.request_payload("estado", timeout=6.0, idle_timeout=0.8)
        return decode_state(payload)

    def globals(self) -> dict[str, Any]:
        payload = self.request_payload("globais", timeout=4.0, idle_timeout=0.4)
        return decode_globals(payload)

    def ir_names(self) -> bytes:
        """Raw payload of the IR-names dump (layout documented in docs/)."""
        return self.request_payload("nomes_ir", timeout=4.0, idle_timeout=0.4)

    def clone_names(self) -> bytes:
        return self.request_payload("nomes_clone", timeout=4.0, idle_timeout=0.4)

    def close(self) -> None:
        close = getattr(self._transport, "close", None)
        if callable(close):
            close()

    def __enter__(self) -> "SonicakeDevice":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
