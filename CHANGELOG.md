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

### Verified

- 70 tests, including the official `zcash/zcash-test-vectors`: 120 Unified
  Addresses decoded **and re-encoded byte-for-byte**, 80 viewing-key strings,
  8 F4Jumble vectors in both directions plus the 4 MB hashed vector, and every
  valid/invalid ZIP 321 example from the ZIP.
