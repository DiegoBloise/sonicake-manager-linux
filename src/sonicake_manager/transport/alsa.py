"""ALSA sequencer transport via libasound (no compiled dependencies).

Uses ctypes over ``libasound.so.2``.  The device is reached through the
ALSA sequencer (not rawmidi), so it works alongside PipeWire/JACK.
"""

from __future__ import annotations

import ctypes
import ctypes.util
import os
import select
import time
from dataclasses import dataclass

from .errors import TransportError

# --- libasound constants (see alsa-lib headers) ------------------------------

SND_SEQ_OPEN_DUPLEX = 3
SND_SEQ_NONBLOCK = 1

SND_SEQ_PORT_CAP_READ = 1 << 0
SND_SEQ_PORT_CAP_WRITE = 1 << 1
SND_SEQ_PORT_CAP_SUBS_READ = 1 << 5
SND_SEQ_PORT_CAP_SUBS_WRITE = 1 << 6

SND_SEQ_PORT_TYPE_MIDI_GENERIC = 1 << 1
SND_SEQ_PORT_TYPE_HARDWARE = 1 << 16
SND_SEQ_PORT_TYPE_SOFTWARE = 1 << 17
SND_SEQ_PORT_TYPE_APPLICATION = 1 << 20

SND_SEQ_EVENT_SYSEX = 130
SND_SEQ_EVENT_LENGTH_VARIABLE = 1 << 2
SND_SEQ_QUEUE_DIRECT = 253

POLLIN = 0x0001


# --- ctypes structs -----------------------------------------------------------


class _RealTime(ctypes.Structure):
    _fields_ = [("tv_sec", ctypes.c_uint32), ("tv_nsec", ctypes.c_uint32)]


class _Timestamp(ctypes.Union):
    _fields_ = [("tick", ctypes.c_uint32), ("time", _RealTime)]


class _Addr(ctypes.Structure):
    _fields_ = [("client", ctypes.c_ubyte), ("port", ctypes.c_ubyte)]


class _Ext(ctypes.Structure):
    _layout_ = "ms"
    _pack_ = 1  # C struct snd_seq_ev_ext is packed: len(4) + ptr(8)

    _fields_ = [("len", ctypes.c_uint32), ("ptr", ctypes.c_void_p)]


class _Control(ctypes.Structure):
    _fields_ = [
        ("channel", ctypes.c_ubyte),
        ("unused", ctypes.c_ubyte * 3),
        ("param", ctypes.c_uint32),
        ("value", ctypes.c_int32),
    ]


class _QueueControl(ctypes.Structure):
    _layout_ = "ms"
    _pack_ = 1

    _fields_ = [
        ("queue", ctypes.c_ubyte),
        ("unused", ctypes.c_ubyte * 3),
        ("param", ctypes.c_uint64),
    ]


class _EventData(ctypes.Union):
    _fields_ = [
        ("control", _Control),
        ("raw8", ctypes.c_ubyte * 12),
        ("raw32", ctypes.c_uint32 * 3),
        ("ext", _Ext),
        ("queue", _QueueControl),
        ("time", _Timestamp),
        ("addr", _Addr),
        ("connect", _Addr * 2),
        ("result", ctypes.c_int32 * 2),
    ]


class _Event(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_ubyte),
        ("flags", ctypes.c_ubyte),
        ("tag", ctypes.c_ubyte),
        ("queue", ctypes.c_ubyte),
        ("time", _Timestamp),
        ("source", _Addr),
        ("dest", _Addr),
        ("data", _EventData),
    ]


_SIZEOF_EVENT = 28
assert ctypes.sizeof(_Event) == _SIZEOF_EVENT


class _Pollfd(ctypes.Structure):
    _fields_ = [("fd", ctypes.c_int), ("events", ctypes.c_short), ("revents", ctypes.c_short)]


def _load_libasound():
    candidates = ["libasound.so.2"]
    found = ctypes.util.find_library("asound")
    if found:
        candidates.insert(0, found)
    for name in candidates:
        try:
            lib = ctypes.CDLL(name)
        except OSError:
            continue
        _bind_symbols(lib)
        return lib
    raise TransportError("libasound (ALSA) not found on this system")


def _bind_symbols(lib: ctypes.CDLL) -> None:
    lib.snd_seq_open.argtypes = [ctypes.POINTER(ctypes.c_void_p), ctypes.c_char_p, ctypes.c_int, ctypes.c_int]
    lib.snd_seq_close.argtypes = [ctypes.c_void_p]
    lib.snd_seq_client_id.argtypes = [ctypes.c_void_p]
    lib.snd_seq_set_client_name.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
    lib.snd_seq_create_simple_port.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_uint, ctypes.c_uint]
    lib.snd_seq_nonblock.argtypes = [ctypes.c_void_p, ctypes.c_int]
    lib.snd_seq_event_output.argtypes = [ctypes.c_void_p, ctypes.POINTER(_Event)]
    lib.snd_seq_drain_output.argtypes = [ctypes.c_void_p]
    lib.snd_seq_event_input.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)]
    lib.snd_seq_event_input_pending.argtypes = [ctypes.c_void_p, ctypes.c_int]
    lib.snd_seq_free_event.argtypes = [ctypes.c_void_p]
    lib.snd_seq_poll_descriptors_count.argtypes = [ctypes.c_void_p, ctypes.c_short]
    lib.snd_seq_poll_descriptors.argtypes = [ctypes.c_void_p, ctypes.POINTER(_Pollfd), ctypes.c_uint, ctypes.c_short]

    lib.snd_seq_client_info_malloc.argtypes = [ctypes.POINTER(ctypes.c_void_p)]
    lib.snd_seq_client_info_malloc.restype = ctypes.c_int
    lib.snd_seq_client_info_free.argtypes = [ctypes.c_void_p]
    lib.snd_seq_client_info_set_client.argtypes = [ctypes.c_void_p, ctypes.c_int]
    lib.snd_seq_client_info_get_client.argtypes = [ctypes.c_void_p]
    lib.snd_seq_client_info_get_client.restype = ctypes.c_int
    lib.snd_seq_client_info_get_name.argtypes = [ctypes.c_void_p]
    lib.snd_seq_client_info_get_name.restype = ctypes.c_char_p
    lib.snd_seq_query_next_client.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    lib.snd_seq_query_next_client.restype = ctypes.c_int

    lib.snd_seq_port_info_malloc.argtypes = [ctypes.POINTER(ctypes.c_void_p)]
    lib.snd_seq_port_info_malloc.restype = ctypes.c_int
    lib.snd_seq_port_info_free.argtypes = [ctypes.c_void_p]
    lib.snd_seq_port_info_set_client.argtypes = [ctypes.c_void_p, ctypes.c_int]
    lib.snd_seq_port_info_set_port.argtypes = [ctypes.c_void_p, ctypes.c_int]
    lib.snd_seq_port_info_get_port.argtypes = [ctypes.c_void_p]
    lib.snd_seq_port_info_get_port.restype = ctypes.c_int
    lib.snd_seq_port_info_get_name.argtypes = [ctypes.c_void_p]
    lib.snd_seq_port_info_get_name.restype = ctypes.c_char_p
    lib.snd_seq_port_info_get_capability.argtypes = [ctypes.c_void_p]
    lib.snd_seq_port_info_get_capability.restype = ctypes.c_uint
    lib.snd_seq_port_info_get_type.argtypes = [ctypes.c_void_p]
    lib.snd_seq_port_info_get_type.restype = ctypes.c_uint
    lib.snd_seq_query_next_port.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    lib.snd_seq_query_next_port.restype = ctypes.c_int

    lib.snd_seq_port_subscribe_malloc.argtypes = [ctypes.POINTER(ctypes.c_void_p)]
    lib.snd_seq_port_subscribe_malloc.restype = ctypes.c_int
    lib.snd_seq_port_subscribe_free.argtypes = [ctypes.c_void_p]
    lib.snd_seq_port_subscribe_set_sender.argtypes = [ctypes.c_void_p, ctypes.POINTER(_Addr)]
    lib.snd_seq_port_subscribe_set_dest.argtypes = [ctypes.c_void_p, ctypes.POINTER(_Addr)]
    lib.snd_seq_subscribe_port.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    lib.snd_seq_subscribe_port.restype = ctypes.c_int
    lib.snd_seq_unsubscribe_port.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    lib.snd_seq_unsubscribe_port.restype = ctypes.c_int


@dataclass(frozen=True)
class DeviceInfo:
    client: int
    port: int
    name: str
    client_name: str


KNOWN_NAME_FRAGMENTS = (
    "pocket master",
    "sonicake",
    "sonic master",
    "sonicmaster",
    "qme",
    "qap",
    "qam",
    "qbs",
)


def _matches_known_device(name: str) -> bool:
    lowered = name.lower()
    return any(fragment in lowered for fragment in KNOWN_NAME_FRAGMENTS)


def list_devices() -> list[DeviceInfo]:
    """List MIDI-ish sequencer ports on this system."""
    lib = _load_libasound()
    handle = ctypes.c_void_p()
    if lib.snd_seq_open(ctypes.byref(handle), b"default", SND_SEQ_OPEN_DUPLEX, 0) < 0:
        raise TransportError("could not open ALSA sequencer (default)")
    try:
        own_id = lib.snd_seq_client_id(handle)
        devices: list[DeviceInfo] = []
        cinfo_ptr = ctypes.c_void_p()
        if lib.snd_seq_client_info_malloc(ctypes.byref(cinfo_ptr)) < 0:
            raise TransportError("out of memory")
        try:
            lib.snd_seq_client_info_set_client(cinfo_ptr, -1)
            while lib.snd_seq_query_next_client(handle, cinfo_ptr) == 0:
                client = lib.snd_seq_client_info_get_client(cinfo_ptr)
                if client == own_id:
                    continue
                raw_name = lib.snd_seq_client_info_get_name(cinfo_ptr) or b""
                client_name = raw_name.decode("utf-8", "replace")

                pinfo_ptr = ctypes.c_void_p()
                if lib.snd_seq_port_info_malloc(ctypes.byref(pinfo_ptr)) < 0:
                    continue
                try:
                    lib.snd_seq_port_info_set_client(pinfo_ptr, client)
                    lib.snd_seq_port_info_set_port(pinfo_ptr, -1)
                    while lib.snd_seq_query_next_port(handle, pinfo_ptr) == 0:
                        port = lib.snd_seq_port_info_get_port(pinfo_ptr)
                        raw = lib.snd_seq_port_info_get_name(pinfo_ptr) or b""
                        name = raw.decode("utf-8", "replace")
                        devices.append(DeviceInfo(client=client, port=port, name=name, client_name=client_name))
                finally:
                    lib.snd_seq_port_info_free(pinfo_ptr)
        finally:
            lib.snd_seq_client_info_free(cinfo_ptr)
        return devices
    finally:
        lib.snd_seq_close(handle)


def find_devices() -> list[DeviceInfo]:
    """Return ports likely to belong to a Sonicake processor."""
    return [d for d in list_devices() if _matches_known_device(d.name) or _matches_known_device(d.client_name)]


class AlsaSequencerTransport:
    """Bidirectional SysEx transport to a sequencer port.

    Parameters
    ----------
    device:
        A ``DeviceInfo`` or a ``(client, port)`` tuple.  If ``None`` the
        first Sonicake-looking port is used; the
        ``SONICAKE_MIDI_ADDRESS`` environment variable (``client:port``)
        takes precedence.
    client_name:
        Name reported to the ALSA sequencer.
    """

    def __init__(self, device=None, client_name: str = "sonicake-manager") -> None:
        env = os.environ.get("SONICAKE_MIDI_ADDRESS")
        if device is None and env:
            try:
                client, port = (int(part) for part in env.split(":", 1))
            except ValueError as exc:
                raise TransportError(f"invalid SONICAKE_MIDI_ADDRESS: {env!r} (expected 'client:port')") from exc
            device = DeviceInfo(client=client, port=port, name="(from environment)", client_name="(from environment)")
        if device is None:
            matches = find_devices()
            if not matches:
                raise TransportError("no Sonicake sequencer port found; set SONICAKE_MIDI_ADDRESS=client:port")
            device = matches[0]
        if isinstance(device, tuple):
            device = DeviceInfo(client=device[0], port=device[1], name=f"{device[0]}:{device[1]}", client_name="")

        self.device = device
        self._lib = _load_libasound()
        self._handle = ctypes.c_void_p()
        if self._lib.snd_seq_open(ctypes.byref(self._handle), b"default", SND_SEQ_OPEN_DUPLEX, 0) < 0:
            raise TransportError("could not open ALSA sequencer (default)")
        self._lib.snd_seq_set_client_name(self._handle, client_name.encode("utf-8"))
        self._lib.snd_seq_nonblock(self._handle, SND_SEQ_NONBLOCK)
        self._port = self._lib.snd_seq_create_simple_port(
            self._handle,
            b"io",
            SND_SEQ_PORT_CAP_READ | SND_SEQ_PORT_CAP_WRITE | SND_SEQ_PORT_CAP_SUBS_READ | SND_SEQ_PORT_CAP_SUBS_WRITE,
            SND_SEQ_PORT_TYPE_MIDI_GENERIC | SND_SEQ_PORT_TYPE_APPLICATION,
        )
        if self._port < 0:
            self.close()
            raise TransportError("could not create sequencer port")
        self.client_id = self._lib.snd_seq_client_id(self._handle)
        self._subscribe_in()
        self._subscribe_out()

    # -- subscriptions ---------------------------------------------------------

    def _subscription(self, sender: tuple[int, int], dest: tuple[int, int]) -> ctypes.c_void_p:
        sub_ptr = ctypes.c_void_p()
        if self._lib.snd_seq_port_subscribe_malloc(ctypes.byref(sub_ptr)) < 0:
            raise TransportError("out of memory")
        sender_addr = _Addr(sender[0], sender[1])
        dest_addr = _Addr(dest[0], dest[1])
        self._lib.snd_seq_port_subscribe_set_sender(sub_ptr, ctypes.byref(sender_addr))
        self._lib.snd_seq_port_subscribe_set_dest(sub_ptr, ctypes.byref(dest_addr))
        return sub_ptr

    def _subscribe_in(self) -> None:
        sub = self._subscription((self.device.client, self.device.port), (self.client_id, self._port))
        try:
            if self._lib.snd_seq_subscribe_port(self._handle, sub) < 0:
                raise TransportError(f"could not subscribe to input port {self.device.client}:{self.device.port}")
        finally:
            self._lib.snd_seq_port_subscribe_free(sub)

    def _subscribe_out(self) -> None:
        sub = self._subscription((self.client_id, self._port), (self.device.client, self.device.port))
        try:
            rc = self._lib.snd_seq_subscribe_port(self._handle, sub)
            # The output subscription activates the device; failure is fatal.
            if rc < 0:
                raise TransportError(f"could not subscribe to output port {self.device.client}:{self.device.port}")
        finally:
            self._lib.snd_seq_port_subscribe_free(sub)

    # -- I/O ------------------------------------------------------------------

    def send(self, frame: bytes) -> None:
        """Send one SysEx frame.

        The documented Sonicake frames start with the ``8080`` prefix; it is
        passed through verbatim inside the sequencer's SysEx event, exactly
        as the reference tooling does.
        """
        if not frame.endswith(b"\xF7"):
            raise ValueError("frame must end with F7")
        buffer = (ctypes.c_ubyte * len(frame)).from_buffer_copy(frame)
        ev = _Event()
        ev.type = SND_SEQ_EVENT_SYSEX
        ev.flags = SND_SEQ_EVENT_LENGTH_VARIABLE
        ev.queue = SND_SEQ_QUEUE_DIRECT
        ev.source.client = self.client_id
        ev.source.port = self._port
        ev.dest.client = self.device.client
        ev.dest.port = self.device.port
        ev.data.ext.len = len(frame)
        ev.data.ext.ptr = ctypes.addressof(buffer)
        if self._lib.snd_seq_event_output(self._handle, ctypes.byref(ev)) < 0:
            raise TransportError("failed to queue SysEx output")
        if self._lib.snd_seq_drain_output(self._handle) < 0:
            raise TransportError("failed to drain SysEx output")

    def send_frames(self, frames: list[bytes], delay: float = 0.015) -> None:
        for frame in frames:
            self.send(frame)
            time.sleep(delay)

    def _poll_event(self, timeout: float) -> bool:
        pfds = _Pollfd(0, 0, 0)
        count = self._lib.snd_seq_poll_descriptors_count(self._handle, POLLIN)
        if count != 1:
            return False
        self._lib.snd_seq_poll_descriptors(self._handle, ctypes.byref(pfds), 1, POLLIN)
        poller = select.poll()
        poller.register(pfds.fd, select.POLLIN)
        return bool(poller.poll(int(timeout * 1000)))

    def _read_pending(self) -> list[bytes]:
        messages: list[bytes] = []
        while True:
            pending = self._lib.snd_seq_event_input_pending(self._handle, 1)
            if pending <= 0:
                break
            ev_ptr = ctypes.c_void_p()
            count = self._lib.snd_seq_event_input(self._handle, ctypes.byref(ev_ptr))
            if count < 0 or not ev_ptr:
                continue
            try:
                ev = ctypes.cast(ev_ptr, ctypes.POINTER(_Event)).contents
                if ev.type == SND_SEQ_EVENT_SYSEX:
                    payload_ptr = ev.data.ext.ptr
                    length = ev.data.ext.len
                    data = ctypes.string_at(payload_ptr, length)
                    messages.append(data)
            finally:
                self._lib.snd_seq_free_event(ev_ptr)
        return messages

    def recv(self, timeout: float = 2.0, idle_timeout: float = 0.25) -> list[bytes]:
        """Collect SysEx messages.

        Reads until ``idle_timeout`` passes without new data or the
        absolute ``timeout`` is reached.
        """
        messages: list[bytes] = []
        deadline = time.monotonic() + timeout
        idle_deadline = time.monotonic() + idle_timeout
        while True:
            remaining = min(deadline, idle_deadline) - time.monotonic()
            if remaining <= 0:
                break
            if not self._poll_event(remaining):
                break
            messages.extend(self._read_pending())
            idle_deadline = time.monotonic() + idle_timeout
        return messages

    def request(self, frame: bytes, timeout: float = 2.0, idle_timeout: float = 0.25) -> list[bytes]:
        self.send(frame)
        return self.recv(timeout=timeout, idle_timeout=idle_timeout)

    def close(self) -> None:
        handle = getattr(self, "_handle", None)
        if handle:
            self._lib.snd_seq_close(handle)
            self._handle = None

    def __enter__(self) -> "AlsaSequencerTransport":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def __del__(self) -> None:  # pragma: no cover - safety net
        try:
            self.close()
        except Exception:
            pass
