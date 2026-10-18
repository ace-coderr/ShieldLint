# ShieldLint — ZECATHON 2026 submission

**Track:** Core & Tooling
**One-liner:** Offline static analysis that finds the places where a Zcash
integration leaks money-flow metadata — transparent recipients, memos and
viewing keys in logs, and broken ZIP 316/321 encodings — before the code ships.

Repository: https://github.com/ace-coderr/ShieldLint · Live demo:
https://shieldlint.vercel.app · MIT · Python 3.11+ · no runtime dependencies.

---

## The problem

Zcash privacy is **opt-in and per-transaction**. That makes it a property of
the *integration*, not of the protocol: a wallet can be perfectly shielded and
still leak everything the moment one payout path uses a `t1…` address, one
`logger.info` prints a memo, or one invoice URI attaches a memo to a
transparent recipient.

These bugs share a trait: **they compile, they pass tests, and they are
invisible in code review.** Reviewers look at logic; the leak is in a string
literal. Today the ecosystem has no automated way to ask the only question that
matters at build time: *where can metadata escape this codebase?*

Existing tooling either checks address *syntax* (a regex, at best) or requires
a running wallet. Nothing decodes a Unified Address properly, understands
ZIP 321 semantics, or knows that a memo must never sit next to a t-address.

## What I built

**ShieldLint**, a zero-dependency Python package and CLI with four layers:

1. **A multi-language lexer** (Python, JS/TS, Rust, Go, Java/Kotlin, C#, C/C++,
   Ruby, PHP, Swift, shells, JSON/YAML/TOML). It separates code from comments
   and prose while preserving offsets, and merges Python/C implicit string
   concatenation so keys split across lines are decoded as one value.

2. **Real Zcash decoders, written from the specifications and verified against
   the official vectors:**
   * Base58Check (transparent), Bech32/Bech32m (Sapling, Unified)
   * **F4Jumble**, the ZIP 316 BLAKE2b Feistel permutation
   * **ZIP 316** Unified Address / Unified Viewing Key parsing: CompactSize
     fram­ing, receiver typecodes, revision-0 vs revision-2 (`u` / `zu` / `tu`)
     rules, expiry metadata, unknown and experimental typecodes
   * **ZIP 321** payment requests: full grammar and cross-parameter semantics
     (indexes, unpadded base64url memos, 512-byte limit, amount formatting,
     `req-` parameters, memo-on-transparent, Sprout rejection)

3. **14 explainable rules** (details in `docs/rules.md`), each tied to a
   specification and shipped with a rationale and remediation. Highlights:

   | | |
   |---|---|
   | SL001 | payment to a transparent address — including via a named constant (`recipient=REFUND_ADDRESS`) |
   | SL003 | Unified Address that still carries a transparent receiver (sender can downgrade) |
   | SL004/SL005 | memo attached to a t-address / memo written to logs |
   | SL006/SL007 | viewing-key or spending-key material in source or logs |
   | SL010/SL011 | payment URI that pays a t-address / invalid ZIP 321 request |
   | SL012 | memo over the 512-byte limit |
   | SL014 | malformed address literal (fund-loss bugs) |

4. **Delivery surfaces that fit real workflows:** text output for humans,
   `--format json`, **SARIF 2.1.0** for GitHub code scanning, **`--format
   github`** for inline PR annotations, `--fail-on` thresholds, inline
   suppression (`# shieldlint: ignore[SL002]`), file-level disables, and a
   TOML config with per-rule severity overrides. A composite `action.yml` and
   CI recipes are included.

Plus two offline utilities that are useful on their own:

```bash
shieldlint address zu1…        # decode any address / viewing key, explain receivers
shieldlint uri 'zcash:…'       # validate a payment request against ZIP 321
```

## Live demo (no install)

**https://shieldlint.vercel.app** runs the same Python engine behind a
serverless endpoint — the CLI is the product, the site is a convenience layer
over it.

* **`/scan`** — paste a file or load the bundled leaky/fixed checkout, press
  scan, and read findings that name the rule, the line, the mechanism and the
  fix. Nothing is written server-side.
* **`/address`** — decode any transparent, Sapling or Unified address or
  viewing key: receivers, typecodes, revision, expiry metadata, and whether the
  address can be downgraded to a transparent payment.
* **`/uri`** — validate a ZIP 321 request against the full grammar: parameter
  indexes, base64url memos, the 512-byte limit, `req-` parameters, and
  memo-on-transparent rejection.
* **`/rules`** — all 14 rules with severity, rationale and remediation;
  filterable and searchable.

The site is eight pages, fully static except the three API calls, and makes
**zero third-party requests** — no fonts, no analytics, no CDNs. That is the
same discipline as the scanner: the tool that argues against metadata leakage
should not leak yours.

## Why it is credible

* **Conformance, not vibes.** 72 tests including the official
  `zcash/zcash-test-vectors`: **124 Unified Addresses** decoded **and re-encoded
  to the identical string**, **66 viewing keys** decoded, **14 F4Jumble
  vectors** in both directions (including the 4 MB hashed vector), and every
  valid/invalid ZIP 321 example from the ZIP.
* **It runs on itself.** `shieldlint check shieldlint` is clean, and it is part
  of CI.
* **It catches what the demo plants.** `examples/vulnerable-checkout`
  (a realistic merchant flow) yields 8 errors and 10 warnings; its fixed twin
  `examples/clean-checkout` yields none.
* **Deterministic and offline.** No network, no execution of target code, no
  key derivation. Same tree → same output.

## Mapping to the judging criteria

**Privacy.** The entire product is a privacy oracle for code. The rules encode
ZIP 315/316/321 semantics rather than taste: transparent-recipient detection,
receiver-downgrade detection, memo/URI validity, viewing-key scoping, and
spend-source selection. A finding states the mechanism *and* the consequence —
"this memo is attached to a transparent recipient, so it is dropped or leaks
off-chain" — which is how privacy decisions should be argued in review.

**Usefulness.** This is the check every Zcash integrator needs and none has.
It runs in one line, has no dependencies, and fits CI, pre-commit and code
scanning. The `address` and `uri` utilities are immediately useful even to
teams that never enable the linter. The output is written for the person who
has to fix the bug.

**Execution.** Working end-to-end: reference-verified decoders, 14 rules,
4 output formats, suppression/config, tests, CI workflows, docs, and a demo with
a leaky and a clean codebase. Not a prototype of a decoder that might one day
form the basis of a linter — the linter is here and it is tested.

**Originality.** Existing privacy tooling is either chain analytics (looking at
transactions after the fact) or wallet UX. ShieldLint is the first
*ZIP-aware static analyser*: it is built on the actual Unified Address and
payment-request encodings, including F4Jumble and revision-2 `zu`/`tu`
semantics, which is what makes findings like "this UA still contains a
transparent receiver" possible at all.

## Demo in 60 seconds

```bash
python -m pip install -e .
shieldlint check examples/vulnerable-checkout     # 8 errors, 10 warnings, exit 1
shieldlint check examples/clean-checkout          # no findings, exit 0
shieldlint address zu175e9thzutjjcqe9u3ca0n98msd…  # decodes receivers offline
shieldlint uri 'zcash:t1cN2…?amount=1&memo=b3JkZXI6MQ'   # INVALID: memo on a t-address
```

Full transcript: `docs/demo.txt`.

## Repository map

```
shieldlint/        address.py · f4jumble.py · bech32.py · base58.py · uri.py
                   source.py (lexer) · rules.py · engine.py · output.py · cli.py
tests/             72 tests + vendored official Zcash vectors
examples/          leaky checkout, fixed checkout, Rust payout fixture, config
docs/              rules.md · design.md · ci.md · demo.txt
action.yml, .github/workflows/shieldlint.yml
```

## Status and next steps

Shipped now: the analyser, the rule set, decoders, CLI, three-plus output
formats, CI integration, conformance tests, documentation.

Next, in rough order of value:

1. **Runtime guardrails:** a `shieldlint.verify(address)` library call for
   wallet code to reject transparent recipients at the boundary (same decoders,
   zero extra dependencies).
2. **Policy DSL:** team-specific rules in YAML (e.g. "our payouts must target
   `zu1`/Orchard only").
3. **Deeper analysis:** tree-sitter backends and cross-file symbol resolution to
   reduce the statement-window heuristics to real call-argument resolution.
4. **Baseline & PR bot:** track "privacy debt" over time and comment on pull
   requests with the leak and the suggested fix.
5. **Wallet-config mode:** check a running wallet's ZIP 315 pool policy and IVK
   scoping, not just source.

## Disclosure

All code in this repository was written during the ZECATHON build window and is
MIT licensed. The only third-party material is the MIT-licensed
`zcash/zcash-test-vectors` JSON files, vendored unmodified for conformance
testing (`tests/vectors/README.md`). The implementations were written from the
public specifications: [ZIP 316](https://zips.z.cash/zip-0316),
[ZIP 321](https://zips.z.cash/zip-0321),
[ZIP 315](https://zips.z.cash/zip-0315),
[ZIP 211](https://zips.z.cash/zip-0211), and the Zcash protocol specification.

All repository URLs in `pyproject.toml`, `output.py`, `action.yml` and the
workflows point at https://github.com/ace-coderr/ShieldLint.

## Submission checklist

Done:

- [x] Public repository, MIT `LICENSE`, no placeholder URLs left.
- [x] Live demo deployed (Vercel, serverless Python).
- [x] 72 tests green on Python 3.11 / 3.12 / 3.13; `shieldlint check shieldlint`
      clean; the action runs on this repository's own PRs.
- [x] Everything written inside the ZECATHON build window; third-party material
      is limited to the MIT-licensed `zcash/zcash-test-vectors` JSON files.

Remaining:

- [x] 1:54 demo recorded **with narration** (`demo/`, reproducible): real CLI run on the leaky
      checkout, the browser scanner, the address decoder, a ZIP 321 request
      accepted and then rejected, and the rule index. Captured from a real X
      display at a constant 30 fps (Playwright's own recorder only wrote ~6
      unique frames per second), narrated, and reproducible:
      `demo/record_screen.py` → `demo/compose_screen.py` →
      `demo/mix_voiceover.py`.
- [x] Final read-through of this file for claims that drifted.
- [ ] Submit on the ZECATHON portal before **Oct 28, 2026 23:59 UTC**
      (one submission, Core & Tooling).
