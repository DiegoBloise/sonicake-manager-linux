# Contributing

Thanks for helping make Sonicake Manager for Linux better.

## Development setup

```bash
python3 -m venv .venv
.venv/bin/pip install -e . pytest
.venv/bin/python -m pytest tests/
```

The test suite does not need a guitar processor; transport tests use a fake device.

## Coding style

- Python ≥ 3.11, standard library first.
- PySide6 for the GUI; no compiled dependencies. The transport talks to ALSA through `ctypes` and `libasound`.
- Keep protocol code byte-accurate and covered by tests.
- User-visible strings go through `sonicake_manager.i18n` (`en` and `pt`).

## Commits

Use small, logically grouped commits with Conventional Commit prefixes:

- `feat:` new functionality
- `fix:` bug fixes
- `refact:` refactoring without behavior changes
- `update:` documentation, tests or metadata updates
- `chore:` maintenance

## Scope

This project implements support from documented protocol knowledge and community notes. Please do not include code, assets or extracted material from proprietary binaries.
