"""Offline decoding of Zcash addresses, viewing keys and spending keys.

Everything here is implemented from the public specifications:

* ZIP 316 — Unified Addresses and Unified Viewing Keys (incl. F4Jumble)
* ZIP 173 — Bech32 (Sapling addresses)
* Zcash protocol spec §5.6 — transparent / Sprout address encodings

No network access and no key material handling beyond recognising an
encoding; the module never derives keys.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable, Iterator

from . import base58, bech32
from .f4jumble import F4JumbleError, f4jumble, f4jumble_inv

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Transparent address version prefixes (2 bytes).
TADDR_VERSIONS = {
    (0x1C, 0xB8): ("transparent-p2pkh", "mainnet"),
    (0x1C, 0xBD): ("transparent-p2sh", "mainnet"),
    (0x1D, 0x25): ("transparent-p2pkh", "testnet"),
    (0x1C, 0xBA): ("transparent-p2sh", "testnet"),
}

#: Sprout address version prefixes (2 bytes).
SPROUT_VERSIONS = {
    (0x16, 0x9A): "mainnet",
    (0x16, 0xB6): "testnet",
}

#: Sapling address / viewing key human-readable parts.
SAPLING_HRPS = {
    "zs": "mainnet",
    "ztestsapling": "testnet",
    "zregtestsapling": "regtest",
}

#: Unified address HRPs -> (network, revision, is_viewing_key)
UNIFIED_HRPS: dict[str, tuple[str, int, bool]] = {
    "u": ("mainnet", 0, False),
    "utest": ("testnet", 0, False),
    "uregtest": ("regtest", 0, False),
    "zu": ("mainnet", 2, False),
    "zutest": ("testnet", 2, False),
    "zuregtest": ("regtest", 2, False),
    "tu": ("mainnet", 2, False),
    "tutest": ("testnet", 2, False),
    "turegtest": ("regtest", 2, False),
    "uview": ("mainnet", 0, True),
    "uviewtest": ("testnet", 0, True),
    "uivk": ("mainnet", 0, True),
    "uivktest": ("testnet", 0, True),
    "uvf": ("mainnet", 2, True),
    "uvftest": ("testnet", 2, True),
    "uvi": ("mainnet", 2, True),
    "uvitest": ("testnet", 2, True),
}

#: Sapling viewing key HRPs.
SAPLING_VIEW_HRPS = {
    "zxviews": ("mainnet", "full"),
    "zxviewtestsapling": ("testnet", "full"),
}

SPENDING_KEY_PREFIXES = ("secret-extended-key-main", "secret-extended-key-test")

#: Receiver typecodes (ZIP 316 typecode registry).
RECEIVER_TYPES = {
    0x00: ("transparent-p2pkh", 20, "Transparent P2PKH"),
    0x01: ("transparent-p2sh", 20, "Transparent P2SH"),
    0x02: ("sapling", 43, "Sapling"),
    0x03: ("orchard", 43, "Orchard"),
}
METADATA_TYPES = {
    0xE0: ("expiry-height", 4, "Address Expiry Height"),
    0xE1: ("expiry-time", 8, "Address Expiry Time"),
}
MUST_UNDERSTAND_METADATA = range(0xE2, 0xFD)
EXPERIMENTAL_TYPES = range(0xFFFA, 0x10000)

MAX_LEN_M = (2**16 + 1) * 64
MAX_FIELD = 0x2000000

# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass
class Receiver:
    typecode: int
    kind: str | None  # None for unknown / unassigned
    data: bytes

    @property
    def name(self) -> str:
        return self.kind or f"unknown-0x{self.typecode:04x}"

    @property
    def transparent(self) -> bool:
        return self.typecode in (0x00, 0x01)


@dataclass
class Metadata:
    typecode: int
    kind: str | None
    value: int


@dataclass
class AddressInfo:
    """Result of classifying a single string token."""

    raw: str
    kind: str = "unknown"
    network: str = "unknown"
    hrp: str | None = None
    revision: int | None = None
    receivers: list[Receiver] = field(default_factory=list)
    metadata: list[Metadata] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    # -- convenience predicates ------------------------------------------------
    @property
    def ok(self) -> bool:
        return not self.errors

    @property
    def is_address(self) -> bool:
        return self.kind in {
            "transparent-p2pkh",
            "transparent-p2sh",
            "sapling",
            "unified",
            "sprout",
        }

    @property
    def is_unified(self) -> bool:
        return self.kind == "unified"

    @property
    def is_transparent(self) -> bool:
        return self.kind in {"transparent-p2pkh", "transparent-p2sh"}

    @property
    def has_transparent_receiver(self) -> bool:
        return any(r.transparent for r in self.receivers)

    @property
    def shielded_receivers(self) -> list[Receiver]:
        return [r for r in self.receivers if not r.transparent]

    @property
    def receiver_summary(self) -> str:
        if not self.receivers:
            return "—"
        return ", ".join(r.name for r in self.receivers)


# ---------------------------------------------------------------------------
# CompactSize (Bitcoin-style varint), used inside Unified Address encodings
# ---------------------------------------------------------------------------


def _read_compact_size(buf: bytes, pos: int) -> tuple[int, int]:
    if pos >= len(buf):
        raise ValueError("truncated compactSize")
    first = buf[pos]
    if first < 0xFD:
        return first, pos + 1
    width = {0xFD: 2, 0xFE: 4, 0xFF: 8}[first]
    end = pos + 1 + width
    if end > len(buf):
        raise ValueError("truncated compactSize")
    return int.from_bytes(buf[pos + 1 : end], "little"), end


def _write_compact_size(value: int) -> bytes:
    if value < 0xFD:
        return bytes([value])
    if value <= 0xFFFF:
        return b"\xFD" + value.to_bytes(2, "little")
    if value <= 0xFFFFFFFF:
        return b"\xFE" + value.to_bytes(4, "little")
    return b"\xFF" + value.to_bytes(8, "little")


# ---------------------------------------------------------------------------
# Unified address / viewing key encoding (ZIP 316)
# ---------------------------------------------------------------------------


def _padding_for(hrp: str) -> bytes:
    raw = hrp.encode("ascii")
    if len(raw) > 16:
        raise ValueError("HRP too long for padding")
    return raw + b"\x00" * (16 - len(raw))


def encode_unified(
    items: Iterable[tuple[int, bytes]],
    hrp: str,
    metadata: Iterable[tuple[int, bytes]] = (),
) -> str:
    """Encode a Unified Address (or viewing key) per ZIP 316.

    ``items`` are ``(typecode, raw_encoding)`` pairs; the caller is
    responsible for supplying receiver/typecode combinations that are valid
    for ``hrp`` (e.g. no transparent receivers under ``zu``).
    """
    payload = bytearray()
    for typecode, raw in sorted(items, key=lambda it: it[0]):
        payload += _write_compact_size(typecode)
        payload += _write_compact_size(len(raw))
        payload += raw
    for typecode, raw in metadata:
        payload += _write_compact_size(typecode)
        payload += _write_compact_size(len(raw))
        payload += raw
    jumbled = f4jumble(bytes(payload) + _padding_for(hrp))
    return bech32.encode(hrp, bech32.convertbits(jumbled, 8, 5, True), bech32m=True)


def decode_unified(raw: str) -> AddressInfo:
    """Decode a Unified Address / Unified Viewing Key string."""
    info = AddressInfo(raw=raw)
    try:
        hrp, data, is_m = bech32.decode(raw)
    except bech32.Bech32Error as exc:
        info.kind = "unified"
        info.errors.append(f"not valid Bech32m: {exc}")
        return info
    info.hrp = hrp
    if hrp not in UNIFIED_HRPS:
        info.kind = "unified"
        info.errors.append(f"unknown Unified Address human-readable part {hrp!r}")
        return info
    if not is_m:
        info.kind = "unified"
        info.errors.append("Unified encodings must use Bech32m, not Bech32")
        return info
    network, revision, is_viewing_key = UNIFIED_HRPS[hrp]
    info.network = network
    info.revision = revision
    info.kind = "unified-viewing-key" if is_viewing_key else "unified"

    try:
        body = bytes(bech32.convertbits(data, 5, 8, False))
    except bech32.Bech32Error as exc:
        info.errors.append(f"bad payload encoding: {exc}")
        return info
    if not (38 <= len(body) <= MAX_LEN_M):
        info.errors.append(f"encoded length {len(body)} outside [38, {MAX_LEN_M}]")
        return info
    try:
        decoded = f4jumble_inv(body)
    except F4JumbleError as exc:  # pragma: no cover - length already checked
        info.errors.append(str(exc))
        return info
    pad = _padding_for(hrp)
    if not decoded.endswith(pad):
        info.errors.append(
            "padding mismatch: this string is not a well-formed "
            f"{'viewing key' if is_viewing_key else 'address'} for HRP {hrp!r}"
        )
        return info
    decoded = decoded[: -len(pad)]

    pos = 0
    last_typecode = -1
    try:
        while pos < len(decoded):
            typecode, pos = _read_compact_size(decoded, pos)
            length, pos = _read_compact_size(decoded, pos)
            if typecode > MAX_FIELD or length > MAX_FIELD:
                raise ValueError("typecode or length exceeds 0x2000000")
            if pos + length > len(decoded):
                raise ValueError("item overruns payload")
            item = decoded[pos : pos + length]
            pos += length
            if typecode < last_typecode:
                info.notes.append("items are not in ascending typecode order")
            last_typecode = typecode

            if typecode in RECEIVER_TYPES and not is_viewing_key:
                kind, expected, _ = RECEIVER_TYPES[typecode]
                if length != expected:
                    raise ValueError(
                        f"{kind} receiver must be {expected} bytes, got {length}"
                    )
                info.receivers.append(Receiver(typecode, kind, item))
            elif typecode in METADATA_TYPES:
                kind, expected, _ = METADATA_TYPES[typecode]
                if is_viewing_key and revision == 0:
                    raise ValueError(
                        "metadata items are not permitted in revision 0 viewing keys"
                    )
                if length != expected:
                    raise ValueError(f"{kind} metadata must be {expected} bytes")
                info.metadata.append(
                    Metadata(typecode, kind, int.from_bytes(item, "little"))
                )
            elif typecode in RECEIVER_TYPES and is_viewing_key:
                kind, _, _ = RECEIVER_TYPES[typecode]
                info.receivers.append(Receiver(typecode, kind + "-view-key", item))
            elif typecode in MUST_UNDERSTAND_METADATA:
                raise ValueError(
                    f"unknown MUST-understand metadata typecode 0x{typecode:04x}"
                )
            elif typecode in EXPERIMENTAL_TYPES:
                info.receivers.append(Receiver(typecode, None, item))
                info.notes.append(f"experimental typecode 0x{typecode:04x} present")
            else:
                info.receivers.append(Receiver(typecode, None, item))
                info.notes.append(f"unrecognised typecode 0x{typecode:04x} present")
    except ValueError as exc:
        info.errors.append(str(exc))
        return info

    if not info.receivers and not info.metadata:
        info.errors.append("no receivers in encoding")
        return info
    if revision == 2 and not is_viewing_key:
        if hrp.startswith("zu") and info.has_transparent_receiver:
            info.errors.append("zu address must not contain transparent receivers")
        if not hrp.startswith(("zu", "tu")):
            info.errors.append("revision 2 addresses must use a zu/tu prefix")
    return info


def decode_sapling(raw: str) -> AddressInfo:
    info = AddressInfo(raw=raw)
    try:
        hrp, data, is_m = bech32.decode(raw)
    except bech32.Bech32Error as exc:
        info.kind = "sapling"
        info.errors.append(f"not valid Bech32: {exc}")
        return info
    info.hrp = hrp
    if hrp not in SAPLING_HRPS:
        info.kind = "sapling"
        info.errors.append(f"unknown Sapling human-readable part {hrp!r}")
        return info
    info.kind = "sapling"
    info.network = SAPLING_HRPS[hrp]
    if is_m:
        info.errors.append("Sapling addresses use Bech32, not Bech32m")
        return info
    try:
        body = bytes(bech32.convertbits(data, 5, 8, False))
    except bech32.Bech32Error as exc:
        info.errors.append(str(exc))
        return info
    if len(body) != 43:
        info.errors.append(f"Sapling address payload must be 43 bytes, got {len(body)}")
        return info
    info.receivers.append(Receiver(0x02, "sapling", body))
    return info


def decode_transparent(raw: str) -> AddressInfo:
    info = AddressInfo(raw=raw)
    try:
        payload = base58.decode_check(raw)
    except base58.Base58Error as exc:
        info.kind = "transparent"
        info.errors.append(f"invalid Base58Check: {exc}")
        return info
    if len(payload) != 22:
        info.kind = "transparent"
        info.errors.append(f"expected 22-byte payload, got {len(payload)}")
        return info
    version = (payload[0], payload[1])
    kind, network = TADDR_VERSIONS.get(
        version, ("transparent", "unknown")
    )
    info.kind = kind
    info.network = network
    if kind == "transparent":
        info.errors.append(f"unknown transparent version prefix 0x{payload[0]:02x}{payload[1]:02x}")
    if kind in {"transparent-p2pkh", "transparent-p2sh"}:
        typecode = 0x00 if kind.endswith("p2pkh") else 0x01
        info.receivers.append(Receiver(typecode, "transparent", payload[2:]))
    return info


def decode_sprout(raw: str) -> AddressInfo:
    info = AddressInfo(raw=raw, kind="sprout")
    try:
        payload = base58.decode_check(raw)
    except base58.Base58Error as exc:
        info.errors.append(f"invalid Base58Check: {exc}")
        return info
    if len(payload) != 66:
        info.errors.append(f"expected 66-byte Sprout payload, got {len(payload)}")
        return info
    version = (payload[0], payload[1])
    if version not in SPROUT_VERSIONS:
        info.errors.append(f"unknown Sprout version prefix 0x{version[0]:02x}{version[1]:02x}")
        return info
    info.network = SPROUT_VERSIONS[version]
    info.notes.append("Sprout is deprecated; sending to Sprout is restricted by ZIP 211")
    return info


def decode_sapling_view(raw: str) -> AddressInfo:
    info = AddressInfo(raw=raw, kind="sapling-viewing-key")
    try:
        hrp, data, is_m = bech32.decode(raw)
    except bech32.Bech32Error as exc:
        info.errors.append(f"not valid Bech32: {exc}")
        return info
    info.hrp = hrp
    if hrp not in SAPLING_VIEW_HRPS:
        info.errors.append(f"unknown Sapling viewing key HRP {hrp!r}")
        return info
    info.network = SAPLING_VIEW_HRPS[hrp][0]
    if is_m:
        info.errors.append("Sapling viewing keys use Bech32, not Bech32m")
        return info
    try:
        body = bytes(bech32.convertbits(data, 5, 8, False))
    except bech32.Bech32Error as exc:
        info.errors.append(str(exc))
        return info
    if len(body) != 169:
        info.errors.append(f"extended full viewing key must be 169 bytes, got {len(body)}")
        return info
    return info


# ---------------------------------------------------------------------------
# Token scanning
# ---------------------------------------------------------------------------

_B58 = "1-9A-HJ-NP-Za-km-z"
_B32 = "02-9ac-hj-np-z"

_TOKEN_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "spending-key",
        re.compile(
            r"\bsecret-extended-key-(?:main|test)1[" + _B32 + r"]{40,}"
        ),
    ),
    (
        "unified-viewing-key",
        re.compile(
            r"\b(?:uvitest|uvftest|uivktest|uviewtest|uvi|uvf|uivk|uview)1["
            + _B32
            + r"]{40,}"
        ),
    ),
    (
        "sapling-viewing-key",
        re.compile(
            r"\b(?:zxviewtestsapling|zxviews)1[" + _B32 + r"]{40,}"
        ),
    ),
    (
        "unified",
        re.compile(
            r"\b(?:zuregtest|turegtest|uregtest|zutest|tutest|utest|zu|tu|u)1["
            + _B32
            + r"]{40,}"
        ),
    ),
    (
        "sapling",
        re.compile(
            r"\b(?:zregtestsapling|ztestsapling|zs)1[" + _B32 + r"]{60,}"
        ),
    ),
    (
        "transparent",
        re.compile(
            r"\bt(?:1|3|m|2)[" + _B58 + r"]{33}\b"
        ),
    ),
    (
        "sprout",
        re.compile(r"\b(?:zc|zt)[" + _B58 + r"]{90,96}\b"),
    ),
]

_KIND_TO_DECODER = {
    "transparent": decode_transparent,
    "sapling": decode_sapling,
    "sprout": decode_sprout,
    "unified": decode_unified,
    "unified-viewing-key": decode_unified,
    "sapling-viewing-key": decode_sapling_view,
}


@dataclass(frozen=True)
class Token:
    start: int
    end: int
    text: str
    kind_hint: str


def iter_address_tokens(text: str) -> Iterator[Token]:
    """Yield address / key-like tokens found in ``text``.

    Longer, more specific patterns are tried first and claimed spans are
    removed so that a Unified Address is never reported as a Sapling address.
    """
    claimed: list[tuple[int, int]] = []
    for kind, pattern in _TOKEN_PATTERNS:
        for match in pattern.finditer(text):
            start, end = match.span()
            if any(s < end and start < e for s, e in claimed):
                continue
            claimed.append((start, end))
            yield Token(start, end, match.group(0), kind)


def classify(token: str, kind_hint: str | None = None) -> AddressInfo:
    """Decode ``token`` into an :class:`AddressInfo` (never raises)."""
    if kind_hint is None:
        hint = None
        for tok in iter_address_tokens(token):
            if token[tok.start : tok.end] == token:
                hint = tok.kind_hint
                break
        if hint is None:
            # Fall back to prefix sniffing so that malformed strings are still
            # classified (used by the malformed-address rule).
            lowered = token.lower()
            if lowered.startswith(SPENDING_KEY_PREFIXES):
                hint = "spending-key"
            elif lowered.startswith(("u1", "utest1", "uregtest1", "zu1", "tu1")):
                hint = "unified"
            elif lowered.startswith(("zs1", "ztestsapling1", "zregtestsapling1")):
                hint = "sapling"
            elif lowered.startswith(("zxviews1", "zxviewtestsapling1")):
                hint = "sapling-viewing-key"
            elif lowered.startswith(("uview1", "uivk1", "uvf1", "uvi1")):
                hint = "unified-viewing-key"
            elif lowered.startswith(("t1", "t3", "tm", "t2")):
                hint = "transparent"
            elif lowered.startswith(("zc", "zt")):
                hint = "sprout"
            else:
                return AddressInfo(raw=token)
        kind_hint = hint
    if kind_hint == "spending-key":
        return AddressInfo(
            raw=token,
            kind="spending-key",
            notes=["this is secret key material"],
        )
    decoder = _KIND_TO_DECODER.get(kind_hint, lambda t: AddressInfo(raw=t))
    info = decoder(token)
    if kind_hint == "transparent" and not info.errors:
        info.kind = info.kind
    return info


def find_addresses(text: str) -> list[tuple[int, int, AddressInfo]]:
    """Return ``(start, end, info)`` for every address-like token in ``text``."""
    out = []
    for tok in iter_address_tokens(text):
        out.append((tok.start, tok.end, classify(tok.text, tok.kind_hint)))
    return out
