"""Whole-bank backup (export only).

This is intentionally backup-only. Restoring 100 slots means repeatedly
overwriting user presets, so it must be designed and validated separately.

A full backup works by selecting each preset once and reading the edit-buffer
state dump. Selection is a device write, though a benign one; callers must
require an explicit confirmation. The original slot is re-selected at the end.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Callable, Iterable

from . import __version__
from .preset_file import build_export, preset_index_from_raw, slot_label

FORMAT = "sonicake-manager-backup"
VERSION = 1
USER_RANGE = range(0, 50)
FACTORY_RANGE = range(50, 100)
ALL_RANGE = range(0, 100)


class BackupError(RuntimeError):
    pass


def _slot_index_from_number(number: int, factory: bool) -> int:
    return number - 1 if not factory else 50 + number - 1


def _iter_slots(bank: str) -> Iterable[tuple[int, bool]]:
    if bank == "user":
        for number in range(1, 51):
            yield _slot_index_from_number(number, factory=False), False
    elif bank == "factory":
        for number in range(1, 51):
            yield _slot_index_from_number(number, factory=True), True
    elif bank == "all":
        yield from _iter_slots("user")
        yield from _iter_slots("factory")
    else:
        raise BackupError(f"unknown bank {bank!r} (expected user, factory or all)")


def build_backup(
    device,
    *,
    bank: str = "all",
    progress: Callable[[int, int, str], None] | None = None,
) -> dict[str, Any]:
    slots = list(_iter_slots(bank))
    original_index = preset_index_from_raw(device.preset_number_raw())
    try:
        names = device.preset_names()
    except Exception:
        names = [""] * 100

    snapshots: list[dict[str, Any]] = []
    for position, (index, factory) in enumerate(slots, start=1):
        number = index + 1 if not factory else index - 50 + 1
        if progress:
            progress(position, len(slots), slot_label(index) or str(index))
        ack = device.select_preset(number, factory=factory)
        if ack not in ("ack", "preset-saved", "preset-modified"):
            raise BackupError(f"selecting {slot_label(index)} returned {ack}")
        state = device.state()
        name = names[index] if 0 <= index < len(names) else None
        snapshots.append(build_export(state, slot_index=index, name=name))

    if original_index is not None:
        try:
            device.select_preset(original_index + 1 if original_index < 50 else original_index - 50 + 1,
                                 factory=original_index >= 50)
        except Exception:
            # Backup data is already collected; don't mask that with restore noise.
            pass

    return {
        "format": FORMAT,
        "version": VERSION,
        "app": {"name": "sonicake-manager", "version": __version__},
        "createdAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "bank": bank,
        "slots": snapshots,
    }


def dumps_backup(data: dict[str, Any]) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def loads_backup(text: str) -> dict[str, Any]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise BackupError(f"not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise BackupError("expected a JSON object")
    if data.get("format") != FORMAT:
        raise BackupError(f"unsupported format {data.get('format')!r}")
    if data.get("version") != VERSION:
        raise BackupError(f"unsupported version {data.get('version')!r}")
    if not isinstance(data.get("slots"), list):
        raise BackupError("missing 'slots' list")
    return data
