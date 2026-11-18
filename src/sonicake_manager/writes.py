"""Write-command frame builders.

Frames come from the packaged tables in ``command_library.json`` (the
documented command set).  Where the reference documents a dynamic
construction (volume out of table range, BPM), the frame is built
on the fly with :func:`build_frame`.

All frames put the edits into the device's edit buffer; persist a
preset with :func:`save_preset_frame`.
"""

from __future__ import annotations

from .decode import MODULE_IDS
from .data import command_library
from .names import encode_name
from .protocol import build_frame, nibble_collapse


def _table() -> dict:
    return command_library()


def _mid(module: str | int) -> int:
    if isinstance(module, str):
        key = module.upper()
        if key not in MODULE_IDS:
            raise KeyError(f"unknown module: {module!r}")
        return MODULE_IDS[key]
    return int(module)


def format_value_key(value) -> str:
    """int -> '5'; fractional -> one decimal ('0.3')."""
    d = float(value)
    r = round(d)
    if abs(d - r) < 1e-6:
        return str(int(r))
    s = f"{d:.1f}"
    return "0.0" if s == "-0.0" else s


def preset_volume_frame(value: int) -> bytes:
    """0402 field 01 (preset volume)."""
    value = int(value)
    if not 0 <= value <= 100:
        raise ValueError("preset volume must be 0..100")
    table = _table()["globalCommands"]["presetVolume"]
    key = str(value)
    if key in table:
        return bytes.fromhex(table[key])
    return build_frame(bytes([0x11, 0x42, 0x01, 0x20, 0x01, 0x00, value & 0xFF, 0]))


def preset_bpm_frame(value: int) -> bytes:
    """0402 field 02 (preset BPM).

    The device accepts this frame but does not persist the BPM value
    (documented firmware quirk).
    """
    value = int(value)
    if not 0 <= value <= 0xFFFF:
        raise ValueError("bpm must be 0..65535")
    return build_frame(bytes([0x11, 0x42, 0x02, 0x20, 0x01, 0x00, value & 0xFF, (value >> 8) & 0xFF]))


def module_state_frame(module: str | int, on: bool) -> bytes:
    mid = _mid(module)
    return bytes.fromhex(_table()["moduleStates"][str(mid)]["on" if on else "off"])


def amp_mode_frame(clone: bool) -> bytes:
    return bytes.fromhex(_table()["ampModes"]["clone" if clone else "factory"])


def effect_type_frame(module: str | int, effect_id: int) -> bytes:
    mid = _mid(module)
    table = _table()["effectTypes"]
    if str(mid) not in table:
        raise KeyError(f"module {mid} has no effect selection (NR is fixed: Gate)")
    key = str(int(effect_id))
    if key not in table[str(mid)]:
        raise KeyError(f"effect {effect_id} not found for module {mid}")
    return bytes.fromhex(table[str(mid)][key])


def parameter_frame(module: str | int, alg_id: int, value) -> bytes:
    mid = _mid(module)
    value_key = format_value_key(value)
    try:
        frame = _table()["parameters"][str(mid)][str(int(alg_id))][value_key]
    except KeyError as exc:
        raise KeyError(
            f"parameter not found: module {mid}, algId {alg_id}, value {value_key!r}"
        ) from exc
    return bytes.fromhex(frame)


def chain_frame(chain: list[str]) -> bytes:
    key = "-".join(chain)
    table = _table()["chainOrderCommands"]
    if key not in table:
        raise KeyError(
            f"invalid chain order: {key}\n"
            "Remember: DRV→AMP→IR→EQ must stay contiguous in that order."
        )
    return bytes.fromhex(table[key])


def preset_select_frame(number: int, factory: bool = False) -> bytes:
    prefix = "F" if factory else "P"
    key = f"{prefix}{int(number):02d}"
    table = _table()["presetCommands"]["factory" if factory else "user"]
    if key not in table:
        raise KeyError(f"unknown preset: {key}")
    return bytes.fromhex(table[key])


def footswitch_frame(module: str | int, fs2: bool, on: bool) -> bytes:
    """11 4D <switch> <module> <state> — assign/remove a module on FS1/FS2."""
    mid = _mid(module)
    return build_frame(bytes([0x11, 0x4D, 1 if fs2 else 0, mid, 1 if on else 0]))


def save_preset_frame(name: str, slot: int) -> bytes:
    """040A — persist the current edit buffer into user slot 1..50."""
    slot = int(slot)
    if not 1 <= slot <= 50:
        raise ValueError("slot must be 1..50")
    name_field = nibble_collapse(bytes.fromhex(encode_name(name)))
    payload = bytes([0x11, 0x4A, slot - 1]) + b"\x00\x00\x00" + name_field + b"\x00" * 3
    return build_frame(payload)


def global_command_frame(command: str, value) -> bytes:
    table = _table()["globalCommands"]
    if command not in table:
        raise KeyError(f"unknown global command: {command!r}")
    key = format_value_key(value)
    if key not in table[command]:
        raise KeyError(f"value {value!r} not available for global command {command!r}")
    return bytes.fromhex(table[command][key])
