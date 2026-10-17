# Rules

ShieldLint ships 14 rules. Each is tied to a public Zcash specification or
privacy recommendation, and each finding carries a rationale you can paste into
a code review.

**Severities**

| Level | Meaning | Default effect on CI |
|-------|---------|----------------------|
| `error` | A privacy or correctness defect that will leak or lose value | fails (`fail_on = "error"`) |
| `warning` | A risky pattern that is sometimes legitimate | reported |
| `note` | Informational (only via severity overrides) | reported |

**Suppressing a finding**

```python
REFUND = "t1…"                # shieldlint: ignore[SL002]
# shieldlint: disable-file    (disables the whole file)
```

`shieldlint: ignore` without a bracket disables every rule for that line and the
next one. Rules can also be disabled or re-graded in `shieldlint.toml`.

---

## SL001 transparent-recipient

**Severity: error** — *Payment sent to a transparent address.*

**What it catches.** A send/payout call whose recipient is a transparent
address — either a `t1`/`t3`/`tm`/`t2` literal inline, or a named constant that
holds one (`REFUND_ADDRESS = "t1…"`, later passed as `recipient=`).

**Why it matters.** Transparent addresses publish the amount, the sender and
the recipient on the public chain. A shielded wallet that pays a t-address
leaks the entire payment, and no later action can undo it.

**Bad**

```python
REFUND_ADDRESS = "t1cN2ZVWzWcVRrnfeQzmkpLhzQ4dYRv8yRY"
wallet.send_payment(recipient=REFUND_ADDRESS, amount_zats=amount)
```

**Good**

```python
SHIELDED_UA = "zu1…"          # Orchard + Sapling receivers, no transparent one
wallet.send_payment(recipient=SHIELDED_UA, amount_zats=amount)
```

**If transparency is unavoidable** — an exchange deposit, a legacy payout
rail — record the decision in code (a comment and a test), keep the address out
of logs, and make sure the UI tells the user the payment is public.

References: [ZIP 316](https://zips.z.cash/zip-0316),
[ZIP 315](https://zips.z.cash/zip-0315).

---

## SL002 transparent-address-literal

**Severity: warning** — *Transparent address literal in source.*

**What it catches.** Any `t1`/`t3`/`tm`/`t2` literal that is not part of a
detected send call: configuration files, defaults, fixtures, docstrings,
constants.

**Why it matters.** A t-address in source becomes a permanent, publicly
linkable endpoint. Every payment to it is visible, and version control links
the code (and its authors) to the address. It also tends to be copy-pasted into
clients, logs and support tickets.

**Bad**

```yaml
merchant:
  refund_address: "t1cN2ZVWzWcVRrnfeQzmkpLhzQ4dYRv8yRY"
```

**Good**

```yaml
merchant:
  refund_address: "zu1…"       # shielded-only Unified Address
```

If the transparent address is required (e.g. a legacy processor), keep it in a
secret store or an environment variable, rotate it per deployment, and never
log or bundle it.

---

## SL003 ua-transparent-receiver

**Severity: warning** — *Unified Address carries a transparent receiver.*

**What it catches.** A Unified Address whose receiver list includes typecode
`0x00` (P2PKH) or `0x01` (P2SH).

**Why it matters.** A Unified Address lets the *sender* choose the best receiver
it supports. If a transparent receiver is present, a transparent-only wallet
picks it and the payment becomes public — without the recipient ever seeing a
t-address. ZIP 316 revision 2 added the `zu` prefix precisely to forbid this.

**Bad**

```
u1pg2aaph7jp8rpf6yhsza25…    # u1: P2PKH + Sapling + Orchard receivers
```

**Good**

```
zu175e9thzutjjcqe9u3ca0n9…   # zu1: shielded-only, revision 2
```

**Nuance.** A `u1…`/`tu1…` address is not *always* wrong — but publishing one
as your payment address tells every counterparty "transparent is fine". If you
need the compatibility escape hatch, keep it internal and hand it out only to
counterparties you know cannot do shielded.

References: [ZIP 316 — Revisions](https://zips.z.cash/zip-0316#revisions).

---

## SL004 memo-to-transparent

**Severity: error** — *Memo attached to a transparent recipient.*

**What it catches.** A memo value in the same statement as a transparent
recipient — `send_payment(recipient=REFUND, memo=…)`, `{"address": "t1…",
"memo": …}`, or a memo literal next to a t-address constant.

**Why it matters.** Memos exist only inside shielded outputs. A memo aimed at a
t-address is silently dropped, or smuggled through an off-chain field — which
means invoice references stop matching. ZIP 321 goes further: it declares such
payment requests *invalid*, so wallets must reject them.

**Bad**

```python
wallet.send_payment(recipient=MERCHANT_TADDR, memo=f"order:{order.id}")
```

**Good**

```python
wallet.send_payment(recipient=SHIELDED_UA, memo=f"order:{order.id}")
```

For transparent rails, keep the reference in your own database and put only a
short random tag in whatever field the payment provider offers.

References: [ZIP 321](https://zips.z.cash/zip-0321).

---

## SL005 memo-exposure

**Severity: warning** — *Memo content passed to a logger.*

**What it catches.** A line that both mentions a memo and calls a logging sink
(`print`, `console.log`, `logger.*`, `println!`, `tracing::*`, `System.out`,
`puts`, …).

**Why it matters.** Memos routinely carry invoices, order ids, emails and
free-form notes. Logs are replicated, shipped to third parties and rarely
expire — a memo in a log is a permanent disclosure. Error trackers are worse:
they often include request bodies.

**Bad**

```python
logger.info("settled order=%s memo=%s", order.id, order.memo)
```

**Good**

```python
memo_ref = hashlib.sha256(order.memo.encode()).hexdigest()[:16]
logger.info("settled order=%s memo_ref=%s", order.id, memo_ref)
```

ShieldLint understands the fix: identifiers such as `memo_hash`, `memo_ref`,
`memo_id` and `memo_digest` do not trigger the rule.

---

## SL006 viewing-key-exposure

**Severity: error** — *Viewing key material in source or logs.*

**What it catches.** Unified/Sapling viewing keys (`uview1…`, `uivk1…`,
`uvf1…`, `uvi1…`, `zxviews1…`) as literals, and identifiers such as `fvk`,
`ufvk`, `ivk`, `ovk` or `viewing_key` flowing into a log call — including
inside f-strings and template literals.

**Why it matters.** A full viewing key decrypts every incoming note and every
memo for the account it covers; an incoming viewing key reveals all incoming
payments. Leaking one deanonymizes the wallet without ever touching the
spending key — and unlike a spending key, viewing keys are often treated as
"read-only" and handled carelessly.

**Bad**

```python
logger.debug(f"watch-only key {OUR_VIEW_KEY}")
```

**Good**

```python
logger.debug("watching account %s", account.id)   # id, never the key
```

Load viewing keys at runtime from a secret store, scope them to one account,
and redact them from exception handlers and HTTP clients.

References: [ZIP 316 — Unified Viewing Keys](https://zips.z.cash/zip-0316).

---

## SL007 spending-key-material

**Severity: error** — *Spending key material committed to source.*

**What it catches.** `secret-extended-key-main1…`/`…-test1…` literals, and
string assignments to identifiers like `spending_key`, `secret_key`,
`seed_phrase` or `mnemonic`.

**Why it matters.** Anyone who can read the repository can spend the funds.
Removing the line is not enough: the value lives on in git history, CI logs,
caches and forks.

**Bad**

```python
HOT_WALLET_KEY = "secret-extended-key-main1…"
```

**Good**

```python
HOT_WALLET_KEY = os.environ["ZEC_HOT_WALLET_KEY"]   # from a KMS/secret store
```

Rotate the key *first*, then purge history (`git filter-repo`), then move
automated payouts to a dedicated account with limited funds.

---

## SL008 transparent-spend-source

**Severity: warning** — *Transparent funds selected as the spend source.*

**What it catches.** Explicit pool selection, e.g. `Source::Transparent`,
`pool: "transparent"`, `from_pool="transparent"`, `pick_transparent`.

**Why it matters.** Spending a transparent UTXO publishes the input side of the
transaction and links your transparent balance to the recipient. ZIP 315
recommends spending shielded notes whenever they are available; most wallets
implement a preference order and only fall back to transparent.

**Bad**

```rust
let source = Source::Transparent;
```

**Good**

```rust
let source = Source::WalletDefault;   // shielded-first, per ZIP 315
```

Keep transparent spending behind an explicit, user-visible choice (e.g. "pay
from shielded balance" unchecked).

References: [ZIP 315](https://zips.z.cash/zip-0315).

---

## SL009 testnet-address-in-source

**Severity: warning** — *Testnet or regtest address in source.*

**What it catches.** Valid addresses on testnet or regtest networks —
`tm…`/`t2…`, `ztestsapling1…`, `utest1…`, `zutest1…`, `tutest1…`, `uregtest1…`.

**Why it matters.** Shipping a test address is either dead code or a
misconfiguration. If a production path ever uses it, real value goes to an
address nobody controls (or to a faucet-funded script). It also leaks the shape
of your test infrastructure.

**Good practice.** Gate addresses on an explicit network switch, and keep
fixtures in a directory excluded from the lint run:

```toml
[shieldlint]
exclude = ["tests/fixtures/**"]
```

---

## SL010 payment-uri-to-transparent

**Severity: error** — *Payment request URI pays a transparent address.*

**What it catches.** A static `zcash:` URI that parses as valid ZIP 321 but
contains a transparent recipient.

**Why it matters.** A payment URI is a promise about how the payment will
happen. If it points at a t-address, every wallet that honours it produces a
fully public payment, and the invoice amount is public too. For merchants this
also destroys the privacy of customers paying from shielded funds.

**Bad**

```
zcash:t1cN2ZVWzWcVRrnfeQzmkpLhzQ4dYRv8yRY?amount=0.25&message=refund
```

**Good**

```
zcash:zu175e9thzutjjcqe9u3ca0n98msd…?amount=0.25&memo=b3JkZXI6MjI5MQ
```

Dynamic URIs (f-strings, template literals) are not validated; build them from
a shielded address constant and validate at runtime with `shieldlint uri`.

References: [ZIP 321](https://zips.z.cash/zip-0321).

---

## SL011 invalid-payment-uri

**Severity: error** — *Invalid ZIP 321 payment request.*

**What it catches.** A static `zcash:` URI that fails the ZIP 321 grammar or
semantics. Examples:

* a memo attached to a transparent recipient;
* `memo=` containing `+`, `/` or `=` (base64url, unpadded only);
* a memo longer than 512 bytes;
* more than 8 fractional digits, grouping separators, `.5` or `5.`;
* duplicate parameters, `address.0`, or a parameter index without an address;
* unknown `req-` parameters (the whole URI must be rejected);
* `amount` and `req-asset` at the same index;
* percent-encoding outside `label`/`message`/other free-text parameters;
* `//` after `zcash:`, or a Sprout recipient.

**Why it matters.** Conformant wallets must reject these requests, so the
failure lands on the customer at checkout — or the request "works" in a lenient
wallet and silently drops the memo, breaking reconciliation.

**Bad**

```
zcash:t1cN2ZVWzWcVRrnfeQzmkpLhzQ4dYRv8yRY?amount=1&memo=b3JkZXI6MQ
```

**Good**

```
zcash:zu175e9thzutjjcqe9u3ca0n98msd…?amount=1&memo=b3JkZXI6MQ
```

References: [ZIP 321](https://zips.z.cash/zip-0321).

---

## SL012 memo-too-long

**Severity: error** — *Memo exceeds the 512-byte limit.*

**What it catches.** A string literal assigned to a memo-ish name that is
longer than 512 bytes after implicit concatenation.

**Why it matters.** Zcash memos are fixed-size 512-byte fields. Longer text is
truncated by wallets or rejected, which breaks invoice matching and can
silently lose structured data. It also pushes PII into the one field every
counterparty can read.

**Bad**

```python
MEMO_SETTLEMENT_NOTE = "order=…; customer=…; courier=…; notes=…"  # 700 bytes
```

**Good**

```python
memo = f"order:{order.id}"        # reference an off-chain record
```

Put the payload in your database (encrypted), and keep a short, stable
reference in the memo.

---

## SL013 sprout-address

**Severity: warning** — *Sprout address.*

**What it catches.** A `zc…`/`zt…` Sprout address.

**Why it matters.** Sprout is deprecated. Transfers into Sprout are restricted
by ZIP 211, and most modern wallets cannot send there at all — so a Sprout
address in a payout path is likely a dead end.

**Good.** Migrate to Orchard, Sapling, or a Unified Address; if you must keep
legacy support, isolate it behind a feature flag and tell the user.

References: [ZIP 211](https://zips.z.cash/zip-0211).

---

## SL014 malformed-address

**Severity: warning** — *Malformed address literal.*

**What it catches.** A string that looks like a Zcash address (correct prefix
and plausible length) but fails decoding — Base58Check failure, wrong payload
length, unknown version bytes, bad Bech32m checksum, or a `zu` address that
contains a transparent receiver.

**Why it matters.** This is not a privacy bug, it is a fund-loss bug. A
truncated or mistyped address is still accepted by the network as an output;
the value lands somewhere nobody can spend.

**Bad**

```yaml
typo_address: "t1cN2ZVWzWcVRrnfeQzmkpLhzQ4dYRv8yRZ"   # last char changed
```

**Good.** Re-copy from a wallet and validate at the boundary:

```bash
shieldlint address "$ADDRESS"     # exit code 1 when invalid
```

---

## Adding your own rule

Rules live in `shieldlint/rules.py`. A rule is a `Rule` (id, slug, severity,
title, summary, rationale, remediation, references) plus a function that takes
`FileEvidence` and yields findings. See
[design.md](design.md#adding-a-rule) for the walkthrough and the evidence model.
