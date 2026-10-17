"""ZIP 321 payment request URI parsing and validation.

Implements the ABNF and semantic rules from ZIP 321, including:

* parameter indexes (``address.1``, ``amount.1``, ...)
* base64url memos and their 512-byte limit
* ``amount`` / ``req-asset`` mutual exclusion
* rejection of memos on transparent recipients
* rejection of Sprout addresses
* unknown ``req-`` parameters invalidate the whole URI

The parser is deliberately strict: a linter should surface anything a
conformant wallet would refuse, before a user discovers it at checkout.
"""

from __future__ import annotations

import base64
import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

from .address import AddressInfo, classify

MAX_ZEC = Decimal(21_000_000)
MAX_MEMO_BYTES = 512

_NAME_RE = re.compile(r"^([A-Za-z][A-Za-z0-9+\-]*)(?:\.([1-9][0-9]{0,3}))?$")
_ADDRESS_RE = re.compile(r"^[A-Za-z0-9]+$")
_AMOUNT_RE = re.compile(r"^[0-9]+(?:\.[0-9]{1,8})?$")
_B64URL_RE = re.compile(r"^[A-Za-z0-9_-]*$")
_QCHAR_RE = re.compile(r"^(?:[A-Za-z0-9\-._~!$'()*+,;:@]|%[0-9A-Fa-f]{2})*$")

KNOWN_PARAMS = {"address", "amount", "memo", "label", "message", "req-asset"}


@dataclass
class Payment:
    index: str  # "" for the unindexed payment
    address: str | None = None
    info: AddressInfo | None = None
    amount: Decimal | None = None
    memo: bytes | None = None
    label: str | None = None
    message: str | None = None
    asset: bytes | None = None

    @property
    def is_transparent(self) -> bool:
        return bool(self.info and self.info.is_transparent)

    @property
    def amount_text(self) -> str:
        return "" if self.amount is None else f"{self.amount:f}"


@dataclass
class PaymentRequest:
    raw: str
    payments: list[Payment] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    @property
    def transparent_payments(self) -> list[Payment]:
        return [p for p in self.payments if p.is_transparent]


class _BadBase64(ValueError):
    pass


def _b64url_decode(value: str) -> bytes:
    padded = value + "=" * (-len(value) % 4)
    try:
        return base64.urlsafe_b64decode(padded.encode("ascii"))
    except Exception as exc:  # binascii.Error is not stable across versions
        raise _BadBase64(f"value is not valid unpadded base64url ({exc})") from None


def _percent_decode(value: str) -> str:
    return re.sub(
        r"%([0-9A-Fa-f]{2})", lambda m: chr(int(m.group(1), 16)), value
    )


def parse_payment_uri(raw: str) -> PaymentRequest:
    """Parse and validate a ``zcash:`` payment request URI."""
    req = PaymentRequest(raw=raw)
    text = raw.strip()
    if not text.lower().startswith("zcash:"):
        req.errors.append("URI must start with 'zcash:'")
        return req
    rest = text[len("zcash:") :]

    if rest.startswith("//"):
        req.errors.append("'//' is not allowed after 'zcash:' (no authority component)")
        return req

    if "?" in rest:
        hier, query = rest.split("?", 1)
    else:
        hier, query = rest, ""

    params: dict[tuple[str, str], str | None] = {}
    # (kept for debugging / future extensions)

    if hier:
        if not _ADDRESS_RE.match(hier):
            req.errors.append(
                "payment address contains characters outside [A-Za-z0-9]"
            )
        params[("address", "")] = hier

    if query:
        for part in query.split("&"):
            if part == "":
                req.errors.append("empty parameter in query string")
                continue
            if "=" in part:
                name_part, value = part.split("=", 1)
            else:
                name_part, value = part, None
            match = _NAME_RE.match(name_part)
            if not match:
                req.errors.append(f"invalid parameter name {name_part!r}")
                continue
            name, index = match.group(1), match.group(2) or ""

            if name not in KNOWN_PARAMS and name.startswith("req-"):
                req.errors.append(
                    f"unknown required parameter '{name}' (all req- parameters must "
                    "be understood; ZIP 321 requires rejecting the whole URI)"
                )
                continue
            if name not in KNOWN_PARAMS:
                req.warnings.append(f"unknown parameter '{name}' ignored")
                continue

            # --- per-parameter value validation -------------------------------
            if value is not None:
                if name == "address":
                    if not _ADDRESS_RE.match(value):
                        req.errors.append(
                            f"address.{index or ''} contains characters outside [A-Za-z0-9]"
                        )
                        continue
                elif name == "amount":
                    if "%" in value:
                        req.errors.append("percent-encoding is not allowed in amount")
                        continue
                    if not _AMOUNT_RE.match(value):
                        req.errors.append(
                            f"invalid amount {value!r} (decimal point, 1-8 fractional "
                            "digits, no grouping separators)"
                        )
                        continue
                    try:
                        amount = Decimal(value)
                    except InvalidOperation:  # pragma: no cover
                        req.errors.append(f"invalid amount {value!r}")
                        continue
                    if amount > MAX_ZEC:
                        req.errors.append(
                            f"amount {value!r} exceeds the 21,000,000 ZEC supply"
                        )
                        continue
                elif name in {"memo", "req-asset"}:
                    if not _B64URL_RE.match(value):
                        req.errors.append(
                            f"{name} must be unpadded base64url "
                            "(characters '+', '/' and '=' are not allowed)"
                        )
                        continue
                    if name == "memo":
                        try:
                            memo = _b64url_decode(value)
                        except _BadBase64 as exc:
                            req.errors.append(f"memo: {exc}")
                            continue
                        if len(memo) > MAX_MEMO_BYTES:
                            req.errors.append(
                                f"memo is {len(memo)} bytes; the maximum is "
                                f"{MAX_MEMO_BYTES}"
                            )
                            continue
                else:  # label, message
                    if not _QCHAR_RE.match(value):
                        req.errors.append(
                            f"{name} contains characters not allowed by ZIP 321"
                        )
                        continue

            key = (name, index)
            if key in params:
                req.errors.append(
                    f"duplicate parameter '{name}{'.' + index if index else ''}'"
                )
                continue
            params[key] = value

    # --- cross-parameter semantics -------------------------------------------
    indexes = {index for (_, index) in params}
    for name, index in params:
        if name != "address" and ("address", index) not in params:
            req.errors.append(
                f"parameter '{name}{'.' + index if index else ''}' has no matching "
                "address parameter"
            )
    if ("address", "") not in params and not any(
        name == "address" for name, _ in params
    ):
        req.errors.append("payment request contains no address")

    for index in indexes:
        amount = params.get(("amount", index))
        asset = params.get(("req-asset", index))
        if amount is not None and asset is not None:
            req.errors.append(
                f"amount and req-asset are mutually exclusive"
                + (f" at index {index}" if index else "")
            )

    # --- build payments -------------------------------------------------------
    for (name, index), _ in params.items():
        if name != "address":
            continue
        address_value = params[("address", index)]
        if address_value is None:
            req.errors.append("address parameter has no value")
            continue
        payment = Payment(index=index, address=address_value)
        info = classify(address_value)
        payment.info = info
        if info.kind == "sprout":
            req.errors.append(
                "Sprout addresses MUST NOT be used in payment requests (ZIP 321; "
                "transfers to Sprout are restricted by ZIP 211)"
            )
        elif info.errors:
            req.errors.append(
                f"invalid address {address_value[:24]}{'…' if len(address_value) > 24 else ''}: "
                + "; ".join(info.errors)
            )

        amount_value = params.get(("amount", index))
        if amount_value is not None:
            try:
                payment.amount = Decimal(amount_value)
            except InvalidOperation:  # pragma: no cover
                pass
        memo_value = params.get(("memo", index))
        if memo_value is not None:
            try:
                payment.memo = _b64url_decode(memo_value)
            except _BadBase64:
                payment.memo = None
            if info.is_transparent:
                req.errors.append(
                    "memo is attached to a transparent recipient; ZIP 321 says a memo "
                    "requires a shielded (memo-capable) address"
                )
        label_value = params.get(("label", index))
        if label_value is not None:
            payment.label = _percent_decode(label_value)
        message_value = params.get(("message", index))
        if message_value is not None:
            payment.message = _percent_decode(message_value)
        asset_value = params.get(("req-asset", index))
        if asset_value is not None:
            try:
                payment.asset = _b64url_decode(asset_value)
            except _BadBase64:
                payment.asset = None
            if not (
                info.is_unified
                and any(r.typecode == 0x03 for r in info.receivers)
            ):
                req.errors.append(
                    "req-asset payments require a Unified Address with an Orchard "
                    "receiver"
                )
        req.payments.append(payment)

    req.payments.sort(key=lambda p: (p.index != "", p.index))

    networks = {p.info.network for p in req.payments if p.info and p.info.network != "unknown"}
    if len(networks) > 1:
        req.warnings.append(
            "payment request mixes addresses from different networks: "
            + ", ".join(sorted(networks))
        )
    return req
