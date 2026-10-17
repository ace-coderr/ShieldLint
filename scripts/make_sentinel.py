#!/usr/bin/env python3
"""Generate the hero sentinel (inline SVG) and inject it into index.html.

    python scripts/make_sentinel.py

Drawn as vector geometry: a faceted graphite helmet, a slim sensor slit behind
glass, angular vent stacks, an instrument dial and one blue rim light. Motion
lives in CSS (the `.sent-*` block in app.css) so the markup stays declarative.

Writes `web/site/_sentinel.svg` and replaces whatever sits between the
`sentinel:start` / `sentinel:end` markers in `web/site/index.html`.
"""

from __future__ import annotations

import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "web" / "site" / "index.html"

BLUE = "#2a5bff"
BLUE_SOFT = "#7f9dff"
EDGE = "rgba(255,255,255,.14)"

# faceted helmet, clockwise from the crown
HEAD = (
    "M320 86 L394 104 L444 156 L462 246 L458 330 L424 394 "
    "L372 428 L320 436 L268 428 L216 394 L182 330 L178 246 "
    "L196 156 L246 104 Z"
)
VISOR = ("M236 232 L404 232 L420 250 L420 292 L404 310 "
         "L236 310 L220 292 L220 250 Z")


def dial(cx: float, cy: float, r: float) -> str:
    out = []
    for deg in range(0, 360, 5):
        a = math.radians(deg - 90)
        major = deg % 45 == 0
        inner = r - (20 if major else 9)
        x1, y1 = cx + math.cos(a) * inner, cy + math.sin(a) * inner
        x2, y2 = cx + math.cos(a) * r, cy + math.sin(a) * r
        op = ".34" if major else ".14"
        w = "1.6" if major else "1"
        out.append(
            f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="rgba(220,232,255,{op})" stroke-width="{w}" stroke-linecap="round"/>'
        )
    return "\n      ".join(out)


def svg() -> str:
    cx, cy = 320.0, 340.0
    return f'''<svg class="sent" viewBox="18 18 604 650" role="img"
     aria-label="ShieldLint sentinel: a graphite helmet with a glass sensor slit, inside an instrument dial">
  <defs>
    <linearGradient id="s-plate" x1="0.1" y1="0" x2="0.85" y2="1">
      <stop offset="0" stop-color="#232b37"/>
      <stop offset=".30" stop-color="#161d27"/>
      <stop offset=".68" stop-color="#101620"/>
      <stop offset="1" stop-color="#080b11"/>
    </linearGradient>
    <linearGradient id="s-plate-lit" x1="0" y1="1" x2="1" y2="0">
      <stop offset="0" stop-color="#0c1119"/>
      <stop offset=".55" stop-color="#1a222e"/>
      <stop offset="1" stop-color="#2b3543"/>
    </linearGradient>
    <linearGradient id="s-visor" x1="0" y1="0" x2="0.25" y2="1">
      <stop offset="0" stop-color="#0e1a2b"/>
      <stop offset=".5" stop-color="#060b13"/>
      <stop offset="1" stop-color="#02050a"/>
    </linearGradient>
    <linearGradient id="s-rim" x1="0" y1="0.2" x2="1" y2="0.9">
      <stop offset="0" stop-color="rgba(127,157,255,0)"/>
      <stop offset=".55" stop-color="rgba(127,157,255,.18)"/>
      <stop offset="1" stop-color="rgba(190,212,255,.85)"/>
    </linearGradient>
    <linearGradient id="s-top" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="rgba(255,255,255,.20)"/>
      <stop offset="1" stop-color="rgba(255,255,255,0)"/>
    </linearGradient>
    <radialGradient id="s-glow" cx="0.55" cy="0.28" r="0.7">
      <stop offset="0" stop-color="{BLUE}" stop-opacity=".38"/>
      <stop offset=".5" stop-color="{BLUE}" stop-opacity=".10"/>
      <stop offset="1" stop-color="{BLUE}" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="s-lens" cx="0.42" cy="0.36" r="0.62">
      <stop offset="0" stop-color="#f2f7ff"/>
      <stop offset=".22" stop-color="#9dbcff"/>
      <stop offset=".62" stop-color="{BLUE}" stop-opacity=".55"/>
      <stop offset="1" stop-color="{BLUE}" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="s-fade" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#fff"/>
      <stop offset=".70" stop-color="#fff"/>
      <stop offset="1" stop-color="#000"/>
    </linearGradient>
    <mask id="s-mask"><rect x="0" y="0" width="640" height="720" fill="url(#s-fade)"/></mask>
    <clipPath id="s-visor-clip"><path d="{VISOR}"/></clipPath>
    <clipPath id="s-head-clip"><path d="{HEAD}"/></clipPath>
    <filter id="s-b10" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur stdDeviation="10"/>
    </filter>
    <filter id="s-b4" x="-60%" y="-60%" width="220%" height="220%">
      <feGaussianBlur stdDeviation="4"/>
    </filter>
  </defs>

  <!-- ambient wash -->
  <ellipse cx="352" cy="252" rx="268" ry="256" fill="url(#s-glow)"/>

  <!-- instrument dial -->
  <g class="sent-dial">
    <circle cx="{cx}" cy="{cy}" r="276" fill="none" stroke="rgba(255,255,255,.07)"/>
    <circle cx="{cx}" cy="{cy}" r="250" fill="none" stroke="rgba(255,255,255,.05)"/>
    <g>{dial(cx, cy, 276)}</g>
  </g>
  <g class="sent-dial-b">
    <path d="M{cx} {cy - 216} A 216 216 0 0 1 {cx + 216} {cy}" fill="none"
          stroke="rgba(127,157,255,.55)" stroke-width="2" stroke-linecap="round"/>
    <path d="M{cx} {cy + 216} A 216 216 0 0 1 {cx - 216} {cy}" fill="none"
          stroke="rgba(127,157,255,.16)" stroke-width="2" stroke-linecap="round"/>
  </g>

  <g mask="url(#s-mask)">
    <!-- shoulders -->
    <path d="M148 486 L214 462 L262 452 L272 512 L214 556 L150 540 Z"
          fill="url(#s-plate-lit)" stroke="{EDGE}"/>
    <path d="M492 486 L426 462 L378 452 L368 512 L426 556 L490 540 Z"
          fill="url(#s-plate)" stroke="{EDGE}"/>
    <path d="M212 500 L258 470" stroke="rgba(190,212,255,.55)" stroke-width="1.6"/>
    <path d="M428 500 L382 470" stroke="rgba(127,157,255,.22)" stroke-width="1.6"/>

    <!-- torso -->
    <path d="M262 452 L378 452 L436 700 L204 700 Z" fill="url(#s-plate)" stroke="{EDGE}"/>
    <path d="M286 466 L354 466 L392 672 L248 672 Z" fill="none" stroke="rgba(255,255,255,.055)"/>
    <path d="M262 452 L378 452" stroke="rgba(255,255,255,.18)" stroke-width="1.2"/>

    <!-- chest instrument -->
    <g class="sent-core">
      <circle cx="320" cy="566" r="54" fill="#06090f" stroke="rgba(255,255,255,.12)"/>
      <circle cx="320" cy="566" r="44" fill="none" stroke="rgba(42,91,255,.40)" stroke-dasharray="2 8"/>
      <circle cx="320" cy="566" r="30" fill="#04070c" stroke="rgba(255,255,255,.08)"/>
      <circle cx="320" cy="566" r="20" fill="url(#s-lens)" opacity=".95"/>
      <circle cx="320" cy="566" r="5" fill="#eef4ff"/>
    </g>
    <g stroke="rgba(255,255,255,.08)">
      <line x1="256" y1="494" x2="384" y2="494"/>
      <line x1="250" y1="640" x2="390" y2="640"/>
    </g>

    <!-- neck -->
    <path d="M292 416 L348 416 L356 462 L284 462 Z" fill="#070a10" stroke="{EDGE}"/>
    <path d="M288 434 L352 434 M286 448 L354 448" stroke="rgba(255,255,255,.07)"/>

    <!-- helmet -->
    <path d="{HEAD}" fill="url(#s-plate)" stroke="rgba(255,255,255,.16)"/>
    <path d="{HEAD}" fill="none" stroke="url(#s-rim)" stroke-width="2"/>
    <!-- crown facet -->
    <path d="M246 104 L320 86 L394 104 L360 132 L280 132 Z" fill="rgba(255,255,255,.045)"/>
    <path d="M280 132 L360 132" stroke="rgba(255,255,255,.14)"/>
    <path d="M246 104 L280 132 M394 104 L360 132" stroke="rgba(255,255,255,.10)"/>
    <!-- side facets -->
    <path d="M196 156 L246 104 L280 132 L236 232 L220 250 L178 246 Z"
          fill="rgba(255,255,255,.018)"/>
    <path d="M444 156 L394 104 L360 132 L404 232 L420 250 L462 246 Z"
          fill="rgba(0,0,0,.25)"/>
    <path d="M182 330 L220 292 L220 250 L178 246 Z" fill="rgba(0,0,0,.30)"/>
    <path d="M458 330 L420 292 L420 250 L462 246 Z" fill="rgba(0,0,0,.34)"/>

    <!-- brow -->
    <path d="M232 206 L408 206 L418 226 L222 226 Z" fill="rgba(255,255,255,.06)"
          stroke="rgba(255,255,255,.10)"/>

    <!-- visor -->
    <path d="{VISOR}" fill="url(#s-visor)" stroke="rgba(255,255,255,.16)"/>
    <g clip-path="url(#s-visor-clip)">
      <ellipse cx="268" cy="240" rx="128" ry="46" fill="{BLUE}" opacity=".20" filter="url(#s-b10)"/>
      <rect class="sent-scanline" x="214" y="236" width="212" height="20" fill="{BLUE_SOFT}"
            opacity=".14" filter="url(#s-b4)"/>
      <path class="sent-slit" d="M254 270 h132" stroke="#dbe7ff" stroke-width="2.6"
            stroke-linecap="round"/>
      <path class="sent-sensor" d="M398 270 h8" stroke="{BLUE_SOFT}" stroke-width="2.6"
            stroke-linecap="round"/>
      <path d="M224 300 h192" stroke="rgba(255,255,255,.06)"/>
    </g>

    <!-- cheek vents -->
    <g stroke="rgba(255,255,255,.13)" stroke-width="2.4" stroke-linecap="round">
      <path d="M198 262 h26 M198 280 h26 M198 298 h26"/>
      <path d="M416 262 h26 M416 280 h26 M416 298 h26"/>
    </g>

    <!-- chin stack -->
    <path d="M284 356 L356 356 L346 408 L294 408 Z" fill="#070a10" stroke="{EDGE}"/>
    <g stroke="rgba(255,255,255,.16)" stroke-width="2" stroke-linecap="round">
      <path d="M296 372 h48"/><path d="M298 384 h44"/><path d="M302 396 h36"/>
    </g>

    <!-- crown light -->
    <path d="M404 104 l16 -22" stroke="rgba(255,255,255,.20)" stroke-width="2.6"
          stroke-linecap="round"/>
    <circle class="sent-pip" cx="422" cy="79" r="4" fill="{BLUE_SOFT}"/>

    <rect class="sent-sheen" x="-160" y="0" width="140" height="720" fill="#cfe0ff"
          opacity=".045" transform="skewX(-14)" clip-path="url(#s-head-clip)"/>
  </g>

  <ellipse cx="320" cy="664" rx="196" ry="26" fill="{BLUE}" opacity=".09" filter="url(#s-b10)"/>
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
    print(f"sentinel v2: {len(markup):,} bytes inline")


if __name__ == "__main__":
    main()
