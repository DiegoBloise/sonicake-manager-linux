"""Decoders for device dumps.

The dumps use a fixed layout.  To stay compatible with the documented
offsets, decoders operate on the *expanded* hex representation
(two nibble bytes per logical byte, two hex chars per wire byte), with the
legacy 11-byte pseudo-frame prelude prepended::

    8080 F0 07 06 00 01 00 00 00 00

This prelude is not sent or received; it exists only so the documented
byte offsets line up.
"""

from __future__ import annotations

from .data import algid_location_map, effect_library, effect_signatures, value_reverse_lookup
from .names import decode_name

MODULE_IDS = {
    "NR": 0,
    "FX1": 1,
    "DRV": 2,
    "AMP": 3,
    "IR": 4,
    "EQ": 5,
    "FX2": 6,
    "DLY": 7,
    "RVB": 8,
    "CLONE": 9,
}
MODULE_NAMES = {v: k for k, v in MODULE_IDS.items()}

_FAKE_HDR = "8080F00706000100000000"


def expand_hex(payload: bytes) -> str:
    """Logical payload bytes -> expanded hex string (as on the wire)."""
    return "".join(f"0{b >> 4:X}0{b & 0x0F:X}" for b in payload)


def collapse_hex(hexstr: str) -> bytes:
    """Expanded hex string -> logical payload bytes."""
    if len(hexstr) % 4 != 0:
        raise ValueError("expanded hex must be a multiple of 4 chars")
    out = bytearray()
    for i in range(0, len(hexstr), 4):
        out.append((int(hexstr[i : i + 2], 16) << 4) | int(hexstr[i + 2 : i + 4], 16))
    return bytes(out)


def _bytes_of(hexstr: str) -> list[str]:
    return [hexstr[i : i + 2] for i in range(0, len(hexstr), 2)]


def decode_preset_names(payload: bytes) -> list[str]:
    """Decode the preset-names dump into 100 slot names (50 user + 50 factory)."""
    payload_hex = expand_hex(payload)
    names = []
    for i in range(100):
        start = (12 + 40 * i) * 2
        block = payload_hex[start : start + 40]
        names.append(decode_name(block) if len(block) == 40 else "")
    return names


def decode_state(payload: bytes) -> dict:
    """Decode the current-preset state dump."""
    payload_hex = expand_hex(payload)
    if len(payload_hex) < 1600:
        raise ValueError(f"dump too short: {len(payload_hex)} hex chars")

    dump = _FAKE_HDR + payload_hex + "F7"
    slices = [(22, 422), (422, 822), (822, 1222), (1222, 1622), (1622, len(dump) - 1)]
    packets = [_bytes_of(_FAKE_HDR + dump[a:b] + "F7") for a, b in slices if a < len(dump)]

    def u16_after(bytes_list: list[str], marker: str) -> int | None:
        s = "".join(bytes_list)
        mi = s.find(marker)
        if mi < 0 or mi % 2:
            return None
        b = (mi + len(marker)) // 2
        if b + 3 >= len(bytes_list):
            return None
        lo = (int(bytes_list[b], 16) << 4) | int(bytes_list[b + 1], 16)
        hi = (int(bytes_list[b + 2], 16) << 4) | int(bytes_list[b + 3], 16)
        return (hi << 8) | lo

    p0 = [f"{int(b, 16):02X}" for b in packets[0][5:-1]]
    p0_str = "".join(p0)

    volume = u16_after(p0, "01020000040000")
    bpm = u16_after(p0, "02020000040000")

    csi = p0_str.rfind("0A000000")
    if csi < 0:
        raise ValueError("dump has no chain marker (0A000000)")
    chain_byte = csi // 2
    global_byte = chain_byte - 10
    n1, n2 = chain_byte - 13, chain_byte - 12
    if global_byte < 0 or n1 < 0:
        raise ValueError("dump truncated before the chain section")

    gs = int(p0[global_byte], 16)
    is_clone = bool(gs & 2)
    rvb_on = bool(gs & 1)
    main_mask = int(p0[n1][1] + p0[n2][1], 16)

    states = {}
    for mid, name in MODULE_NAMES.items():
        if mid >= 9:
            continue
        states[name] = rvb_on if mid == 8 else bool(main_mask & (1 << mid))
    if is_clone:
        states["IR"] = True

    chain: list[int] = []
    for i in range(chain_byte + 4, len(p0) - 1):
        try:
            mid = int(p0[i], 16)
        except ValueError:
            break
        if mid in MODULE_NAMES and mid < 9 and p0[i + 1] == "00" and mid not in chain:
            chain.append(mid)
        if len(chain) == 9:
            break
    if 0 not in chain:
        chain.insert(0, 0)

    # Selected effects: signatures live in packet 1.
    signatures = effect_signatures()
    lib = effect_library()
    name_to_id = {v["name"]: int(k) for k, v in lib.items()}
    selected = {0: 1}  # NR is fixed to Gate
    if len(packets) > 1:
        p1 = [f"{int(b, 16):02X}" for b in packets[1]]
        for mid_s, spec in signatures.items():
            off, length = spec["offset"], spec["length"]
            sig = "".join(p1[off : off + length]).upper()
            name = spec["signatures"].get(sig)
            if name:
                selected[int(mid_s)] = name_to_id[name]

    # Parameters: algId -> (packet, offset) + reverse value table.
    locations = algid_location_map()
    reverse = value_reverse_lookup()
    params: dict[int, dict[str, object]] = {}
    for mid, fx_id in selected.items():
        values = {}
        for prm in lib[str(fx_id)]["alg"]:
            loc = locations.get(f"{mid}_{prm['algId']}")
            if not loc:
                continue
            pi, off = loc["p"], loc["o"]
            if pi < 0 or pi >= len(packets) or off < 0 or len(packets[pi]) < off + 6:
                continue
            block = "".join(f"{int(b, 16):02X}" for b in packets[pi][off : off + 6])
            value = reverse.get(block)
            if value is not None:
                values[prm["name"]] = value
        if values:
            params[mid] = values

    def mask_at(byte_offset: int) -> int:
        if (byte_offset + 4) * 2 > len(dump):
            return 0
        nb = lambda b: int(dump[b * 2 : b * 2 + 2], 16)
        low = (nb(byte_offset) << 4) | nb(byte_offset + 1)
        high = (nb(byte_offset + 2) << 4) | nb(byte_offset + 3)
        return low | (high << 8)

    def bits_to_modules(mask: int) -> list[str]:
        return [MODULE_NAMES[i] for i in range(9) if mask & (1 << i)]

    return {
        "presetVolume": volume,
        "presetBpm": bpm,
        "cloneMode": is_clone,
        "moduleStates": states,
        "signalChain": [MODULE_NAMES[m] for m in chain],
        "selectedEffects": {MODULE_NAMES[m]: lib[str(fx)]["name"] for m, fx in sorted(selected.items())},
        "parameters": {MODULE_NAMES[m]: v for m, v in sorted(params.items())},
        "footswitchFS1": bits_to_modules(mask_at(947)),
        "footswitchFS2": bits_to_modules(mask_at(955)),
    }


def decode_globals(payload: bytes) -> dict:
    """Decode the global-settings dump."""
    if not payload:
        raise ValueError("device did not return the globals dump (NACK?)")
    payload_hex = expand_hex(payload)
    ll = len(payload_hex) // 2
    p = "0001" + "0000" + f"0{ll >> 4:X}0{ll & 0xF:X}" + payload_hex
    if len(p) < 276:
        raise ValueError(f"globals dump too short: {len(p)}")

    def u(off: int) -> int:
        return int(p[off : off + 2], 16) * 16 + int(p[off + 2 : off + 4], 16)

    def db(off: int) -> int:
        b1 = int(p[off : off + 2], 16)
        b2 = int(p[off + 2 : off + 4], 16)
        if b1 == 0x0F:
            return b2 - 16
        if b1 == 0x0E:
            return b2 - 32
        return b1 * 16 + b2

    def u_at(off: int) -> int:
        return u(off) if off + 4 <= len(p) else 0

    return {
        "globalVolume": u(100),
        "inputLevel": db(172),
        "fxRecLevel": db(192),
        "monitorLevel": db(212),
        "btRecLevel": db(272),
        "backlight": u_at(152),
        "mode": u_at(252),
        "reamp": u_at(292),
        "eco": u_at(312),
        "expFsType": u_at(332),
    }


def is_ack(payload: bytes) -> bool:
    return payload == bytes([0x14, 0x08, 0x00])


def is_nack(payload: bytes) -> bool:
    return payload == bytes([0x14, 0x08, 0x01])


def is_preset_modified(payload: bytes) -> bool:
    return payload == bytes([0x12, 0x45, 0x01])


def is_preset_saved(payload: bytes) -> bool:
    return payload == bytes([0x12, 0x45, 0x00])
