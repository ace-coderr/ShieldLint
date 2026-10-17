"""The ShieldLint rule set.

Each rule is a small, explainable check tied to a public Zcash standard or
privacy recommendation.  Heuristics are intentionally conservative: a rule
fires only when the code contains both a privacy-relevant value (address,
key, memo, URI) and a plausible sink for it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, Iterable, Iterator

from .address import AddressInfo
from .source import Literal, SourceFile
from .uri import PaymentRequest

SEVERITIES = ("error", "warning", "note")


@dataclass(frozen=True)
class Rule:
    id: str
    slug: str
    severity: str
    title: str
    summary: str
    rationale: str
    remediation: str
    refs: tuple[tuple[str, str], ...] = ()

    @property
    def anchor(self) -> str:
        return self.slug

    @property
    def url(self) -> str:
        return f"docs/rules.md#{self.id.lower()}-{self.slug}"


RULES: list[Rule] = [
    Rule(
        id="SL001",
        slug="transparent-recipient",
        severity="error",
        title="Payment sent to a transparent address",
        summary="A send/payout call hands a transparent (t-address) recipient to a "
        "transaction builder.",
        rationale="Transparent addresses publish the amount, the sender and the "
        "recipient on-chain. A shielded wallet that pays a t-address leaks the "
        "whole payment, and the receiving side cannot recover privacy later.",
        remediation="Send to a shielded receiver instead: a Unified Address with "
        "Orchard/Sapling receivers (u1…/zu1…) or a Sapling address. If the "
        "counterparty only accepts transparent, treat the payment as public and "
        "say so in your UI.",
        refs=(
            ("ZIP 316 — Unified Addresses", "https://zips.z.cash/zip-0316"),
            ("ZIP 315 — multiple pools", "https://zips.z.cash/zip-0315"),
        ),
    ),
    Rule(
        id="SL002",
        slug="transparent-address-literal",
        severity="warning",
        title="Transparent address literal in source",
        summary="A t-address is hard-coded in source (config, fixtures or a "
        "refund/donation constant).",
        rationale="A t-address in source tends to become a permanent, publicly "
        "linkable endpoint: every payment to it is visible, and the code base "
        "itself becomes the link between you and the address.",
        remediation="Prefer a shielded Unified Address or a Sapling address. If a "
        "transparent address is unavoidable, keep it out of logs, version control "
        "and client bundles, and rotate it per deployment.",
    ),
    Rule(
        id="SL003",
        slug="ua-transparent-receiver",
        severity="warning",
        title="Unified Address carries a transparent receiver",
        summary="The UA contains a transparent receiver (typecode 0x00/0x01), so "
        "senders may downgrade to it.",
        rationale="A Unified Address lets the sender choose the best receiver it "
        "supports. If a transparent receiver is present, a transparent-only wallet "
        "will pick it and the payment becomes public. Revision 2 of ZIP 316 added "
        "`zu` addresses precisely to rule this out.",
        remediation="Distribute a shielded-only address (`zu1…` on revision 2, or a "
        "UA containing only Orchard/Sapling receivers). Keep transparent receivers "
        "for edge cases only, and never in the address you publish.",
        refs=(("ZIP 316 — Revisions", "https://zips.z.cash/zip-0316#revisions"),),
    ),
    Rule(
        id="SL004",
        slug="memo-to-transparent",
        severity="error",
        title="Memo attached to a transparent recipient",
        summary="A memo is paired with a transparent address in the same payment.",
        rationale="Memos exist only inside shielded outputs. A memo aimed at a "
        "t-address is either dropped by the wallet or smuggled through an off-chain "
        "channel; ZIP 321 declares such payment requests invalid.",
        remediation="Send the payment to a shielded address with a memo, or move "
        "the reference off-chain (order id in your own database) for transparent "
        "payments.",
        refs=(("ZIP 321 — payment request URIs", "https://zips.z.cash/zip-0321"),),
    ),
    Rule(
        id="SL005",
        slug="memo-exposure",
        severity="warning",
        title="Memo content passed to a logger",
        summary="A memo value is written to a log or printed.",
        rationale="Memos routinely carry invoices, order references, emails and "
        "free-form notes. Logs are replicated, shipped to third parties and rarely "
        "expire, so a memo in a log is a permanent disclosure to whoever can read "
        "the logs.",
        remediation="Log a random payment reference or a salted hash of the memo, "
        "and store the memo encrypted where only the settlement service can read it.",
    ),
    Rule(
        id="SL006",
        slug="viewing-key-exposure",
        severity="error",
        title="Viewing key material in source or logs",
        summary="A Unified/Sapling viewing key (UFVK/UIVK/IVK/OVK or extfvk) appears "
        "as a literal or flows into a log call.",
        rationale="A full viewing key decrypts every incoming note and memo for the "
        "account it belongs to, and an incoming viewing key reveals all incoming "
        "payments. Leaking one deanonymizes the wallet without ever touching the "
        "spending key.",
        remediation="Never commit viewing keys. Load them at runtime from a secret "
        "store, scope them to a single account, and redact them from logs and error "
        "reporting.",
        refs=(("ZIP 316 — Unified Viewing Keys", "https://zips.z.cash/zip-0316"),),
    ),
    Rule(
        id="SL007",
        slug="spending-key-material",
        severity="error",
        title="Spending key material committed to source",
        summary="A string that looks like a spending key, seed or mnemonic is "
        "assigned in source.",
        rationale="Anyone who can read the repository can spend the funds. Even "
        "after removal, the value lives on in git history, CI logs and caches.",
        remediation="Rotate the key now, purge it from history, and read secrets "
        "from a KMS/environment at runtime. Prefer a dedicated hot-wallet account "
        "with limited funds for automated payouts.",
    ),
    Rule(
        id="SL008",
        slug="transparent-spend-source",
        severity="warning",
        title="Transparent funds selected as the spend source",
        summary="The code explicitly spends from the transparent pool.",
        rationale="Spending a transparent UTXO publishes the input side of the "
        "transaction and links your transparent balance to the recipient. ZIP 315 "
        "recommends spending shielded notes whenever the wallet has them.",
        remediation="Let the wallet choose the source (shielded first), or select a "
        "shielded pool explicitly. Keep transparent spending behind an explicit, "
        "user-visible choice.",
        refs=(("ZIP 315 — wallet handling of multiple pools", "https://zips.z.cash/zip-0315"),),
    ),
    Rule(
        id="SL009",
        slug="testnet-address-in-source",
        severity="warning",
        title="Testnet or regtest address in source",
        summary="A testnet/regtest address literal is present.",
        rationale="Test addresses are funded by faucets and controlled by nobody in "
        "production. Shipping one is either dead code or a misconfiguration that can "
        "route real value to the wrong network.",
        remediation="Gate test addresses behind an explicit network switch, or move "
        "them into test fixtures excluded from the lint run.",
    ),
    Rule(
        id="SL010",
        slug="payment-uri-to-transparent",
        severity="error",
        title="Payment request URI pays a transparent address",
        summary="A `zcash:` URI in source targets a transparent recipient.",
        rationale="A payment URI is a promise about how the payment will happen. If "
        "it points at a t-address, every wallet that honours it produces a fully "
        "public payment, and the invoice amount is public too.",
        remediation="Build the URI around a shielded Unified Address or Sapling "
        "address. If a transparent leg is required, generate the URI per request and "
        "document the exposure.",
        refs=(("ZIP 321 — payment request URIs", "https://zips.z.cash/zip-0321"),),
    ),
    Rule(
        id="SL011",
        slug="invalid-payment-uri",
        severity="error",
        title="Invalid ZIP 321 payment request",
        summary="A `zcash:` URI literal fails ZIP 321 validation.",
        rationale="Wallets must reject non-conformant payment requests, so an invalid "
        "URI is a checkout that fails at the worst possible moment — or silently "
        "drops a memo or a recipient.",
        remediation="Fix the URI: check parameter indexes, base64url memos, the "
        "512-byte memo limit, amount formatting and that every parameter has a "
        "matching address.",
        refs=(("ZIP 321 — payment request URIs", "https://zips.z.cash/zip-0321"),),
    ),
    Rule(
        id="SL012",
        slug="memo-too-long",
        severity="error",
        title="Memo exceeds the 512-byte limit",
        summary="A memo literal is longer than the 512 bytes a shielded output can "
        "carry.",
        rationale="Zcash memos are fixed-size 512-byte fields. Longer text is "
        "truncated by wallets or rejected, which breaks invoice matching and can "
        "silently lose structured data.",
        remediation="Put the payload off-chain and reference it from the memo "
        "(order id, hash), or split it into multiple payments.",
    ),
    Rule(
        id="SL013",
        slug="sprout-address",
        severity="warning",
        title="Sprout address",
        summary="A Sprout address is used in source.",
        rationale="Sprout is deprecated: transfers into Sprout are restricted by ZIP "
        "211 and most modern wallets cannot send there at all.",
        remediation="Migrate to Orchard, Sapling, or a Unified Address.",
        refs=(("ZIP 211 — disabling new Sprout value", "https://zips.z.cash/zip-0211"),),
    ),
    Rule(
        id="SL014",
        slug="malformed-address",
        severity="warning",
        title="Malformed address literal",
        summary="A string that looks like a Zcash address fails decoding "
        "(checksum, length or network prefix).",
        rationale="A truncated or mistyped address is not a privacy bug, it is a "
        "fund-loss bug: the network will accept the transaction and the value lands "
        "somewhere nobody can spend.",
        remediation="Re-copy the address from the wallet and validate it with a "
        "decoder before use; add a checksum check at the boundary where addresses "
        "enter your system.",
    ),
]

RULE_BY_ID = {r.id: r for r in RULES}


# ---------------------------------------------------------------------------
# Evidence
# ---------------------------------------------------------------------------

_SEND_CALL_RE = re.compile(
    r"\b(send|sendmany|send_many|sendtoaddress|send_to_address|pay|payout|payment|"
    r"transfer|withdraw|refund|tip|disburse|settle|publish_transaction)\w*\s*\(",
    re.IGNORECASE,
)
_RECIPIENT_KEY_RE = re.compile(
    r"\b(recipient|payee|destination|dest|to_address|toaddress|recipient_address|"
    r"payee_address|output_address)\s*[=:]",
    re.IGNORECASE,
)
_LOG_RE = re.compile(
    r"\b(console\.\w+|logger\.\w+|log\.\w+|logging\.\w+|print\w*\s*\(|println!|"
    r"print!|eprintln!|dbg!|tracing::\w+|(?:info|warn|error|debug|trace)!\s*\(|"
    r"System\.(?:out|err)\.\w+|puts\b|pp\b|fmt\.Print\w*)",
    re.IGNORECASE,
)
_VIEW_KEY_IDENT_RE = re.compile(
    r"\b(\w*fvk|\w*ivk|\w*ovk|viewing[_-]?key|\w*view[_-]?key|viewingkey)\b",
    re.IGNORECASE,
)
_SECRET_IDENT_RE = re.compile(
    r"\b(spending[_-]?key|spend[_-]?key|secret[_-]?key|seed[_-]?phrase|mnemonic|"
    r"mnemonic[_-]?phrase)\b\s*[=:]\s*['\"`]",
    re.IGNORECASE,
)
_MEMO_IDENT_RE = re.compile(r"\bmemo\w*\b", re.IGNORECASE)
_MEMO_HARMLESS_RE = re.compile(
    r"memo[_-]?(hash|hashes|id|ids|ref|refs|reference|references|digest|commitment|"
    r"index|pointer|ptr)\w*",
    re.IGNORECASE,
)


def _memo_leak_in(text: str) -> bool:
    """True if ``text`` mentions a memo in a way that can leak its contents."""
    for match in _MEMO_IDENT_RE.finditer(text):
        if not _MEMO_HARMLESS_RE.fullmatch(match.group(0)):
            return True
    return False


def _assigned_name(file: SourceFile, offset: int) -> str | None:
    prefix = file.text[max(0, offset - 200) : offset]
    match = re.search(
        r"([A-Za-z_]\w*)\s*(?::\s*[^=]{1,40})?=\s*[(\s]*[\"'`]*$", prefix
    )
    return match.group(1) if match else None
_TRANSPARENT_SOURCE_RE = re.compile(
    r"\b(?:Source|Pool|SpendPool|InputPool|SpendSource)::Transparent\b"
    r"|\b(?:from|source|input|spend)[_-]?pool\s*[=:]\s*['\"]transparent['\"]"
    r"|\bpool\s*[=:]\s*['\"]transparent['\"]"
    r"|\bpick_transparent\b",
    re.IGNORECASE,
)


@dataclass
class AddressHit:
    literal: Literal
    token: str
    offset: int
    line: int
    col: int
    info: AddressInfo
    in_uri: bool = False


@dataclass
class UriHit:
    literal: Literal
    text: str
    offset: int
    line: int
    col: int
    request: PaymentRequest


@dataclass
class Symbol:
    """A named constant that holds exactly one address."""

    name: str
    info: AddressInfo
    line: int
    col: int


@dataclass
class FileEvidence:
    file: SourceFile
    addresses: list[AddressHit] = field(default_factory=list)
    uris: list[UriHit] = field(default_factory=list)
    symbols: dict[str, Symbol] = field(default_factory=dict)

    def usages(self, symbol: Symbol) -> Iterator[tuple[int, int]]:
        """Yield (line, col) for each reference to ``symbol`` outside its definition."""
        for match in re.finditer(
            rf"\b{re.escape(symbol.name)}\b", self.file.masked
        ):
            line, col = self.file.line_col(match.start())
            if line == symbol.line:
                continue
            yield line, col


# ---------------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------------


def _finding(rule: Rule, file: SourceFile, line: int, col: int, message: str, detail: str = ""):
    from .engine import Finding  # local import to avoid a cycle

    return Finding(
        rule=rule,
        path=file.rel,
        line=line,
        col=col,
        message=message,
        detail=detail,
        snippet=file.line_text(line).strip()[:160],
    )


def _send_context(file: SourceFile, hit: AddressHit) -> bool:
    ctx = file.context(hit.line, before=2, after=1)
    return bool(_SEND_CALL_RE.search(ctx) or _RECIPIENT_KEY_RE.search(ctx))


def _uid_plausible(token: str, kind: str) -> bool:
    if kind == "transparent":
        return len(token) == 35
    if kind == "sapling":
        return len(token) in range(76, 92)
    if kind == "sprout":
        return len(token) in range(92, 100)
    if kind == "unified":
        return 60 <= len(token) <= 700
    if kind == "unified-viewing-key":
        return 60 <= len(token) <= 700
    if kind == "sapling-viewing-key":
        return len(token) > 100
    return False


def rule_sl001(ev: FileEvidence) -> Iterator:
    rule = RULE_BY_ID["SL001"]
    for hit in ev.addresses:
        if hit.in_uri or not hit.info.is_transparent or not hit.info.ok:
            continue
        if _send_context(ev.file, hit):
            yield _finding(
                rule,
                ev.file,
                hit.line,
                hit.col,
                "payment to a transparent address leaks amount, sender and recipient",
                f"recipient `{_short(hit.token)}` is a {hit.info.kind} address on "
                f"{hit.info.network}. Use a shielded Unified Address or Sapling "
                "address for the recipient, or mark the payment as public in code "
                "review.",
            )


def _send_usage(ev: FileEvidence, symbol: Symbol, after: int = 2) -> tuple[int, int] | None:
    """Pick the most send-like reference to a symbol (call first, then key)."""
    fallback = None
    for line, col in ev.usages(symbol):
        ctx = ev.file.context(line, before=2, after=after)
        if _SEND_CALL_RE.search(ctx):
            return line, col
        if fallback is None and _RECIPIENT_KEY_RE.search(ctx):
            fallback = (line, col)
    return fallback


def rule_sl001_symbols(ev: FileEvidence) -> Iterator:
    rule = RULE_BY_ID["SL001"]
    for symbol in ev.symbols.values():
        if not symbol.info.is_transparent or not symbol.info.ok:
            continue
        usage = _send_usage(ev, symbol, after=2)
        if usage:
            line, col = usage
            yield _finding(
                rule,
                ev.file,
                line,
                col,
                f"payment to a transparent address via `{symbol.name}`",
                f"`{symbol.name}` holds a {symbol.info.kind} address "
                f"({_short(symbol.info.raw)}). The payment will be public: amount, "
                "sender and recipient are all visible on-chain. Use a shielded "
                "Unified Address or Sapling address instead.",
            )


def rule_sl004_symbols(ev: FileEvidence) -> Iterator:
    rule = RULE_BY_ID["SL004"]
    for symbol in ev.symbols.values():
        if not symbol.info.is_transparent or not symbol.info.ok:
            continue
        chosen: tuple[int, int] | None = None
        for line, col in ev.usages(symbol):
            ctx = ev.file.context(line, before=3, after=3)
            if not _memo_leak_in(ctx):
                continue
            if _SEND_CALL_RE.search(ctx):
                chosen = (line, col)
                break
            if chosen is None and _RECIPIENT_KEY_RE.search(ctx):
                chosen = (line, col)
        if chosen is None:
            continue
        line, col = chosen
        yield _finding(
            rule,
            ev.file,
            line,
            col,
            f"memo sent with transparent recipient `{symbol.name}`",
            "memos only exist inside shielded outputs; a memo paired with a "
            "t-address is dropped or leaks off-chain. Pay a shielded address "
            "with the memo, or keep the reference in your database.",
        )


def rule_sl002(ev: FileEvidence) -> Iterator:
    rule = RULE_BY_ID["SL002"]
    for hit in ev.addresses:
        if hit.in_uri or not hit.info.is_transparent or not hit.info.ok:
            continue
        if _send_context(ev.file, hit):
            continue  # SL001 owns this one
        yield _finding(
            rule,
            ev.file,
            hit.line,
            hit.col,
            f"transparent address literal ({hit.info.kind}, {hit.info.network})",
            "every payment to a t-address is public on-chain. Prefer a shielded "
            "Unified Address (`zu1…`) or a Sapling address. If this literal is a "
            "refund/donation endpoint, keep it out of logs and client bundles.",
        )


def rule_sl003(ev: FileEvidence) -> Iterator:
    rule = RULE_BY_ID["SL003"]
    for hit in ev.addresses:
        if not hit.info.is_unified or not hit.info.ok:
            continue
        if hit.info.has_transparent_receiver:
            names = ", ".join(r.name for r in hit.info.receivers)
            yield _finding(
                rule,
                ev.file,
                hit.line,
                hit.col,
                "Unified Address includes a transparent receiver",
                f"receivers: {names}. A sender that cannot do shielded will pick the "
                "transparent receiver, making the payment public. Publish a "
                "shielded-only address (`zu1…` on ZIP 316 rev. 2) instead.",
            )


def rule_sl004(ev: FileEvidence) -> Iterator:
    rule = RULE_BY_ID["SL004"]
    for hit in ev.addresses:
        if hit.in_uri or not hit.info.is_transparent or not hit.info.ok:
            continue
        ctx = ev.file.context(hit.line, before=3, after=3)
        if _memo_leak_in(ctx):
            yield _finding(
                rule,
                ev.file,
                hit.line,
                hit.col,
                "memo attached to a transparent recipient",
                "memos only exist in shielded outputs. Send the memo-bearing payment "
                "to a shielded address, or keep the reference off-chain.",
            )


def rule_sl005(ev: FileEvidence) -> Iterator:
    rule = RULE_BY_ID["SL005"]
    file = ev.file
    for lineno in range(1, len(file.line_starts) + 1):
        masked = file.masked_line(lineno)
        if not masked.strip():
            continue
        if _LOG_RE.search(masked) and _memo_leak_in(masked):
            yield _finding(
                rule,
                file,
                lineno,
                1,
                "memo value passed to a log/print call",
                "memos carry invoice ids and PII; log a salted hash or a random "
                "payment reference instead.",
            )


def rule_sl006(ev: FileEvidence) -> Iterator:
    rule = RULE_BY_ID["SL006"]
    file = ev.file
    for hit in ev.addresses:
        if hit.info.kind in {"unified-viewing-key", "sapling-viewing-key"} and hit.info.ok:
            yield _finding(
                rule,
                file,
                hit.line,
                hit.col,
                f"{'Unified' if hit.info.kind.startswith('unified') else 'Sapling'} "
                "viewing key literal in source",
                "a viewing key decrypts every incoming note (and memo) it covers. "
                "Load it from a secret store at runtime; never commit it.",
            )
    for lineno in range(1, len(file.line_starts) + 1):
        masked = file.masked_line(lineno)
        if not masked.strip():
            continue
        if _LOG_RE.search(masked) and _VIEW_KEY_IDENT_RE.search(masked):
            yield _finding(
                rule,
                file,
                lineno,
                1,
                "viewing key passed to a log/print call",
                "this prints viewing authority to wherever logs are shipped. Redact "
                "the key and log an identifier (account id) instead.",
            )


def rule_sl007(ev: FileEvidence) -> Iterator:
    rule = RULE_BY_ID["SL007"]
    file = ev.file
    for hit in ev.addresses:
        if hit.info.kind == "spending-key":
            yield _finding(
                rule,
                file,
                hit.line,
                hit.col,
                "spending key material committed to source",
                "rotate this key immediately and purge it from git history; read "
                "secrets from a KMS or environment at runtime.",
            )
    for lineno in range(1, len(file.line_starts) + 1):
        masked = file.masked_line(lineno)
        if _SECRET_IDENT_RE.search(masked):
            yield _finding(
                rule,
                file,
                lineno,
                1,
                "spending key / seed assigned from a string literal",
                "keep key material out of source. Use env vars or a secret manager "
                "and rotate anything that has been committed.",
            )


def rule_sl008(ev: FileEvidence) -> Iterator:
    rule = RULE_BY_ID["SL008"]
    file = ev.file
    for lineno in range(1, len(file.line_starts) + 1):
        masked = file.masked_line(lineno)
        if not masked.strip():
            continue  # blank line or pure comment
        # the pool name usually lives inside a string literal, which the lexer
        # blanks in `masked`, so match against the original line instead.
        line = file.line_text(lineno)
        match = _TRANSPARENT_SOURCE_RE.search(line)
        if match:
            yield _finding(
                rule,
                file,
                lineno,
                match.start() + 1,
                "transparent pool selected as the spend source",
                "spending transparent UTXOs publishes the input side of the "
                "transaction. Let the wallet prefer shielded notes (ZIP 315).",
            )


def rule_sl009(ev: FileEvidence) -> Iterator:
    rule = RULE_BY_ID["SL009"]
    for hit in ev.addresses:
        if hit.in_uri or not hit.info.ok:
            continue
        if hit.info.is_address and hit.info.network in {"testnet", "regtest"}:
            yield _finding(
                rule,
                ev.file,
                hit.line,
                hit.col,
                f"{hit.info.network} address literal in source",
                f"`{_short(hit.token)}` is a {hit.info.kind} address on "
                f"{hit.info.network}. Gate test addresses behind a network check or "
                "move them to fixtures.",
            )


def rule_sl010(ev: FileEvidence) -> Iterator:
    rule = RULE_BY_ID["SL010"]
    for hit in ev.uris:
        req = hit.request
        if not req.ok:
            continue  # SL011 owns invalid requests
        transparent = [p for p in req.payments if p.is_transparent]
        if transparent:
            addrs = ", ".join(_short(p.address or "") for p in transparent)
            yield _finding(
                rule,
                ev.file,
                hit.line,
                hit.col,
                "payment request URI targets a transparent address",
                f"recipient(s): {addrs}. Every wallet that honours this URI will "
                "produce a fully public payment. Rebuild the request around a "
                "shielded Unified Address.",
            )


def rule_sl011(ev: FileEvidence) -> Iterator:
    rule = RULE_BY_ID["SL011"]
    for hit in ev.uris:
        req = hit.request
        if req.ok:
            continue
        first = req.errors[0]
        extra = len(req.errors) - 1
        detail = first + (f" (and {extra} more issue{'s' if extra > 1 else ''})" if extra else "")
        yield _finding(
            rule,
            ev.file,
            hit.line,
            hit.col,
            "invalid ZIP 321 payment request",
            detail,
        )


def rule_sl012(ev: FileEvidence) -> Iterator:
    rule = RULE_BY_ID["SL012"]
    file = ev.file
    for lit in file.literals:
        size = len(lit.value.encode("utf-8", "replace"))
        if size <= 512:
            continue
        name = _assigned_name(file, lit.start) or ""
        if "memo" not in name.lower():
            continue
        line, col = file.line_col(lit.start)
        yield _finding(
            rule,
            file,
            line,
            col,
            f"memo literal is {size} bytes (limit 512)",
            "memos are fixed 512-byte fields; longer text is truncated or "
            "rejected. Reference an off-chain record instead.",
        )


def rule_sl013(ev: FileEvidence) -> Iterator:
    rule = RULE_BY_ID["SL013"]
    for hit in ev.addresses:
        if hit.in_uri:
            continue
        if hit.info.kind == "sprout" and hit.info.ok:
            yield _finding(
                rule,
                ev.file,
                hit.line,
                hit.col,
                "Sprout address",
                "Sprout is deprecated and transfers into Sprout are restricted by "
                "ZIP 211. Migrate to Orchard, Sapling or a Unified Address.",
            )


def rule_sl014(ev: FileEvidence) -> Iterator:
    rule = RULE_BY_ID["SL014"]
    for hit in ev.addresses:
        if hit.in_uri or hit.info.ok or not hit.info.errors:
            continue
        if hit.info.kind == "spending-key":
            continue
        if not _uid_plausible(hit.token, hit.info.kind):
            continue
        detail = "; ".join(hit.info.errors[:2])
        yield _finding(
            rule,
            ev.file,
            hit.line,
            hit.col,
            f"address fails validation ({hit.info.kind})",
            detail + ". A transaction to this string is unspendable; re-copy it "
            "from a wallet and validate at the boundary.",
        )


def _short(value: str, width: int = 18) -> str:
    return value if len(value) <= width else value[: width - 1] + "…"


ALL_RULES: list[Callable[[FileEvidence], Iterable]] = [
    rule_sl001,
    rule_sl001_symbols,
    rule_sl004_symbols,
    rule_sl002,
    rule_sl003,
    rule_sl004,
    rule_sl005,
    rule_sl006,
    rule_sl007,
    rule_sl008,
    rule_sl009,
    rule_sl010,
    rule_sl011,
    rule_sl012,
    rule_sl013,
    rule_sl014,
]
