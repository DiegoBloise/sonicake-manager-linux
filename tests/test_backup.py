"""Tests for whole-bank backup construction (stubbed device)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sonicake_manager.backup import BackupError, build_backup, dumps_backup, loads_backup
import pytest


class StubDevice:
    def __init__(self) -> None:
        self.current = 59  # F10
        self.selected = []
        self.names = [f"USER {i:02d}" for i in range(1, 51)] + [f"FACTORY {i:02d}" for i in range(1, 51)]

    def preset_number_raw(self) -> bytes:
        return bytes([self.current, 0])

    def preset_names(self):
        return self.names

    def select_preset(self, number: int, factory: bool = False) -> str:
        index = (number - 1) if not factory else 50 + number - 1
        self.current = index
        self.selected.append((number, factory))
        return "ack"

    def state(self) -> dict:
        return {"presetVolume": self.current, "selectedEffects": {}, "moduleStates": {}, "parameters": {}}


def test_build_backup_all_and_restore_original_slot():
    device = StubDevice()
    data = build_backup(device, bank="all")
    assert data["format"] == "sonicake-manager-backup"
    assert len(data["slots"]) == 100
    assert data["slots"][0]["slot"]["label"] == "P01"
    assert data["slots"][50]["slot"]["label"] == "F01"
    assert device.current == 59
    assert device.selected[-1] == (10, True)  # original slot F10 re-selected


def test_build_backup_user_only():
    device = StubDevice()
    data = build_backup(device, bank="user")
    assert len(data["slots"]) == 50
    assert all(slot["slot"]["index"] < 50 for slot in data["slots"])


def test_build_backup_rejects_unknown_bank():
    with pytest.raises(BackupError):
        build_backup(StubDevice(), bank="nope")


def test_backup_roundtrip():
    device = StubDevice()
    data = build_backup(device, bank="user")
    loaded = loads_backup(dumps_backup(data))
    assert len(loaded["slots"]) == 50
    assert loaded["slots"][0]["state"]["presetVolume"] == 0
