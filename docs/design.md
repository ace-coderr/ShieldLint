# Design

ShieldLint is a static analyser with one opinion: **a Zcash integration should
be able to state, mechanically, where money-flow metadata can escape.** The
design optimises for three things:

1. **Correct decoding.** A linter that guesses whether a string is a t-address
   is worse than no linter. ShieldLint implements ZIP 316 (including F4Jumble),
   Bech32m, Base58Check and ZIP 321 from the specifications and is tested
   against the official vectors.
2. **Explainability.** Every finding names the mechanism ("memo attached to a
   transparent recipient"), the consequence ("the memo is dropped or leaks
   off-chain") and the fix. No opaque scores, no heuristics without a rationale.
3. **Zero friction.** One Python package, no runtime dependencies, no network,
   no wallet, no keys. Drop it in CI in one line.

## Web UI

The site is a first-class surface, not documentation decoration: a reviewer who
has never touched Zcash should be able to answer "what does this catch, and what
does the output mean" without leaving it.

- **Pages** — home, scanner, address decoder, ZIP 321 validator, rule index,
  docs, install. Every route carries the same nav island, footer and type scale.
- **Nav** — a floating capsule that shrinks on scroll, hides on scroll-down and
  returns on scroll-up; on mobile it becomes a full-height drawer over a scrim.
- **Hero** — a bespoke SVG "engine": an orbiting sentinel shield that sweeps a
  scan beam over the Zcash encodings it understands. It is inline SVG, ~4 KB,
  animates with CSS only and freezes under `prefers-reduced-motion`.
- **Motion** — one reveal per section block, counters on the evidence stats,
  staggered findings, scroll-spy in the docs. Nothing moves on its own outside
  the hero, and every animation degrades to a static layout.
- **Type + colour** — ink `#07090d`, paper, one signal blue `#2a5bff`; a serif
  italic is reserved for the hero's last line. Section rules and label chains are
  14 px, never full-width dividers.
- **Mobile** — single column at 760 px, 20 px gutters, tables and code scroll in
  their own containers, docs get a sticky horizontal table of contents.

Build path: `scripts/build_site.py` inlines `web/site/*` and `web/static/*` into
`web/pages.py` and `web/assets.py`. No CDN, no external font, no runtime fetch —
the same bundle serves the Arena preview, `uvicorn` and Vercel.

## Pipeline

```
              ┌──────────────────────────────────────────────────────────┐
  source tree │  discover  →  lex  →  evidence  →  rules  →  report      │  text/json/
  ──────────► │                                                          │  sarif/github
              └──────────────────────────────────────────────────────────┘
```

| Stage | Module | What it does |
|-------|--------|--------------|
| discover | `source.py` | walks paths, filters extensions, skips vendored/build dirs and oversized or binary files |
| lex | `source.py` | per-language scanner that blanks comments and string *contents* while preserving offsets; collects string literals |
| evidence | `engine.py` | decodes every address / key / payment URI found in literals; records named constants that hold addresses |
| rules | `rules.py` | 14 checks over the evidence, each tagged with severity and remediation |
| report | `output.py` | text, JSON, SARIF 2.1.0 or GitHub Actions annotations; exit code from `fail_on` |

### Why the lexer, and not a parser

A parser per language would be more precise but would make the tool a
maintenance burden and a false sense of correctness (half of Zcash code is
generated or embedded in templates). Instead the lexer answers two questions
that matter for these rules:

* *is this text code or prose?* — comments and docstrings are blanked, so a
  documented example address is not reported;
* *what exactly does this literal contain?* — literals keep their raw values
  and file offsets, so a truncated key is decoded as one string even when it is
  split across lines (Python and C implicit concatenation are merged).

Everything else is done on the decoded values, where correctness is cheap to
test.

### The decoders

`address.py` is a from-spec implementation of:

* **Base58Check** for transparent addresses (2-byte version prefixes),
* **Bech32 / Bech32m** (BIP 173/350) for Sapling and Unified encodings,
* **F4Jumble** (ZIP 316) — the 4-round BLAKE2b Feistel permutation that makes a
  Unified Address look random regardless of its receivers,
* **Unified Address / Unified Viewing Key** parsing: CompactSize item framing,
  receiver typecodes, revision-0 vs revision-2 (`u`/`zu`/`tu`) rules, address
  expiry metadata, unknown and experimental typecodes,
* **Sprout** addresses, for completeness and deprecation warnings.

Test vectors are vendored under `tests/vectors/` and exercised by
`tests/test_vectors.py`: 120 Unified Addresses are decoded **and re-encoded to
the exact same string**, 80 viewing-key strings are decoded, and the long-input
F4Jumble vectors (3.2 MB and 4 MB) are checked by hash.

`uri.py` implements ZIP 321 as a strict validator: the ABNF productions
(`paramindex`, `qchar`, base64url without padding), then the cross-parameter
semantics (each index needs an address, `amount`/`req-asset` exclusion,
512-byte memo limit, no memos on transparent recipients, no Sprout, unknown
`req-` parameters invalidate the request).

### Evidence, not regexes-on-lines

`build_evidence()` turns a file into:

```python
FileEvidence(
    addresses = [AddressHit(token, info, line, col, in_uri), …],
    uris      = [UriHit(text, request, line, col), …],
    symbols   = {"REFUND_ADDRESS": Symbol(info, line, col), …},
)
```

Rules consume this model instead of re-scanning text, which keeps them short and
makes their behaviour testable in isolation.

### Light dataflow

Most real code does not inline addresses; it defines constants. When a literal
is exactly one address and is assigned to a name, ShieldLint records a
`Symbol`. Rule functions can then ask for the symbol's usages outside its
definition and inspect the surrounding statement:

```python
REFUND_ADDRESS = "t1cN2…"                       # ← SL002 (literal, risky)

def settle(wallet, amount):
    wallet.send_payment(recipient=REFUND_ADDRESS, amount=amount)
    #                  ↑ SL001: payment to a transparent address
```

This is deliberately shallow: assignments only, same file only, no attribute
tracking, no interprocedural flow. It catches the pattern that matters
(constants passed to send calls) without pretending to be a dataflow engine.

**Statement window.** Rules that need "is this the same payment?" use a small
masked window around the line (2–3 lines before, up to 4 after, whitespace
collapsed). A send call, its recipient and its memo are almost always within
that window; longer, function-spanning analysis is out of scope and documented
as such.

## Precision vs recall

Every heuristic rule fires only when **two independent signals** agree:

| Rule | Signal A | Signal B |
|------|----------|----------|
| SL001 | transparent address (literal or symbol) | send/payout call or recipient key in the statement |
| SL004 | memo identifier | transparent recipient in the statement |
| SL005 | memo identifier (not `memo_hash`/`memo_ref`/…) | logging sink |
| SL006 (code) | viewing-key identifier | logging sink |
| SL012 | literal > 512 bytes | assigned to a memo-ish name |

Pure literal rules (SL002, SL003, SL009, SL013, SL014) have no context
requirement, so they are deterministic. Rules that can be legitimately
triggered (SL002, SL008, SL009) are `warning`; rules whose consequence is
irreversible (SL001, SL004, SL006, SL007, SL010, SL011, SL012) are `error`.

Suppressing false positives is cheap and local (inline directive or config), which
lets the rules err on the side of reporting the leak.

## Security posture

* **Never executes target code.** No imports, no eval, no subprocess on the
  analysed tree.
* **No network.** Nothing is fetched; vector files are vendored.
* **No key material.** The tool recognises key encodings; it never derives,
  decrypts or writes them. Findings quote at most a truncated address prefix.
* **Read-only.** The only file written is the report you ask for with `-o`.
* **Deterministic.** Same tree, same output, sorted by path/line/rule.

## Performance

The scanner jumps from one comment/string construct to the next with a single
regex and keeps positions in a binary-searchable table, so cost scales with the
number of comments and strings rather than with raw characters.

Measured on the [librustzcash](https://github.com/zcash/librustzcash) checkout
(382 files, 17 MB): **~4 seconds**, single-threaded, no cache. The 4 MB
F4Jumble vector is the slowest thing in the test-suite.

## Limitations

These are explicit, because a privacy tool that oversells itself is a liability.

1. **Static, single-file analysis.** No interprocedural flow, no cross-file
   symbols, no reflection, no dependency injection, no runtime values.
2. **Dynamic URIs are skipped.** `f"zcash:{addr}?amount=…"` cannot be validated
   statically; use `shieldlint uri` (or the library) at runtime.
3. **Heuristic sinks.** A send call written as `processor.submit(intent)` may be
   missed; a t-address literal near an unrelated `refund()` call may be
   reported. Suppression and severity overrides exist for this.
4. **No note-level privacy reasoning.** ShieldLint cannot tell whether a
   transaction graph is linkable (timing, amounts, cross-pool migrations) — that
   needs wallet state and chain data.
5. **No protocol-level leaks.** Fee amounts, expiry heights, pool selection at
   the wallet level, light-client queries and mempool exposure are out of scope.
6. **Language coverage.** The lexer knows the languages in `EXTENSIONS`;
   template languages (Vue/Svelte, ERB, JSP) fall back to plain-text handling
   of their file extension and may produce noisier results.
7. **Address validity ≠ consent.** A `zu1…` address is shielded-only by
   construction, but the recipient's wallet may still behave badly. ShieldLint
   checks the encoding, not the counterparty.

## Adding a rule

1. Add a `Rule(...)` entry to `RULES` in `shieldlint/rules.py` with a stable id
   (`SL0NN`), a slug, severity, rationale and references.
2. Write `rule_slNNN(ev: FileEvidence) -> Iterator[Finding]`. Use the evidence
   (`ev.addresses`, `ev.uris`, `ev.symbols`, `ev.usages(symbol)`) and the
   helpers (`_send_context`, `_memo_leak_in`, `_send_usage`).
3. Register it in `ALL_RULES`.
4. Add the rule to `docs/rules.md` with a bad/good example and references.
5. Add tests to `tests/test_rules.py` (a positive and a negative case) and, if
   it decodes something new, a vector test.

Keep the "two signals" discipline: a rule that fires on a single ubiquitous
token will be disabled by users and protect nobody.

## Roadmap

* A small policy-DSL so teams can add rules in YAML without forking;
* tree-sitter backends for TypeScript/Rust to replace window heuristics with
  call-argument resolution;
* cross-file symbol resolution for monorepos;
* a wallet-RPC mode that checks a *running* wallet's configuration (ZIP 315 pool
  policy, IVK scoping) rather than just source;
* GitHub App that comments on pull requests with the specific leak and the
  fixed diff, and tracks "privacy debt" over time.

## Testing

```bash
python -m unittest discover -s tests -t .      # 70 tests
python -m shieldlint check shieldlint            # the tool lints itself
```

The examples directory doubles as an integration test: `examples/vulnerable-
checkout` must produce findings for every rule that applies to code, and
`examples/clean-checkout` must produce none.

Robustness: ShieldLint has been run over the full librustzcash tree (382 Rust
files) and 120 files from the CPython standard library without a crash; as
expected, findings in a real tree concentrate in vendored test vectors, which is
what `exclude` is for.
