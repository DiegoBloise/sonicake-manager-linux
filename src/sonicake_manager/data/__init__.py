"""Access to the packaged device-data tables."""

from __future__ import annotations

import json
from functools import lru_cache
from importlib import resources
from pathlib import Path
from typing import Any

DATA_PACKAGE = "sonicake_manager.data"


@lru_cache(maxsize=None)
def _load(name: str) -> Any:
    path = resources.files(DATA_PACKAGE) / name
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def effect_library() -> dict:
    return _load("effect_library.json")


def effect_signatures() -> dict:
    return _load("effect_signatures.json")


def command_library() -> dict:
    return _load("command_library.json")


def character_map() -> dict:
    return _load("character_map.json")


def device_capabilities() -> dict:
    return _load("device_capabilities.json")


def algid_location_map() -> dict:
    return _load("algid_location_map.json")


def value_reverse_lookup() -> dict:
    return _load("value_reverse_lookup.json")


def modules() -> dict:
    return _load("modules.json")
