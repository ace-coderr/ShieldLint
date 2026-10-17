"""F4Jumble, the reversible byte permutation used by Unified Addresses.

Implemented from ZIP 316 ("Jumbling").  The construction is a 4-round
unkeyed Feistel network built from BLAKE2b; it is *not* a hash.  It exists
so that every Unified Address string looks uniformly random, which prevents
an address from advertising which receiver types it contains and defeats
certain malleability attacks.
"""

from __future__ import annotations

import hashlib
import struct

L_H = 64  # bytes
L_M_MAX = (2**16 + 1) * L_H  # 4,194,368 bytes
MIN_LEN = 38

_H_PERSON = b"UA_F4Jumble_H"
_G_PERSON = b"UA_F4Jumble_G"


class F4JumbleError(ValueError):
    pass


def _h(i: int, u: bytes, out_len: int) -> bytes:
    person = _H_PERSON + bytes([i, 0, 0])
    return hashlib.blake2b(u, digest_size=out_len, person=person).digest()


def _g(i: int, u: bytes, out_len: int) -> bytes:
    chunks = []
    produced = 0
    j = 0
    while produced < out_len:
        person = _G_PERSON + bytes([i]) + struct.pack("<H", j)
        chunks.append(hashlib.blake2b(u, digest_size=64, person=person).digest())
        produced += 64
        j += 1
    return b"".join(chunks)[:out_len]


def _xor(a: bytes, b: bytes) -> bytes:
    return bytes(x ^ y for x, y in zip(a, b))


def _split_lengths(length: int) -> tuple[int, int]:
    l_l = min(L_H, length // 2)
    l_r = length - l_l
    return l_l, l_r


def f4jumble(m: bytes) -> bytes:
    """Apply F4Jumble to ``m`` (38 <= len(m) <= L_M_MAX)."""
    length = len(m)
    if not (MIN_LEN <= length <= L_M_MAX):
        raise F4JumbleError(f"input length {length} outside [{MIN_LEN}, {L_M_MAX}]")
    l_l, l_r = _split_lengths(length)
    a, b = m[:l_l], m[l_l:]
    x = _xor(b, _g(0, a, l_r))
    y = _xor(a, _h(0, x, l_l))
    d = _xor(x, _g(1, y, l_r))
    c = _xor(y, _h(1, d, l_l))
    return c + d


def f4jumble_inv(m: bytes) -> bytes:
    """Invert :func:`f4jumble`."""
    length = len(m)
    if not (MIN_LEN <= length <= L_M_MAX):
        raise F4JumbleError(f"input length {length} outside [{MIN_LEN}, {L_M_MAX}]")
    l_l, _ = _split_lengths(length)
    c, d = m[:l_l], m[l_l:]
    y = _xor(c, _h(1, d, l_l))
    x = _xor(d, _g(1, y, length - l_l))
    a = _xor(y, _h(0, x, l_l))
    b = _xor(x, _g(0, a, length - l_l))
    return a + b
