# Changelog

All notable changes to ShieldLint are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and the project adheres to [Semantic Versioning](https://semver.org/).

## [0.1.0] — 2026-10-17

First public release, built for ZECATHON 2026 (Core & Tooling).

### Added

- **Decoders written from the specifications:** Bech32/Bech32m (BIP 173/350),
  Base58Check, **F4Jumble** (ZIP 316) and the full Unified Address / Unified
  Viewing Key encoding, including CompactSize framing, receiver typecodes,
  revision-0 vs revision-2 (`u` / `zu` / `tu`) rules and address expiry metadata.
- **ZIP 321 payment request parser** with parameter indexes, unpadded base64url
  memos, the 512-byte memo limit, amount formatting, `req-` parameters and the
  memo-on-transparent / Sprout rejections.
- **14 privacy rules** (SL001–SL014) covering transparent recipients and
  downgrade receivers, memo and viewing-key exposure, spend-source selection,
  testnet and Sprout addresses, invalid payment URIs, oversized memos and
  malformed addresses.
- **Light dataflow:** named constants that hold an address are tracked, so
  `send_payment(recipient=REFUND_ADDRESS)` is caught across the file.
- **Multi-language lexer:** Python, JS/TS, Rust, Go, Java/Kotlin, C#, C/C++,
  Ruby, PHP, Swift, shells, JSON/YAML/TOML.
- **Output formats:** text, JSON, **SARIF 2.1.0** and GitHub Actions annotations,
  plus `--fail-on` thresholds and `--quiet`.
- **Configuration:** `shieldlint.toml` / JSON, per-rule severity overrides,
  inline `shieldlint: ignore[...]` and file-level disables.
- **CLI helpers:** `shieldlint address` (offline decode) and `shieldlint uri`
  (validate a payment request).
- **Examples:** a deliberately leaky merchant checkout, its fixed twin and a Rust
  payout fixture.
- **CI:** composite `action.yml`, GitHub Actions workflow with SARIF upload, and
  recipes for GitLab CI, pre-commit and Docker.

### Web UI — second pass (2026-10-17)

A full visual rebuild of the eight-page site, deployed to Vercel with the CLI.

- **Floating nav island** that dims, blurs and hides on scroll-down, returns on
  scroll-up, and carries a 2 px scroll-progress hairline.
- **New hero**: a bespoke inline-SVG sentinel-shield "engine" — orbiting dashed
  rings, blinking visor, a sweeping scan beam, caught-signal markers and a live
  findings card — replacing the static terminal screenshot. CSS-only animation,
  disabled under `prefers-reduced-motion`.
- **Motion system**: staggered section reveals, animated stat counters, cached
  scroll-spy in the docs, and a card spotlight — all with a no-JS/no-observer
  fallback that leaves content visible.
- **Layout discipline**: section label rules reduced from 34 px to 14 px, a
  unified 76 px padding rhythm, bento rule grid, "three surfaces" section and a
  giant wordmark footer.
- **Mobile**: single-column at 760 px, 20 px gutters, drawer nav over a scrim with
  body-scroll lock, scrollable tables and code, sticky chip TOC in the docs, and
  zero horizontal overflow at 360/390/768/1024 px.
- **Docs rebuild**: grouped sidebar with scroll-spy, a Zcash concepts primer, a
  "reading a report" guide, Docker and pre-commit sections and next-page cards.
- **Social card** regenerated in the ink/blue identity with the same robot.


### Verified

- 70 tests, including the official `zcash/zcash-test-vectors`: 120 Unified
  Addresses decoded **and re-encoded byte-for-byte**, 80 viewing-key strings,
  8 F4Jumble vectors in both directions plus the 4 MB hashed vector, and every
  valid/invalid ZIP 321 example from the ZIP.
