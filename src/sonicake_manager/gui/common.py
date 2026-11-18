"""Shared GUI helpers: busy cursor, module ordering, effect catalogs."""

from __future__ import annotations

import contextlib

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from ..data import command_library, effect_library
from ..decode import MODULE_IDS

MODULE_ORDER = ["NR", "FX1", "DRV", "AMP", "IR", "EQ", "FX2", "DLY", "RVB"]


@contextlib.contextmanager
def busy_cursor(status_text: str | None = None):
    """Show a wait cursor (and optional status text) while a call runs."""
    QApplication.setOverrideCursor(Qt.WaitCursor)
    try:
        yield
    finally:
        QApplication.restoreOverrideCursor()


def effect_catalog(module_name: str) -> list[tuple[int, str]]:
    """Effect ids + display names available for a module."""
    mid = MODULE_IDS[module_name]
    table = command_library().get("effectTypes", {}).get(str(mid))
    if not table:
        return []
    library = effect_library()
    out = []
    for key in table:
        spec = library.get(key)
        out.append((int(key), spec["name"] if spec else key))
    return out


def effect_params(effect_id: int) -> list[dict]:
    """Alg descriptors (name, algId, min, max, step…) for an effect id."""
    spec = effect_library().get(str(effect_id), {})
    return spec.get("alg", [])


def preset_label(index: int) -> str | None:
    """'P01'..'P50' for 0..49, 'F01'..'F50' for 50..99."""
    if 0 <= index <= 49:
        return f"P{index + 1:02d}"
    if 50 <= index <= 99:
        return f"F{index - 49:02d}"
    return None
