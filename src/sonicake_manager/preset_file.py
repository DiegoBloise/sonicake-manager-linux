"""JSON export/import of the current edit buffer.

Export is read-only and captures the decoded live state.  Import replays
selected parts of that state with the same write commands used by the GUI;
it does **not** save to a user slot unless the caller asks for that
afterwards.  Footswitch assignments and BPM are intentionally not restored:
BPM is not persisted by the device, and footswitch assignment frames are not
validated against hardware yet.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from . import __version__
from .data import command_library, effect_library
from .decode import MODULE_IDS

FORMAT = "sonicake-manager-preset"
VERSION = 1
MODULE_ORDER = ["NR", "FX1", "DRV", "AMP", "IR", "EQ", "FX2", "DLY", "RVB"]


class PresetFileError(ValueError):
    """Raised when an export file is malformed or unsupported."""


def slot_label(index: int | None) -> str | None:
    if index is None:
        return None
    if 0 <= index <= 49:
        return f"P{index + 1:02d}"
    if 50 <= index <= 99:
        return f"F{index - 49:02d}"
    return None


def preset_index_from_raw(raw: bytes) -> int | None:
    if raw and len(raw) >= 2:
        return raw[0] | (raw[1] << 8)
    return None


def build_export(state: dict[str, Any], *, slot_index: int | None, name: str | None) -> dict[str, Any]:
    return {
        "format": FORMAT,
        "version": VERSION,
        "app": {"name": "sonicake-manager", "version": __version__},
        "exportedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "slot": (
            {"index": slot_index, "label": slot_label(slot_index), "name": name or ""}
            if slot_index is not None
            else None
        ),
        "state": state,
    }


def dumps_export(data: dict[str, Any]) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False, sort_keys=False) + "\n"


def loads_export(text: str) -> dict[str, Any]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise PresetFileError(f"not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise PresetFileError("expected a JSON object")
    if data.get("format") != FORMAT:
        raise PresetFileError(f"unsupported format {data.get('format')!r}")
    if data.get("version") != VERSION:
        raise PresetFileError(f"unsupported version {data.get('version')!r}")
    state = data.get("state")
    if not isinstance(state, dict):
        raise PresetFileError("missing 'state' object")
    # Validate the fields we know how to replay, without requiring all of them.
    for key in ("moduleStates", "selectedEffects", "parameters"):
        value = state.get(key)
        if value is not None and not isinstance(value, dict):
            raise PresetFileError(f"state.{key} must be an object")
    if state.get("signalChain") is not None and not isinstance(state["signalChain"], list):
        raise PresetFileError("state.signalChain must be a list")
    return data


def _effect_id_for_name(module: str, name: str) -> int | None:
    mid = MODULE_IDS.get(module)
    table = (command_library().get("effectTypes") or {}).get(str(mid)) if mid is not None else None
    if not table:
        return None
    lib = effect_library()
    wanted = name.strip().casefold()
    for effect_id in table:
        spec = lib.get(str(effect_id))
        if spec and str(spec.get("name", "")).strip().casefold() == wanted:
            return int(effect_id)
    return None


def _alg_id_for_param(effect_id: int, param_name: str) -> int | None:
    wanted = param_name.strip().casefold()
    for descriptor in effect_library().get(str(effect_id), {}).get("alg", []):
        if str(descriptor.get("name", "")).strip().casefold() == wanted:
            return int(descriptor["algId"])
    return None


def _boolish(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "on")
    return False


def apply_export(device, data: dict[str, Any]) -> dict[str, list[str]]:
    """Replay an export into the edit buffer. Returns a per-action report."""
    state = data.get("state", {})
    if not isinstance(state, dict):
        raise PresetFileError("missing 'state' object")

    report: dict[str, list[str]] = {"applied": [], "skipped": []}

    def note(kind: str, detail: str) -> None:
        report[kind].append(detail)

    # 1) Amp mode first; it does not carry parameter data but can change voicing.
    if "cloneMode" in state:
        status = device.set_amp_mode(_boolish(state["cloneMode"]))
        note("applied", f"amp mode -> {'clone' if _boolish(state['cloneMode']) else 'normal'} ({status})")

    # 2) Effect types before parameters: switching effects resets parameter data.
    selected: dict[str, int] = {}
    effects = state.get("selectedEffects") or {}
    for module in MODULE_ORDER:
        name = effects.get(module)
        if not name:
            continue
        if module == "NR":
            note("skipped", "NR is fixed to Gate on this device")
            continue
        effect_id = _effect_id_for_name(module, str(name))
        if effect_id is None:
            note("skipped", f"{module}: unknown effect {name!r}")
            continue
        selected[module] = effect_id
        status = device.set_effect_type(module, effect_id)
        note("applied", f"{module} effect -> {name} ({status})")

    # 3) Parameters, using the exported effect selection as the algId source.
    parameters = state.get("parameters") or {}
    for module, values in parameters.items():
        if module not in MODULE_IDS or not isinstance(values, dict):
            note("skipped", f"parameters.{module}: malformed entry")
            continue
        effect_id = selected.get(module)
        if effect_id is None and module in effects:
            effect_id = _effect_id_for_name(module, str(effects[module]))
        if effect_id is None:
            note("skipped", f"{module}: cannot map parameters without a known effect")
            continue
        for param_name, value in values.items():
            alg_id = _alg_id_for_param(effect_id, str(param_name))
            if alg_id is None:
                note("skipped", f"{module}.{param_name}: unknown parameter for this effect")
                continue
            status = device.set_parameter(module, alg_id, value)
            note("applied", f"{module}.{param_name} -> {value} ({status})")

    # 4) Module on/off.
    module_states = state.get("moduleStates") or {}
    for module in MODULE_ORDER:
        if module in module_states:
            status = device.set_module_state(module, _boolish(module_states[module]))
            note("applied", f"{module} -> {'on' if _boolish(module_states[module]) else 'off'} ({status})")

    # 5) Chain order and preset volume last.
    chain = state.get("signalChain")
    if isinstance(chain, list) and chain:
        order = [str(part).strip().upper() for part in chain if str(part).strip()]
        status = device.set_chain(order)
        note("applied", f"chain -> {'-'.join(order)} ({status})")

    if state.get("presetVolume") is not None:
        try:
            volume = int(float(state["presetVolume"]))
        except (TypeError, ValueError):
            note("skipped", f"presetVolume: cannot parse {state['presetVolume']!r}")
        else:
            status = device.set_preset_volume(volume)
            note("applied", f"preset volume -> {volume} ({status})")

    if state.get("presetBpm") is not None:
        note("skipped", "BPM is not persisted by the device; not replayed")
    if state.get("footswitchFS1") is not None or state.get("footswitchFS2") is not None:
        note("skipped", "footswitch assignments are exported but not replayed yet")

    return report
