"""Exception types for the ALSA sequencer transport."""

from __future__ import annotations


class TransportError(RuntimeError):
    """Raised when the ALSA sequencer cannot be opened or used."""
