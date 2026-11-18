"""Documented request frames for the Sonicake SysEx protocol.

These frames are exact constants observed against the device; they are not
computed at send time. Use them as-is.
"""

REQUESTS: dict[str, str] = {
    "estado": "8080F0000900010000000201020401F7",
    "nomes": "8080F0000E00010000000201020400F7",
    "numero": "8080F0000700010000000201020403F7",
    "globais": "8080F00B0900010000000201020100F7",
    "nomes_ir": "8080F0020900010000000201020200F7",
    "nomes_clone": "8080F0030500010000000201020204F7",
    "modificado": "8080F0010500010000000201020405F7",
    "init_session": "8080F0050900010000000201020300F7",
}


def request_bytes(name: str) -> bytes:
    if name not in REQUESTS:
        raise KeyError(f"unknown request: {name}")
    return bytes.fromhex(REQUESTS[name])
