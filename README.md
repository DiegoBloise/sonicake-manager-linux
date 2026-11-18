# Sonicake Manager for Linux

Open-source desktop manager for [Sonicake](https://www.sonicake.com/) guitar processors — edit presets, chain modules, manage IRs and clone profiles, browse factory banks, back up and restore data, and talk to your hardware directly over USB-MIDI or Bluetooth LE.

This project targets Linux-first and ships a clean, documented protocol implementation built from hands-on hardware observation and community knowledge.

## Features

- Connect to Pocket Master and Q-series processors over USB-MIDI and BLE-MIDI
- Read and write the editor buffer, persist presets to any of the 50 user slots
- Visual signal-chain editor with per-module parameter control
- IR upload and clone (NAM) profile management
- Preset backup/restore, import/export (`.json`), rename, reset
- Global settings: footswitches, backlight, ECO mode, reamp
- Pure-Python protocol layer — usable as a library or from the CLI/GUI

## Supported devices

See [docs/devices.md](docs/devices.md).

## Requirements

- Linux with ALSA
- Python 3.11+

## Status

Early development. See [docs/protocol.md](docs/protocol.md) and the roadmap.
