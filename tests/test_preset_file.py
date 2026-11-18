"""Tests for current-preset JSON export/import."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest

from sonicake_manager.device import SonicakeDevice
from sonicake_manager.preset_file import (
    PresetFileError,
    apply_export,
    build_export,
    dumps_export,
    loads_export,
    preset_index_from_raw,
    slot_label,
)
from sonicake_manager.transport import FakeTransport

ACK = bytes.fromhex("8080F00B02000100000003010400080000F7")


def sample_state():
    return {
        "presetVolume": 72,
        "presetBpm": 100,
        "cloneMode": True,
        "moduleStates": {"NR": True, "DRV": False, "AMP": True},
        "selectedEffects": {"DRV": "Scream", "AMP": "Flyman B1+"},
        "parameters": {"DRV": {"Gain": 18, "Tone": 58}, "AMP": {"Bass": 46}},
        "signalChain": ["NR", "FX1", "DRV", "AMP", "IR", "EQ", "FX2", "DLY", "RVB"],
        "footswitchFS1": ["DRV"],
        "footswitchFS2": ["DLY"],
    }


def test_export_roundtrip():
    data = build_export(sample_state(), slot_index=4, name="P05 TONE")
    loaded = loads_export(dumps_export(data))
    assert loaded["version"] == 1
    assert loaded["slot"]["label"] == "P05"
    assert loaded["state"]["parameters"]["DRV"]["Gain"] == 18


def test_loads_export_rejects_bad_files():
    with pytest.raises(PresetFileError):
        loads_export("not json")
    with pytest.raises(PresetFileError):
        loads_export('{"format": "other", "version": 1, "state": {}}')
    with pytest.raises(PresetFileError):
        loads_export('{"format": "sonicake-manager-preset", "version": 99, "state": {}}')


def test_slot_label_and_raw_index():
    assert slot_label(0) == "P01"
    assert slot_label(49) == "P50"
    assert slot_label(50) == "F01"
    assert slot_label(99) == "F50"
    assert preset_index_from_raw(bytes([61, 0])) == 61


def test_apply_export_replays_known_fields():
    data = loads_export(dumps_export(build_export(sample_state(), slot_index=None, name=None)))
    # amp mode + 2 effects + 3 params + 3 module states + chain + volume = 11 writes
    transport = FakeTransport([ACK] * 20)
    report = apply_export(SonicakeDevice(transport), data)
    assert len(transport.sent) == 11
    assert report["applied"]
    assert any(item.startswith("DRV effect -> Scream") for item in report["applied"])
    assert any(item.startswith("preset volume -> 72") for item in report["applied"])
    assert any("BPM" in item for item in report["skipped"])
    assert any("footswitch" in item for item in report["skipped"])


def test_apply_export_skips_unknown_effect():
    state = sample_state()
    state["selectedEffects"] = {"DRV": "Not A Real Effect"}
    state["parameters"] = {"DRV": {"Gain": 18}}
    data = build_export(state, slot_index=None, name=None)
    transport = FakeTransport([ACK] * 20)
    report = apply_export(SonicakeDevice(transport), data)
    assert any("unknown effect" in item for item in report["skipped"])
