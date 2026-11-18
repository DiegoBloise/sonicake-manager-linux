"""In-memory transport used by tests (no hardware involved)."""

from __future__ import annotations

import time


class FakeTransport:
    """Records sent frames and replays canned responses."""

    def __init__(self, responses: list[bytes] | None = None) -> None:
        self.sent: list[bytes] = []
        self._responses = list(responses or [])

    def send(self, frame: bytes) -> None:
        self.sent.append(frame)

    def send_frames(self, frames: list[bytes], delay: float = 0.0) -> None:
        for frame in frames:
            self.sent.append(frame)
            if delay:
                time.sleep(delay)

    def recv(self, timeout: float = 0.0, idle_timeout: float = 0.0) -> list[bytes]:
        responses, self._responses = self._responses, []
        return responses

    def request(self, frame: bytes, timeout: float = 0.0, idle_timeout: float = 0.0) -> list[bytes]:
        self.send(frame)
        return self.recv(timeout=timeout, idle_timeout=idle_timeout)

    def close(self) -> None:
        pass

    def __enter__(self) -> "FakeTransport":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
