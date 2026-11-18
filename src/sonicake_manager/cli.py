"""Command-line interface for Sonicake processors.

Examples
--------

    sonicake-manager list
    sonicake-manager info
    sonicake-manager names
    sonicake-manager state --json
    sonicake-manager export preset.json
    sonicake-manager import-preset preset.json --yes
    sonicake-manager select P03
    sonicake-manager set DRV 0 40
    sonicake-manager save 1 --name "MY TONE"
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .device import SonicakeDevice, DeviceError
from .preset_file import apply_export, build_export, dumps_export, loads_export, preset_index_from_raw
from .transport import AlsaSequencerTransport, TransportError, find_devices, list_devices
from .validation import is_valid_name


def _eprint(*args: object) -> None:
    print(*args, file=sys.stderr)


def _print_json(data: object) -> None:
    print(json.dumps(data, indent=2, ensure_ascii=False, default=str))


def _resolve_device(arg_device: str | None):
    if arg_device:
        try:
            client, port = (int(part) for part in arg_device.split(":", 1))
        except ValueError:
            _eprint(f"error: --device must be 'client:port', got {arg_device!r}")
            sys.exit(2)
        from .transport import DeviceInfo
        return DeviceInfo(client=client, port=port, name=f"{client}:{port}", client_name="")
    matches = find_devices()
    if not matches:
        _eprint("error: no Sonicake sequencer port found; use --device client:port (see 'list')")
        sys.exit(2)
    return matches[0]


def _open(args) -> SonicakeDevice:
    device = _resolve_device(getattr(args, "device", None))
    return SonicakeDevice(AlsaSequencerTransport(device))


def _preset_label(index: int) -> str | None:
    if 0 <= index <= 49:
        return f"P{index + 1:02d}"
    if 50 <= index <= 99:
        return f"F{index - 49:02d}"
    return None


# -- commands -----------------------------------------------------------------


def cmd_list(args) -> int:
    ports = list_devices()
    known = {(d.client, d.port) for d in find_devices()}
    for d in ports:
        marker = "*" if (d.client, d.port) in known else " "
        print(f"{marker} {d.client}:{d.port}\t{d.name}\t({d.client_name})")
    if not any((d.client, d.port) in known for d in ports):
        print("\n(* = Sonicake device detected)")
    else:
        print("\n(* = Sonicake device; use --device client:port to select)")
    return 0


def cmd_info(args) -> int:
    with _open(args) as dev:
        raw = dev.preset_number_raw()
    payload = raw
    result = {"preset_number_raw": payload.hex()}
    if len(payload) >= 2:
        index = payload[0] | (payload[1] << 8)
        result["preset_index"] = index
        result["preset"] = _preset_label(index)
    if getattr(args, "json", False):
        _print_json(result)
    else:
        print(f"preset: {result.get('preset') or '?'} (index {result.get('preset_index')}, raw {result['preset_number_raw']})")
    return 0


def cmd_state(args) -> int:
    with _open(args) as dev:
        state = dev.state()
    _print_json(state)
    return 0


def cmd_names(args) -> int:
    with _open(args) as dev:
        names = dev.preset_names()
    for i, name in enumerate(names):
        label = f"U{i + 1:02d}" if i < 50 else f"F{i - 49:02d}"
        if name:
            print(f"{label}  {name}")
    return 0


def cmd_globals(args) -> int:
    with _open(args) as dev:
        data = dev.globals()
    _print_json(data)
    return 0


def cmd_ir_names(args) -> int:
    with _open(args) as dev:
        names = dev.ir_name_list()
    for index, name in enumerate(names, start=1):
        print(f"IR {index}  {name}")
    return 0


def cmd_clone_names(args) -> int:
    with _open(args) as dev:
        names = dev.clone_name_list()
    for index, name in enumerate(names, start=1):
        print(f"CLONE {index}  {name}")
    return 0


def cmd_export(args) -> int:
    with _open(args) as dev:
        state = dev.state()
        index = preset_index_from_raw(dev.preset_number_raw())
        name = args.name
        if name is None:
            try:
                names = dev.preset_names()
            except DeviceError:
                names = []
            if index is not None and 0 <= index < len(names):
                name = names[index]
    data = build_export(state, slot_index=index, name=name)
    text = dumps_export(data)
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
        slot = (data.get("slot") or {}).get("label") or "?"
        print(f"exported {slot} to {args.output}")
    else:
        print(text, end="")
    return 0


def cmd_import_preset(args) -> int:
    if not args.yes:
        _eprint("refusing to write to the device without --yes")
        return 2
    try:
        data = loads_export(Path(args.file).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        _eprint(f"error: {exc}")
        return 2
    with _open(args) as dev:
        report = apply_export(dev, data)
        for line in report["applied"]:
            print(f"ok: {line}")
        for line in report["skipped"]:
            print(f"skip: {line}")
        if any(line.rstrip(")").endswith(("nack", "timeout", "preset-modified")) for line in report["applied"]):
            print("warning: at least one device write was not ACKed")
            return 1
        if args.save_slot is not None:
            name = args.name or (data.get("slot") or {}).get("name") or "PRESET"
            name = name.upper()
            if not is_valid_name(name):
                _eprint(f"error: invalid preset name {name!r}")
                return 2
            ack = dev.save_preset(name, args.save_slot)
            print(f"save '{name}' to slot {args.save_slot}: {ack}")
            return 0 if ack == "ack" else 1
    return 0



def cmd_select(args) -> int:
    factory = args.name.upper().startswith("F")
    number = int(args.name[1:])
    with _open(args) as dev:
        ack = dev.select_preset(number, factory=factory)
    print(f"select {args.name.upper()}: {ack}")
    return 0 if ack == "ack" else 1


def cmd_set_module(args) -> int:
    with _open(args) as dev:
        ack = dev.set_module_state(args.module, args.state.lower() in ("on", "1", "true"))
    print(f"module {args.module} {args.state}: {ack}")
    return 0 if ack == "ack" else 1


def cmd_set(args) -> int:
    with _open(args) as dev:
        ack = dev.set_parameter(args.module, int(args.alg_id), float(args.value))
    print(f"parameter {args.module} algId {args.alg_id} = {args.value}: {ack}")
    return 0 if ack == "ack" else 1


def cmd_effect(args) -> int:
    with _open(args) as dev:
        ack = dev.set_effect_type(args.module, int(args.effect_id))
    print(f"effect {args.module} -> {args.effect_id}: {ack}")
    return 0 if ack == "ack" else 1


def cmd_chain(args) -> int:
    chain = [part.strip().upper() for part in args.order.split("-") if part.strip()]
    with _open(args) as dev:
        ack = dev.set_chain(chain)
    print(f"chain {'-'.join(chain)}: {ack}")
    return 0 if ack == "ack" else 1


def cmd_volume(args) -> int:
    with _open(args) as dev:
        ack = dev.set_preset_volume(args.value)
    print(f"preset volume {args.value}: {ack}")
    return 0 if ack == "ack" else 1


def cmd_amp_mode(args) -> int:
    with _open(args) as dev:
        ack = dev.set_amp_mode(args.mode == "clone")
    print(f"amp mode {args.mode}: {ack}")
    return 0 if ack == "ack" else 1


def cmd_save(args) -> int:
    with _open(args) as dev:
        ack = dev.save_preset(args.name, args.slot)
    print(f"save '{args.name}' to slot {args.slot}: {ack}")
    return 0 if ack == "ack" else 1


def cmd_set_global(args) -> int:
    value: object = args.value
    try:
        number = float(value)
        value = int(number) if number.is_integer() else number
    except ValueError:
        pass
    with _open(args) as dev:
        ack = dev.set_global(args.command, value)
    print(f"global {args.command} = {value}: {ack}")
    return 0 if ack == "ack" else 1


# -- entry point ---------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sonicake-manager", description=__doc__)
    parser.add_argument("--device", help="MIDI port as 'client:port' (default: auto-detect, or SONICAKE_MIDI_ADDRESS)")
    parser.add_argument("--json", action="store_true", help="print raw JSON for dump commands")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="list sequencer ports (* = detected Sonicake)").set_defaults(func=cmd_list)
    sub.add_parser("info", help="current preset number").set_defaults(func=cmd_info)
    sub.add_parser("state", help="decoded current-preset state (JSON)").set_defaults(func=cmd_state)
    sub.add_parser("names", help="list the 100 preset names").set_defaults(func=cmd_names)
    sub.add_parser("globals", help="decoded global settings (JSON)").set_defaults(func=cmd_globals)
    sub.add_parser("ir-names", help="list the 5 user IR slot names").set_defaults(func=cmd_ir_names)
    sub.add_parser("clone-names", help="list the 5 user clone profile slot names").set_defaults(func=cmd_clone_names)

    p = sub.add_parser("export", help="export the current edit buffer as JSON (stdout if no file)")
    p.add_argument("output", nargs="?", help="output file; prints to stdout when omitted")
    p.add_argument("--name", help="name stored in the export (default: read from the device)")
    p.set_defaults(func=cmd_export)

    p = sub.add_parser("import-preset", help="replay an exported preset into the edit buffer (requires --yes)")
    p.add_argument("file")
    p.add_argument("--yes", action="store_true", help="confirm writes to the device")
    p.add_argument("--save-slot", type=int, help="after importing, save the buffer to user slot 1..50")
    p.add_argument("--name", help="name for --save-slot (default: name from the export)")
    p.set_defaults(func=cmd_import_preset)

    p = sub.add_parser("select", help="select a preset, e.g. P03 or F12")
    p.add_argument("name", help="preset slot, e.g. P03 (user) or F12 (factory)")
    p.set_defaults(func=cmd_select)

    p = sub.add_parser("set-module", help="turn a module on/off")
    p.add_argument("module", help="NR, FX1, DRV, AMP, IR, EQ, FX2, DLY, RVB")
    p.add_argument("state", help="on or off")
    p.set_defaults(func=cmd_set_module)

    p = sub.add_parser("set", help="set a parameter, e.g. 'set DRV 0 40'")
    p.add_argument("module")
    p.add_argument("alg_id", type=int)
    p.add_argument("value")
    p.set_defaults(func=cmd_set)

    p = sub.add_parser("effect", help="set the effect type of a module")
    p.add_argument("module")
    p.add_argument("effect_id", type=int)
    p.set_defaults(func=cmd_effect)

    p = sub.add_parser("chain", help="set the signal chain order")
    p.add_argument("order", help="hyphenated order, e.g. NR-FX1-FX2-DLY-RVB-DRV-AMP-IR-EQ")
    p.set_defaults(func=cmd_chain)

    p = sub.add_parser("volume", help="set preset volume 0..100")
    p.add_argument("value", type=int)
    p.set_defaults(func=cmd_volume)

    p = sub.add_parser("amp-mode", help="set amp mode")
    p.add_argument("mode", choices=["normal", "clone"])
    p.set_defaults(func=cmd_amp_mode)

    p = sub.add_parser("save", help="save the edit buffer into a user slot (1..50)")
    p.add_argument("slot", type=int)
    p.add_argument("--name", required=True, help="preset name (max 10 chars)")
    p.set_defaults(func=cmd_save)

    p = sub.add_parser("set-global", help="set a global command, e.g. 'set-global globalVolume 80'")
    p.add_argument("command")
    p.add_argument("value")
    p.set_defaults(func=cmd_set_global)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (TransportError, DeviceError, KeyError, ValueError) as exc:
        _eprint(f"error: {exc}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
