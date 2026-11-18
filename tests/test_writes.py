"""Tests for the write-command frame builders and device write API."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest

from sonicake_manager import writes
from sonicake_manager.data import command_library
from sonicake_manager.device import SonicakeDevice
from sonicake_manager.protocol import PacketReassembler, parse_frame
from sonicake_manager.transport import FakeTransport

ACK = bytes.fromhex("8080F00B02000100000003010400080000F7")
NACK = bytes.fromhex("8080F00B05000100000003010400080001F7")


def test_write_tables_all_parse():
    lib = command_library()
    count = 0
    for mid, onoff in lib["moduleStates"].items():
        for hexframe in onoff.values():
            parse_frame(bytes.fromhex(hexframe))
            count += 1
    for group in ("ampModes", "chainOrderCommands"):
        for hexframe in lib[group].values():
            parse_frame(bytes.fromhex(hexframe))
            count += 1
    for hexframe in (f for t in lib["effectTypes"].values() for f in t.values()):
        parse_frame(bytes.fromhex(hexframe))
        count += 1
    for t in lib["parameters"].values():
        for t2 in t.values():
            if t2:
                for hexframe in t2.values():
                    parse_frame(bytes.fromhex(hexframe))
                    count += 1
    for table in lib["globalCommands"].values():
        for hexframe in table.values():
            parse_frame(bytes.fromhex(hexframe))
            count += 1
    for bank in ("user", "factory"):
        for hexframe in lib["presetCommands"][bank].values():
            parse_frame(bytes.fromhex(hexframe))
            count += 1
    assert count > 6000


def test_save_preset_matches_documented_frame():
    frame = writes.save_preset_frame("TEST", 1)
    assert frame.hex() == (
        "8080f006090001000001030101040a0000000000000000"
        "0504040505030504"
        "000000000000000000000000"
        "000000000000"
        "f7"
    )


def test_save_preset_slot_bounds():
    with pytest.raises(ValueError):
        writes.save_preset_frame("X", 0)
    with pytest.raises(ValueError):
        writes.save_preset_frame("X", 51)


def test_format_value_key():
    assert writes.format_value_key(5) == "5"
    assert writes.format_value_key(5.0) == "5"
    assert writes.format_value_key(-3) == "-3"
    assert writes.format_value_key(0.25) == "0.2"  # rounds to one decimal
    assert writes.format_value_key(-0.04) == "0.0"


def test_parameter_frame_lookup():
    frame = writes.parameter_frame("DRV", 0, 40)
    parse_frame(frame)
    with pytest.raises(KeyError):
        writes.parameter_frame("DRV", 0, 12345)


def test_effect_type_frame_requires_supported_module():
    with pytest.raises(KeyError):
        writes.effect_type_frame("NR", 1)


def test_device_set_parameter_waits_for_ack():
    transport = FakeTransport(responses=[ACK])
    device = SonicakeDevice(transport)
    assert device.set_parameter("DRV", 0, 40) == "ack"
    assert len(transport.sent) == 1


def test_device_set_parameter_nack():
    transport = FakeTransport(responses=[NACK])
    device = SonicakeDevice(transport)
    assert device.set_parameter("DRV", 0, 40) == "nack"


def test_device_save_preset_uses_save_frame():
    transport = FakeTransport(responses=[ACK])
    device = SonicakeDevice(transport)
    assert device.save_preset("TEST", 1) == "ack"
    assert transport.sent[0] == writes.save_preset_frame("TEST", 1)


def test_device_select_preset_factory():
    transport = FakeTransport(responses=[ACK])
    device = SonicakeDevice(transport)
    assert device.select_preset(3, factory=True) == "ack"
    assert transport.sent[0] == bytes.fromhex(
        command_library()["presetCommands"]["factory"]["F03"]
    )
