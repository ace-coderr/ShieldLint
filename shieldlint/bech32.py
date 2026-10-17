"""Bech32 / Bech32m (BIP-173 / BIP-350) encoding and decoding.

Implemented from the specifications because Zcash uses Bech32m for Unified
Addresses and Bech32 for Sapling addresses; see ZIP 316 and ZIP 173.
"""

from __future__ import annotations

CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"
CHARSET_REV = {c: i for i, c in enumerate(CHARSET)}

BECH32_CONST = 1
BECH32M_CONST = 0x2BC830A3


class Bech32Error(ValueError):
    """Raised when a Bech32/Bech32m string is malformed."""


def _polymod(values: list[int]) -> int:
    generator = (0x3B6A57B2, 0x26508E6D, 0x1EA119FA, 0x3D4233DD, 0x2A1462B3)
    chk = 1
    for value in values:
        top = chk >> 25
        chk = ((chk & 0x1FFFFFF) << 5) ^ value
        for i in range(5):
            if (top >> i) & 1:
                chk ^= generator[i]
    return chk


def _hrp_expand(hrp: str) -> list[int]:
    return [ord(x) >> 5 for x in hrp] + [0] + [ord(x) & 31 for x in hrp]


def _create_checksum(hrp: str, data: list[int], const: int) -> list[int]:
    values = _hrp_expand(hrp) + data
    polymod = _polymod(values + [0, 0, 0, 0, 0, 0]) ^ const
    return [(polymod >> 5 * (5 - i)) & 31 for i in range(6)]


def _verify_checksum(hrp: str, data: list[int]) -> int:
    """Return the checksum constant the string verifies against (or 0 if invalid)."""
    return _polymod(_hrp_expand(hrp) + data)


def convertbits(data, frombits: int, tobits: int, pad: bool) -> list[int]:
    """General power-of-2 base conversion (BIP-173 reference algorithm)."""
    acc = 0
    bits = 0
    ret: list[int] = []
    maxv = (1 << tobits) - 1
    max_acc = (1 << (frombits + tobits - 1)) - 1
    for value in data:
        if value < 0 or (value >> frombits):
            raise Bech32Error("invalid data value for convertbits")
        acc = ((acc << frombits) | value) & max_acc
        bits += frombits
        while bits >= tobits:
            bits -= tobits
            ret.append((acc >> bits) & maxv)
    if pad:
        if bits:
            ret.append((acc << (tobits - bits)) & maxv)
    elif bits >= frombits or ((acc << (tobits - bits)) & maxv):
        raise Bech32Error("invalid padding in convertbits")
    return ret


def encode(hrp: str, data: list[int], *, bech32m: bool = True) -> str:
    """Encode 5-bit ``data`` with ``hrp`` using Bech32m (default) or Bech32."""
    if not hrp or any(ord(c) < 33 or ord(c) > 126 for c in hrp):
        raise Bech32Error("invalid human-readable part")
    if hrp.lower() != hrp:
        raise Bech32Error("human-readable part must be lowercase")
    const = BECH32M_CONST if bech32m else BECH32_CONST
    combined = data + _create_checksum(hrp, data, const)
    return hrp + "1" + "".join(CHARSET[d] for d in combined)


def decode(s: str) -> tuple[str, list[int], bool]:
    """Decode a Bech32/Bech32m string.

    Returns ``(hrp, data, is_bech32m)`` where ``data`` excludes the checksum.
    Raises :class:`Bech32Error` on any malformation.
    """
    if not isinstance(s, str):
        raise Bech32Error("not a string")
    if len(s) < 8:
        raise Bech32Error("too short")
    if any(ord(c) < 33 or ord(c) > 126 for c in s):
        raise Bech32Error("invalid character")
    if s.lower() != s and s.upper() != s:
        raise Bech32Error("mixed case")
    s = s.lower()
    pos = s.rfind("1")
    if pos < 1 or pos + 7 > len(s):
        raise Bech32Error("missing or misplaced separator")
    hrp = s[:pos]
    try:
        data = [CHARSET_REV[c] for c in s[pos + 1 :]]
    except KeyError as exc:
        raise Bech32Error(f"invalid data character {exc.args[0]!r}") from None
    const = _verify_checksum(hrp, data)
    if const == BECH32_CONST:
        return hrp, data[:-6], False
    if const == BECH32M_CONST:
        return hrp, data[:-6], True
    raise Bech32Error("invalid checksum")


def decode_bytes(hrp: str, s: str, *, bech32m: bool = True) -> bytes:
    """Decode ``s``, requiring the expected ``hrp`` and checksum variant."""
    got_hrp, data, got_m = decode(s)
    if got_hrp != hrp:
        raise Bech32Error(f"unexpected human-readable part {got_hrp!r}")
    if got_m != bech32m:
        raise Bech32Error("wrong checksum variant (bech32 vs bech32m)")
    try:
        return bytes(convertbits(data, 5, 8, False))
    except Bech32Error:
        raise
