"""Tests for the preset-modified notification query."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sonicake_manager.device import SonicakeDevice
from sonicake_manager.transport import FakeTransport

MODIFIED = bytes.fromhex("8080F0070A000100000003010204050001F7")
SAVED = bytes.fromhex("8080F0070D000100000003010204050000F7")


def test_preset_modified_true():
    device = SonicakeDevice(FakeTransport([MODIFIED]))
    assert device.preset_modified() is True


def test_preset_modified_false():
    device = SonicakeDevice(FakeTransport([SAVED]))
    assert device.preset_modified() is False
