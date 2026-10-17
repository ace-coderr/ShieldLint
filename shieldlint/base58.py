"""Base58Check (Bitcoin alphabet), used for Zcash transparent addresses."""

from __future__ import annotations

import hashlib

ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
ALPHABET_REV = {c: i for i, c in enumerate(ALPHABET)}


class Base58Error(ValueError):
    pass


def decode(s: str) -> bytes:
    if not s:
        raise Base58Error("empty string")
    num = 0
    for char in s:
        try:
            num = num * 58 + ALPHABET_REV[char]
        except KeyError:
            raise Base58Error(f"invalid base58 character {char!r}") from None
    body = num.to_bytes((num.bit_length() + 7) // 8, "big") if num else b""
    pad = len(s) - len(s.lstrip("1"))
    return b"\x00" * pad + body


def encode(data: bytes) -> str:
    num = int.from_bytes(data, "big")
    out = ""
    while num:
        num, rem = divmod(num, 58)
        out = ALPHABET[rem] + out
    pad = len(data) - len(data.lstrip(b"\x00"))
    return "1" * pad + out


def _checksum(data: bytes) -> bytes:
    return hashlib.sha256(hashlib.sha256(data).digest()).digest()[:4]


def decode_check(s: str) -> bytes:
    raw = decode(s)
    if len(raw) < 5:
        raise Base58Error("too short for Base58Check")
    payload, checksum = raw[:-4], raw[-4:]
    if _checksum(payload) != checksum:
        raise Base58Error("checksum mismatch")
    return payload


def encode_check(payload: bytes) -> str:
    return encode(payload + _checksum(payload))
