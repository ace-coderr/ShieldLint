# ShieldLint

[![CI](https://github.com/ace-coderr/shieldlint/actions/workflows/shieldlint.yml/badge.svg)](https://github.com/ace-coderr/shieldlint/actions/workflows/shieldlint.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](pyproject.toml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

**Offline privacy linting for Zcash software.** Point it at a repository; it
reads every address, viewing key and `zcash:` payment request it can find and
tells you where the integration leaks money-flow metadata — before the code
ships.

Built for **ZECATHON 2026 — Core & Tooling track**. MIT licensed, zero runtime
dependencies, no network access, no keys touched.

**[Try it in the browser →](https://shieldlint.vercel.app)** — scan a file, decode an
address, validate a payment request. Same engine, no install.

```
$ shieldlint check examples/vulnerable-checkout
shieldlint 0.1.0  ·  2 files scanned  ·  8 errors, 10 warnings

examples/vulnerable-checkout/checkout.py
  19:19     warning SL002  transparent address literal (transparent-p2pkh, mainnet)
  24:6      warning SL003  Unified Address includes a transparent receiver
  32:6      error   SL006  Unified viewing key literal in source
                      a viewing key decrypts every incoming note (and memo) it covers.
                      help: docs/rules.md#sl006-viewing-key-exposure
  41:19     error   SL007  spending key material committed to source
  45:6      error   SL012  memo literal is 678 bytes (limit 512)
  65:16     error   SL011  invalid ZIP 321 payment request
                      memo is attached to a transparent recipient; ZIP 321 says a memo
                      requires a shielded (memo-capable) address
  80:19     error   SL001  payment to a transparent address via `REFUND_ADDRESS`
                      The payment will be public: amount, sender and recipient are all
                      visible on-chain. Use a shielded Unified Address instead.
  ...
8 errors, 10 warnings, 0 notes across 2 files   (fail-on=error)
✖ findings at or above the failure threshold
```

*(Full run in [docs/demo.txt](docs/demo.txt).)*

**▶ [Watch the demo](ShieldLint-demo.mp4)** — 1:39, narrated and captioned: the
CLI on a leaky checkout, the browser scanner, the address decoder, a ZIP 321
request accepted and then rejected, and the rule index.

---

## Why this exists

Zcash privacy is **opt-in and per-transaction**, so it is lost in code, not in
cryptography. Three failure modes account for most real leaks:

1. **Transparent recipients.** One `t1…` address in a payout path makes the
   amount, sender and recipient public forever. It compiles, it tests fine, it
   is invisible in review.
2. **Data in the wrong place.** Memos carry invoices and PII; viewing keys
   decrypt an entire account. Both end up in logs and error trackers because
   strings are just strings.
3. **Encoding mistakes.** A truncated address or an invalid ZIP 321 URI is a
   checkout that fails — or worse, funds sent somewhere unspendable.

Privacy has no compile error. ShieldLint is the missing compiler diagnostic:
deterministic, offline, CI-friendly, and explained in terms of the Zcash
specifications rather than vibes.

## Install

```bash
python -m pip install .          # or: pipx install .
shieldlint --version
```

Requires Python 3.11+. No third-party packages at runtime.

Run from a checkout without installing:

```bash
python -m shieldlint check .
```

## Quickstart

```bash
shieldlint check src/                               # lint a tree
shieldlint check . --fail-on warning                # strict CI gate
shieldlint check . --format sarif -o shieldlint.sarif
shieldlint check . --format github                  # Actions annotations
shieldlint rules                                    # explain every rule
shieldlint address u1...                            # decode an address offline
shieldlint uri 'zcash:u1...?amount=0.5&memo=...'    # validate a payment request
```

Exit codes: `0` nothing at/above the threshold, `1` findings, `2` usage/config
error.

## What it catches

| ID | Severity | Check |
|----|----------|-------|
| **SL001** | error | Payment sent to a transparent address (inline literal or named constant) |
| **SL002** | warning | Transparent address hard-coded in source/config |
| **SL003** | warning | Unified Address carries a transparent receiver (senders can downgrade) |
| **SL004** | error | Memo attached to a transparent recipient |
| **SL005** | warning | Memo content passed to a logger/`print` |
| **SL006** | error | Viewing key (UFVK/UIVK/IVK/OVK/extfvk) in source or logs |
| **SL007** | error | Spending key / seed material committed to source |
| **SL008** | warning | Transparent pool selected as the spend source (ZIP 315) |
| **SL009** | warning | Testnet/regtest address in production code |
| **SL010** | error | `zcash:` payment request URI pays a transparent address |
| **SL011** | error | Invalid ZIP 321 payment request (memo on t-addr, bad amount, duplicate params, …) |
| **SL012** | error | Memo literal over the 512-byte limit |
| **SL013** | warning | Sprout address (deprecated, ZIP 211) |
| **SL014** | warning | Malformed address literal (bad checksum/length) |

Every rule documents its rationale, a bad example, a fixed example and
references in **[docs/rules.md](docs/rules.md)**.

## Under the hood

ShieldLint is three layers, all implemented from the specifications:

1. **A small lexer per language** (Python, JS/TS, Rust, Go, Java/Kotlin, C#,
   C/C++, Ruby, PHP, Swift, shells, JSON/YAML/TOML). It masks comments and
   string bodies but keeps offsets, so rules can tell code from prose and still
   read the exact literals. Python/C implicit string concatenation is merged so
   keys split over several lines are still decoded as one value.
2. **Real Zcash decoders.** Bech32/Bech32m, Base58Check, **F4Jumble** and the
   full **ZIP 316** Unified Address / Unified Viewing Key encoding, plus a
   strict **ZIP 321** payment-request parser. The decoder understands receiver
   typecodes, `zu`/`tu` revision-2 rules, expiry metadata and network prefixes
   — and it is validated against the official Zcash test vectors.
3. **Rules with light dataflow.** When an address literal is assigned to a
   named constant, ShieldLint remembers it (`REFUND_ADDRESS = "t1…"`) and
   follows simple references, so `send_payment(recipient=REFUND_ADDRESS)` is
   caught even though the literal is hundreds of lines away.

Architecture, threat model and limitations: **[docs/design.md](docs/design.md)**.

## Conformance

The decoder is not a best-effort regex. The test-suite (72 tests) includes the
official [Zcash test vectors](https://github.com/zcash/zcash-test-vectors):

* 14 F4Jumble vectors, forward and inverse, including the 4 MB hashed vector;
* 124 Unified Address vectors (revision 0 and revision 2) decoded **and**
  re-encoded byte-for-byte, including expiry metadata and unknown typecodes;
* 80 Unified Viewing Key strings (UFVK/UIVK, revision 0 and 2);
* every valid and invalid ZIP 321 example from the ZIP itself.

```bash
python -m unittest discover -s tests -t .
```

## Configuration

`shieldlint.toml` (auto-discovered) or JSON via `--config`:

```toml
[shieldlint]
fail_on   = "error"                 # error | warning | note | never
exclude   = ["tests/fixtures/**", "vendor/**"]
include_docs = false                # also scan Markdown/text
disable   = ["SL002"]               # switch rules off entirely

[shieldlint.severity]
SL008 = "note"                      # override a rule's severity
```

Inline suppression works in any comment style:

```python
REFUND = "t1…"                 # shieldlint: ignore[SL002]
# shieldlint: disable-file     (whole file)
```

`shieldlint: ignore` also covers the following line, which suits both
end-of-line and preceding-line comments.

## CI

GitHub Actions with code scanning (SARIF):

```yaml
- run: pipx install .
- run: shieldlint check src --format sarif -o shieldlint.sarif --fail-on error
- uses: github/codeql-action/upload-sarif@v3
  with:
    sarif_file: shieldlint.sarif
```

There is also a composite action in [`action.yml`](action.yml) and ready-made
workflows in [`docs/ci.md`](docs/ci.md) (GitHub, GitLab, pre-commit).

## What it deliberately does not do

ShieldLint is static analysis, not a wallet auditor. It does not see cross-file
call graphs, does not evaluate dynamic URIs, does not inspect notes or prove
that a transaction is unlinkable. It catches the leaks that are visible in the
source — the ones that account for most shipped bugs — and says so in
[docs/design.md](docs/design.md#limitations). Treat a clean run as a floor, not
a ceiling.

## Project layout

```
shieldlint/          the package (address, f4jumble, uri, source, rules, engine, cli)
tests/               unit + conformance tests, vendored Zcash vectors
examples/            a deliberately leaky checkout, its fixed twin, a Rust fixture
docs/                rules.md, design.md, ci.md, demo.txt
action.yml           composite GitHub Action
```

## License

MIT. Test vectors are vendored from
[zcash/zcash-test-vectors](https://github.com/zcash/zcash-test-vectors) under
the MIT license; see [tests/vectors/README.md](tests/vectors/README.md).
