# Changelog

All notable changes to ShieldLint are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and the project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Accessibility

- **WCAG 2.1 AA contrast on every page.** The mono micro-labels (breadcrumbs,
  scan-panel timings, footer status, footer meta) and the `--muted-2` token were
  raised until an automated pass reported **0 low-contrast samples** on all
  seven routes, at both 1440 px and 390 px.
- **Gap-free heading outline.** Footer column titles and docs-sidebar group
  labels are no longer `<h5>`/`<h4>`; card titles that directly followed the page
  `<h1>` were promoted to `<h2>`. Every page now runs `h1 → h2 → h3` with no
  skipped levels and exactly one `<h1>`.
- Verified keyboard-only: 18-stop tab order, visible focus ring on every stop,
  skip link first, mobile drawer toggles `aria-expanded` and closes on Escape,
  the rules filter reports `aria-pressed`.
- Cross-engine: Chromium, Firefox and WebKit render with **0 console errors and
  0 horizontal overflow**.

### Demo

- **The demo is re-captured from a real display.** Playwright's video recorder
  emits a frame only when the page repaints, which left 745 unique frames in
  120 s (~6 fps) and visible stepping on every scroll. `record_screen.py` now
  captures a kiosk Chromium from Xvfb with `x11grab` at a constant 30 fps
  (28–30 unique fps during motion), `compose_screen.py` assembles the beats and
  emits a timeline, and `mix_voiceover.py` places the narration on it.
- **The demo is narrated.** Eight lines, one per beat, timed so a
  line never starts before its visual cut and no silence runs past ~1.2 s.
  `docs/demo/mix_voiceover.py` trims the TTS tail silence, fits each clip to its
  slot, and re-encodes the picture with a keyframe every 2 s — the recorded
  master had one every ~5.7 s, which made players hang and skip on seek.

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

### Web UI — sixth pass: sentinel, cold (2026-10-17)

The friendly build was rejected in favour of something severe.

- **Graphite, not ceramic.** Plates run #4b5768 → #141a24; the figure is held
  together by a standing rim light on both edges of the helm and a specular
  brow line rather than by brightness.
- **Cut geometry.** The rounded head is replaced with a 12-sided faceted helm,
  a tapered visor, angular pauldrons and bevel facets on every corner.
- **No face.** The two lit eyes are gone; the visor carries a single narrow
  sensor line, corner brackets and a slow scan pass. No beacon, no amber, no
  status dots — blue only, and sparingly.
- Chest crest is etched rather than glowing; indicator notches replace the
  tri-colour column.
- Social card re-rendered from the same SVG.

### Web UI — fifth pass: the sentinel, designed (2026-10-17)

Feedback on the fourth pass was blunt and correct: the figure read as an
unfinished silhouette — "no designs, no colour, not even recognizable".
It is now a designed object.

- **Light ceramic shell** (white → cool grey gradient) against the ink hero, so
  the figure is legible at a glance and no longer reads as a mask.
- **Real face:** two lit instrument eyes that blink together, a gloss-black
  visor, graphite crown plate and jaw, cheek panels, vent stack, side pods,
  collar ring.
- **Colour identity:** brand-blue crest with the ShieldLint Z, a tri-colour
  status column (green / amber / dim), an amber beacon on a stalk, blue rim
  lights on the arms and shoulder arcs.
- **Material detail:** panel seams, bolts, a bright edge highlight, a soft
  contact shadow, and a longer torso so the findings card lands on the chest
  rather than cutting the figure at the waist.
- **Scene:** the flat blue disc is gone; the bloom is off-centre and softer, and
  the dial, arcs and the existing motion carry the depth.
- Social card re-rendered from the same SVG.

### Web UI — fourth pass: the sentinel returns (2026-10-17)

The flat editor panel is gone. The hero is a robot again — drawn as an
engineered artefact rather than a character.

- **New hero figure.** A faceted graphite helmet with a glass sensor slit,
  angular cheek vents and a chest instrument, inside a rotating dial with tick
  marks. CSS animates a scan band inside the visor, a travelling sheen, a
  blinking crown light and a breathing chest lens; `prefers-reduced-motion`
  leaves it still. Generated as vector geometry by `scripts/art/make_sentinel.py`
  (15 KB inline, no raster asset).
- **Interior pages get a spine.** Every sub-page hero is now ink, with a blue
  wash, a masked construction grid and a hairline underline. A `page-facts`
  strip under each title states the concrete numbers (rules, specs, deps).
- **The nav island is readable everywhere.** It was 68 % ink, which turned
  mid-grey over the light interior pages; it is now 90 % ink and 96 % when
  scrolled.
- **Social card follows the hero.** `scripts/art/render_sentinel.py` rasterises the
  same SVG to a transparent PNG and `make_og.py` composites it, so the card can
  never drift from the homepage again.
- Removed the dead editor-panel CSS and its generated hero bitmap path.

### Web UI — third pass: the hero is the tool (2026-10-17)

The homepage hero no longer illustrates the product — it shows it working.

- **New hero artefact.** The right column is now a dark editor caught mid-scan:
  `apps/pay/checkout.py` with a transparent-recipient line (`SL001`) and a
  viewing-key line (`SL006`) flagged in place, a scan beam travelling the file,
  a light orbiting the panel border, and the findings report sliding out
  underneath it (`exit 1`). All of it is HTML/CSS — crisp at any density.
- **Illustration removed.** The generated hero render, its `/hero.webp` route and
  its base64 bundle are gone; page weight drops and nothing is fetched for the
  hero. The robot sentinel and its animation rules are deleted.
- **Chips repositioned** so they read as annotations floating beside the panel
  (`zu1… shielded only`, `t1… flagged`, `offline · 0 network calls`) instead of
  covering the code.
- **Social card redrawn** in the same language: the OG image is now the scan
  panel plus its report, not the old robot.
- **Cleanup:** removed the superseded `scripts/embed_web.py` and the stale
  `web/static/index.html` build it consumed.

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
