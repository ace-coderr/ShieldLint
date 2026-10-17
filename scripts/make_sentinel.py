#!/usr/bin/env python3
"""Generate the hero sentinel (inline SVG) and inject it into index.html.

    python scripts/make_sentinel.py

Cold variant: graphite plates with cut bevels, a tapered visor holding a narrow
sensor line instead of eyes, no beacon, no amber. The figure is held together by
engineering detail — rim lights, hairline seams, bolt rows — so it still reads as
a machine at a glance while staying severe.

Motion is CSS (`.sent-*` in app.css). Writes `web/site/_sentinel.svg` and
replaces the content between the sentinel markers in `web/site/index.html`.
"""

from __future__ import annotations

import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "web" / "site" / "index.html"

BLUE = "#2a5bff"
BLUE_SOFT = "#8fb0ff"


def dial(cx: float, cy: float, r: float) -> str:
    out = []
    for deg in range(0, 360, 5):
        a = math.radians(deg - 90)
        major = deg % 45 == 0
        inner = r - (18 if major else 8)
        x1, y1 = cx + math.cos(a) * inner, cy + math.sin(a) * inner
        x2, y2 = cx + math.cos(a) * r, cy + math.sin(a) * r
        op = ".40" if major else ".16"
        w = "1.6" if major else "1"
        out.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                   f'stroke="rgba(214,228,255,{op})" stroke-width="{w}" stroke-linecap="round"/>')
    return "\n      ".join(out)


# faceted helm, clockwise from the crown
HEAD = (
    "M320 116 L394 142 L428 198 L434 264 L422 332 L394 378 L346 406 "
    "L294 406 L246 378 L218 332 L206 264 L212 198 L246 142 Z"
)
# tapered visor
VISOR = "M248 230 L392 230 L404 252 L396 300 L320 320 L244 300 L236 252 Z"
TORSO = "M246 414 L394 414 L470 700 L170 700 Z"


def svg() -> str:
    cx, cy = 320.0, 340.0
    return f'''<svg class="sent" viewBox="24 24 592 660" role="img"
     aria-label="ShieldLint sentinel: a graphite machine with a narrow sensor visor inside an instrument dial">
  <defs>
    <linearGradient id="s-plate" x1="0.1" y1="0" x2="0.88" y2="1">
      <stop offset="0" stop-color="#4b5768"/>
      <stop offset=".26" stop-color="#333d4c"/>
      <stop offset=".64" stop-color="#242d3a"/>
      <stop offset="1" stop-color="#141a24"/>
    </linearGradient>
    <linearGradient id="s-plate-l" x1="0" y1="1" x2="1" y2="0">
      <stop offset="0" stop-color="#1a222d"/>
      <stop offset=".5" stop-color="#313c4b"/>
      <stop offset="1" stop-color="#546173"/>
    </linearGradient>
    <linearGradient id="s-plate-d" x1="0" y1="0" x2="0.7" y2="1">
      <stop offset="0" stop-color="#1d2531"/>
      <stop offset="1" stop-color="#0c1119"/>
    </linearGradient>
    <linearGradient id="s-visor" x1="0.1" y1="0" x2="0.8" y2="1">
      <stop offset="0" stop-color="#101a29"/>
      <stop offset=".5" stop-color="#05080e"/>
      <stop offset="1" stop-color="#010306"/>
    </linearGradient>
    <linearGradient id="s-rim" x1="0" y1="0.15" x2="1" y2="0.85">
      <stop offset="0" stop-color="rgba(255,255,255,.95)"/>
      <stop offset=".32" stop-color="rgba(196,214,255,.42)"/>
      <stop offset=".6" stop-color="rgba(127,157,255,.10)"/>
      <stop offset="1" stop-color="rgba(127,157,255,.55)"/>
    </linearGradient>
    <radialGradient id="s-glow" cx="0.5" cy="0.26" r="0.7">
      <stop offset="0" stop-color="{BLUE}" stop-opacity=".30"/>
      <stop offset=".52" stop-color="{BLUE}" stop-opacity=".08"/>
      <stop offset="1" stop-color="{BLUE}" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="s-fade" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#fff"/>
      <stop offset=".76" stop-color="#fff"/>
      <stop offset="1" stop-color="#000"/>
    </linearGradient>
    <mask id="s-mask"><rect x="0" y="0" width="640" height="720" fill="url(#s-fade)"/></mask>
    <clipPath id="s-visor-clip"><path d="{VISOR}"/></clipPath>
    <clipPath id="s-head-clip"><path d="{HEAD}"/></clipPath>
    <filter id="s-b12" x="-60%" y="-60%" width="220%" height="220%">
      <feGaussianBlur stdDeviation="12"/>
    </filter>
    <filter id="s-b4" x="-60%" y="-60%" width="220%" height="220%">
      <feGaussianBlur stdDeviation="4"/>
    </filter>
    <filter id="s-drop" x="-30%" y="-30%" width="160%" height="170%">
      <feDropShadow dx="0" dy="20" stdDeviation="20" flood-color="#04070c" flood-opacity=".6"/>
    </filter>
  </defs>

  <ellipse cx="368" cy="214" rx="296" ry="256" fill="url(#s-glow)" opacity=".85"/>

  <g class="sent-dial">
    <circle cx="{cx}" cy="{cy}" r="272" fill="none" stroke="rgba(255,255,255,.09)"/>
    <circle cx="{cx}" cy="{cy}" r="238" fill="none" stroke="rgba(255,255,255,.055)"/>
    <g>{dial(cx, cy, 272)}</g>
  </g>
  <g class="sent-dial-b">
    <path d="M{cx} {cy - 205} A 205 205 0 0 1 {cx + 205} {cy}" fill="none"
          stroke="rgba(143,176,255,.5)" stroke-width="2.2" stroke-linecap="round"/>
    <path d="M{cx} {cy + 205} A 205 205 0 0 1 {cx - 205} {cy}" fill="none"
          stroke="rgba(143,176,255,.16)" stroke-width="2.2" stroke-linecap="round"/>
  </g>

  <g mask="url(#s-mask)" filter="url(#s-drop)">
    <!-- ========================================== pauldrons (cut) -->
    <path d="M244 420 L188 434 L154 492 L146 566 L172 596 L214 604 L250 486 Z"
          fill="url(#s-plate-l)" stroke="rgba(255,255,255,.10)" stroke-width="1.5"/>
    <path d="M396 420 L452 434 L486 492 L494 566 L468 596 L426 604 L390 486 Z"
          fill="url(#s-plate-d)" stroke="rgba(255,255,255,.08)" stroke-width="1.5"/>
    <path d="M160 470 L206 452" stroke="rgba(190,212,255,.55)" stroke-width="1.8"/>
    <path d="M480 470 L434 452" stroke="rgba(143,176,255,.28)" stroke-width="1.8"/>
    <path d="M158 540 L204 540 M160 566 L206 566" stroke="rgba(255,255,255,.10)" stroke-width="1.4"/>

    <!-- ================================================ torso -->
    <path d="{TORSO}" fill="url(#s-plate)" stroke="rgba(255,255,255,.12)" stroke-width="1.6"/>
    <path d="M246 414 L394 414" stroke="rgba(255,255,255,.26)" stroke-width="1.4"/>
    <!-- chest plate -->
    <path d="M272 446 L368 446 L392 560 L248 560 Z" fill="url(#s-plate-d)"
          stroke="rgba(255,255,255,.10)" stroke-width="1.4"/>
    <path d="M272 446 L368 446" stroke="rgba(190,212,255,.35)" stroke-width="1.4"/>
    <!-- etched seams -->
    <path d="M262 456 L238 620" stroke="rgba(255,255,255,.08)" stroke-width="1.2"/>
    <path d="M378 456 L402 620" stroke="rgba(255,255,255,.06)" stroke-width="1.2"/>
    <path d="M248 610 L392 610" stroke="rgba(255,255,255,.07)" stroke-width="1.2"/>

    <!-- crest: etched, not glowing -->
    <g class="sent-crest">
      <path d="M320 466 L346 475 L346 496 C346 514 335 525 320 532 C305 525 294 514 294 496 L294 475 Z"
            fill="rgba(10,16,24,.85)" stroke="{BLUE_SOFT}" stroke-width="2"/>
      <path d="M309 483 h22 l-22 20 h22" fill="none" stroke="{BLUE_SOFT}" stroke-width="2.4"
            stroke-linejoin="round" opacity=".95"/>
    </g>
    <!-- indicator notches -->
    <g fill="{BLUE_SOFT}">
      <rect x="258" y="504" width="14" height="3" rx="1.5" opacity=".85"/>
      <rect x="258" y="516" width="14" height="3" rx="1.5" opacity=".45"/>
      <rect x="258" y="528" width="14" height="3" rx="1.5" opacity=".20"/>
    </g>
    <text x="286" y="640" font-family="ui-monospace, Menlo, monospace" font-size="9"
          letter-spacing="2.6" fill="rgba(214,228,255,.22)">SL-01</text>
    <text x="346" y="640" font-family="ui-monospace, Menlo, monospace" font-size="9"
          letter-spacing="2.6" fill="rgba(214,228,255,.12)">SENTINEL</text>

    <!-- ================================================= neck -->
    <path d="M292 392 L348 392 L352 424 L288 424 Z" fill="#0a0e15"/>
    <path d="M292 400 L348 400 M290 410 L350 410" stroke="rgba(255,255,255,.12)"/>
    <ellipse cx="320" cy="424" rx="74" ry="14" fill="url(#s-plate-d)"
             stroke="rgba(143,176,255,.30)"/>

    <!-- ================================================= helm -->
    <path d="{HEAD}" fill="url(#s-plate)" stroke="rgba(255,255,255,.16)" stroke-width="1.6"/>
    <path d="{HEAD}" fill="none" stroke="url(#s-rim)" stroke-width="2.2"/>
    <path d="M206 264 L212 198 L246 142" fill="none" stroke="#eaf1ff" stroke-opacity=".75"
          stroke-width="2.4" stroke-linecap="round"/>
    <path d="M434 264 L428 198 L394 142" fill="none" stroke="rgba(143,176,255,.55)"
          stroke-width="2" stroke-linecap="round"/>

    <!-- crown facet + bevels -->
    <path d="M246 142 L320 116 L394 142 L360 168 L280 168 Z" fill="rgba(255,255,255,.05)"/>
    <path d="M280 168 L360 168 M246 142 L280 168 M394 142 L360 168"
          stroke="rgba(255,255,255,.13)" stroke-width="1.2"/>
    <path d="M212 198 L246 142 L280 168 L236 230 L220 252 L206 264 Z" fill="rgba(255,255,255,.02)"/>
    <path d="M428 198 L394 142 L360 168 L404 230 L420 252 L434 264 Z" fill="rgba(0,0,0,.34)"/>
    <path d="M206 264 L220 252 L236 252 L222 332 Z" fill="rgba(0,0,0,.26)"/>
    <path d="M434 264 L420 252 L404 252 L418 332 Z" fill="rgba(0,0,0,.40)"/>
    <path d="M222 332 L248 378 L246 348 Z" fill="rgba(0,0,0,.22)"/>
    <path d="M418 332 L392 378 L394 348 Z" fill="rgba(0,0,0,.34)"/>

    <!-- brow block -->
    <path d="M232 200 L408 200 L416 222 L224 222 Z" fill="#111821"
          stroke="rgba(255,255,255,.12)" stroke-width="1.2"/>
    <path d="M232 200 L408 200" stroke="rgba(232,240,255,.55)" stroke-width="1.6"/>

    <!-- =============================================== visor -->
    <path d="{VISOR}" fill="url(#s-visor)" stroke="rgba(255,255,255,.18)" stroke-width="1.8"/>
    <g clip-path="url(#s-visor-clip)">
      <ellipse cx="300" cy="236" rx="86" ry="28" fill="{BLUE}" opacity=".18" filter="url(#s-b12)"/>
      <!-- narrow sensor line, the only light -->
      <path class="sent-sensor" d="M262 268 h116" stroke="#cfe0ff" stroke-width="2.2"
            stroke-linecap="round" opacity=".85"/>
      <path d="M262 268 h116" stroke="#cfe0ff" stroke-width="6" opacity=".12"
            filter="url(#s-b4)"/>
      <!-- scan pass inside the visor -->
      <rect class="sent-scanline" x="236" y="230" width="168" height="18" fill="#bcd2ff"
            opacity=".10" filter="url(#s-b4)"/>
      <path d="M246 288 h148" stroke="rgba(255,255,255,.07)"/>
      <!-- corner brackets, instrument detail -->
      <path d="M250 240 v-6 h8 M390 234 h-8 v6" stroke="rgba(190,212,255,.45)"
            stroke-width="1.6" fill="none"/>
      <path d="M250 292 v6 h8 M382 298 h8 v-6" stroke="rgba(190,212,255,.28)"
            stroke-width="1.6" fill="none"/>
    </g>
    <path d="M252 218 L388 218" stroke="rgba(255,255,255,.30)" stroke-width="1.4"
          clip-path="url(#s-visor-clip)"/>

    <!-- cheek vents -->
    <g stroke="rgba(214,228,255,.26)" stroke-width="2" stroke-linecap="round">
      <path d="M224 256 h22 M224 272 h22 M224 288 h22"/>
      <path d="M394 256 h22 M394 272 h22 M394 288 h22"/>
    </g>

    <!-- jaw plate -->
    <path d="M282 328 L358 328 L344 392 L296 392 Z" fill="url(#s-plate-d)"
          stroke="rgba(255,255,255,.12)" stroke-width="1.4"/>
    <path d="M282 328 L358 328" stroke="rgba(190,212,255,.30)" stroke-width="1.2"/>
    <g stroke="rgba(214,228,255,.30)" stroke-width="1.8" stroke-linecap="round">
      <path d="M300 352 h40"/><path d="M304 364 h32"/>
    </g>

    <!-- bolt rows -->
    <g fill="rgba(214,228,255,.16)">
      <circle cx="238" cy="196" r="2.4"/><circle cx="402" cy="196" r="2.4"/>
      <circle cx="222" cy="322" r="2.4"/><circle cx="418" cy="322" r="2.4"/>
      <circle cx="270" cy="412" r="2.4"/><circle cx="370" cy="412" r="2.4"/>
    </g>

    <!-- specular streak across the helm -->
    <rect class="sent-sheen" x="-160" y="0" width="150" height="720" fill="#dbe8ff"
          opacity=".05" transform="skewX(-16)" clip-path="url(#s-head-clip)"/>
  </g>

  <ellipse cx="320" cy="648" rx="186" ry="20" fill="{BLUE}" opacity=".10" filter="url(#s-b12)"/>
</svg>'''


def main() -> None:
    markup = svg()
    (ROOT / "web" / "site" / "_sentinel.svg").write_text(markup + "\n", encoding="utf-8")

    doc = INDEX.read_text(encoding="utf-8")
    start_tag, end_tag = "<!-- sentinel:start -->", "<!-- sentinel:end -->"
    if start_tag not in doc or end_tag not in doc:
        raise SystemExit("sentinel markers missing from web/site/index.html")
    a = doc.index(start_tag) + len(start_tag)
    b = doc.index(end_tag)
    INDEX.write_text(doc[:a] + "\n" + markup + "\n          " + doc[b:], encoding="utf-8")
    print(f"sentinel cold: {len(markup):,} bytes inline")


if __name__ == "__main__":
    main()
