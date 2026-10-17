#!/usr/bin/env python3
"""Generate the hero sentinel (inline SVG) and inject it into index.html.

    python scripts/make_sentinel.py

The figure is a designed object, not a silhouette: a light ceramic shell with
visible panel seams and bolts, a glossy visor carrying two lit eyes, audio pods,
a beacon, a collar ring and a chest crest in the brand blue. Light shell against
the ink hero is what makes it legible and friendly at a glance.

Motion is CSS (`.sent-*` in app.css). Writes `web/site/_sentinel.svg` and
replaces the content between the sentinel markers in `web/site/index.html`.
"""

from __future__ import annotations

import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "web" / "site" / "index.html"

BLUE = "#2a5bff"
BLUE_SOFT = "#7f9dff"
AMBER = "#f0bd6a"
TEAL = "#35c08a"


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


HEAD = (
    "M320 122 C368 122 402 134 416 160 L432 224 L434 268 C436 306 430 340 414 362 "
    "L386 390 C368 402 346 408 320 408 C294 408 272 402 254 390 "
    "L226 362 C210 340 204 306 206 268 L208 224 L224 160 C238 134 272 122 320 122 Z"
)
VISOR = (
    "M250 226 C250 210 262 202 278 202 L362 202 C378 202 390 210 390 226 "
    "L390 288 C390 306 378 314 362 314 L278 314 C262 314 250 306 250 288 Z"
)
TORSO = "M246 414 L394 414 L486 700 L154 700 Z"


def svg() -> str:
    cx, cy = 320.0, 340.0
    return f'''<svg class="sent" viewBox="24 24 592 660" role="img"
     aria-label="ShieldLint sentinel: a white ceramic robot with a blue visor, standing inside an instrument dial">
  <defs>
    <!-- shell materials -->
    <linearGradient id="s-shell" x1="0.12" y1="0" x2="0.86" y2="1">
      <stop offset="0" stop-color="#eef3fa"/>
      <stop offset=".30" stop-color="#dae2ee"/>
      <stop offset=".70" stop-color="#b9c5d6"/>
      <stop offset="1" stop-color="#939fb2"/>
    </linearGradient>
    <linearGradient id="s-shell-side" x1="0" y1="0" x2="1" y2="0.6">
      <stop offset="0" stop-color="#95a2b6"/>
      <stop offset=".55" stop-color="#c6d0de"/>
      <stop offset="1" stop-color="#e8edf5"/>
    </linearGradient>
    <linearGradient id="s-armor" x1="0.1" y1="0" x2="0.9" y2="1">
      <stop offset="0" stop-color="#39445a"/>
      <stop offset=".55" stop-color="#232c3c"/>
      <stop offset="1" stop-color="#131a26"/>
    </linearGradient>
    <linearGradient id="s-shell-dark" x1="0" y1="0" x2="0.4" y2="1">
      <stop offset="0" stop-color="#8e9cb0"/>
      <stop offset="1" stop-color="#5d6a7e"/>
    </linearGradient>
    <linearGradient id="s-visor" x1="0.1" y1="0" x2="0.8" y2="1">
      <stop offset="0" stop-color="#16233a"/>
      <stop offset=".45" stop-color="#070c15"/>
      <stop offset="1" stop-color="#02050a"/>
    </linearGradient>
    <linearGradient id="s-collar" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#3d4b60"/>
      <stop offset="1" stop-color="#141b26"/>
    </linearGradient>
    <radialGradient id="s-eye" cx="0.5" cy="0.45" r="0.62">
      <stop offset="0" stop-color="#ffffff"/>
      <stop offset=".42" stop-color="#bcd2ff"/>
      <stop offset="1" stop-color="{BLUE}" stop-opacity=".85"/>
    </radialGradient>
    <radialGradient id="s-glow" cx="0.5" cy="0.3" r="0.68">
      <stop offset="0" stop-color="{BLUE}" stop-opacity=".34"/>
      <stop offset=".55" stop-color="{BLUE}" stop-opacity=".09"/>
      <stop offset="1" stop-color="{BLUE}" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="s-fade" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#fff"/>
      <stop offset=".74" stop-color="#fff"/>
      <stop offset="1" stop-color="#000"/>
    </linearGradient>
    <linearGradient id="s-crest" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#5b86ff"/>
      <stop offset="1" stop-color="{BLUE}"/>
    </linearGradient>
    <mask id="s-mask"><rect x="0" y="0" width="640" height="720" fill="url(#s-fade)"/></mask>
    <clipPath id="s-visor-clip"><path d="{VISOR}"/></clipPath>
    <filter id="s-b12" x="-60%" y="-60%" width="220%" height="220%">
      <feGaussianBlur stdDeviation="12"/>
    </filter>
    <filter id="s-b5" x="-60%" y="-60%" width="220%" height="220%">
      <feGaussianBlur stdDeviation="5"/>
    </filter>
    <filter id="s-drop" x="-30%" y="-30%" width="160%" height="170%">
      <feDropShadow dx="0" dy="18" stdDeviation="18" flood-color="#04070c" flood-opacity=".55"/>
    </filter>
  </defs>

  <!-- scene -->
  <ellipse cx="372" cy="216" rx="300" ry="262" fill="url(#s-glow)" opacity=".78"/>

  <g class="sent-dial">
    <circle cx="{cx}" cy="{cy}" r="272" fill="none" stroke="rgba(255,255,255,.09)"/>
    <circle cx="{cx}" cy="{cy}" r="238" fill="none" stroke="rgba(255,255,255,.06)"/>
    <g>{dial(cx, cy, 272)}</g>
  </g>
  <g class="sent-dial-b">
    <path d="M{cx} {cy - 205} A 205 205 0 0 1 {cx + 205} {cy}" fill="none"
          stroke="rgba(127,157,255,.55)" stroke-width="2.2" stroke-linecap="round"/>
    <path d="M{cx} {cy + 205} A 205 205 0 0 1 {cx - 205} {cy}" fill="none"
          stroke="rgba(127,157,255,.18)" stroke-width="2.2" stroke-linecap="round"/>
  </g>

  <g mask="url(#s-mask)" filter="url(#s-drop)">
    <!-- ============================================ shoulders + arms -->
    <path d="M232 424 C186 428 160 456 152 512 L146 588 L206 600 L246 470 Z"
          fill="url(#s-armor)" stroke="rgba(255,255,255,.09)" stroke-width="1.6"/>
    <path d="M408 424 C454 428 480 456 488 512 L494 588 L434 600 L394 470 Z"
          fill="url(#s-armor)" stroke="rgba(255,255,255,.07)" stroke-width="1.6"/>
    <path d="M158 468 C176 448 204 440 230 442" fill="none" stroke="rgba(127,157,255,.55)"
          stroke-width="1.8"/>
    <path d="M482 468 C464 448 436 440 410 442" fill="none" stroke="rgba(127,157,255,.22)"
          stroke-width="1.8"/>
    <path d="M166 470 C186 462 208 464 220 476" fill="none"
          stroke="rgba(255,255,255,.75)" stroke-width="2"/>
    <path d="M474 470 C454 462 432 464 420 476" fill="none"
          stroke="rgba(255,255,255,.22)" stroke-width="2"/>

    <!-- ================================================== torso -->
    <path d="{TORSO}" fill="url(#s-shell)" stroke="rgba(23,32,48,.30)" stroke-width="1.8"/>
    <!-- chest inset -->
    <path d="M268 440 L372 440 L398 566 L242 566 Z" fill="#e7edf6"
          stroke="rgba(23,32,48,.22)" stroke-width="1.6"/>
    <path d="M268 440 L372 440" stroke="rgba(255,255,255,.9)" stroke-width="1.6"/>
    <!-- side seams -->
    <path d="M262 452 L238 610" stroke="rgba(23,32,48,.18)" stroke-width="1.4"/>
    <path d="M378 452 L402 610" stroke="rgba(23,32,48,.24)" stroke-width="1.4"/>
    <!-- crest plate -->
    <circle cx="320" cy="496" r="40" fill="#0a1018" stroke="rgba(23,32,48,.5)" stroke-width="2"/>
    <circle cx="320" cy="496" r="31" fill="url(#s-crest)" opacity=".16"/>
    <g class="sent-crest">
      <path d="M320 470 L342 478 L342 496 C342 512 332 522 320 528 C308 522 298 512 298 496 L298 478 Z"
            fill="none" stroke="{BLUE_SOFT}" stroke-width="2.4"/>
      <path d="M310 486 h20 l-20 20 h20" fill="none" stroke="#eaf1ff" stroke-width="2.6"
            stroke-linecap="round" stroke-linejoin="round"/>
    </g>
    <!-- status lights -->
    <g class="sent-lights">
      <circle cx="270" cy="516" r="4" fill="{TEAL}"/>
      <circle cx="270" cy="532" r="4" fill="{AMBER}" opacity=".85"/>
      <circle cx="270" cy="548" r="4" fill="rgba(23,32,48,.25)"/>
    </g>
    <text x="300" y="648" font-family="ui-monospace, Menlo, monospace" font-size="9"
          letter-spacing="2.4" fill="rgba(23,32,48,.38)">SL-01</text>
    <text x="358" y="648" font-family="ui-monospace, Menlo, monospace" font-size="9"
          letter-spacing="2.4" fill="rgba(23,32,48,.22)">SENTINEL</text>

    <!-- =================================================== neck -->
    <path d="M292 392 L348 392 L352 424 L288 424 Z" fill="url(#s-collar)"/>
    <path d="M292 400 L348 400 M290 410 L350 410" stroke="rgba(255,255,255,.16)"/>
    <ellipse cx="320" cy="424" rx="76" ry="15" fill="url(#s-collar)"/>
    <ellipse cx="320" cy="424" rx="76" ry="15" fill="none" stroke="{BLUE_SOFT}" stroke-opacity=".55"/>

    <!-- =================================================== head -->
    <path d="{HEAD}" fill="url(#s-shell)" stroke="rgba(23,32,48,.34)" stroke-width="1.8"/>
    <!-- crown seam + bolts -->
    <path d="M320 132 L320 202" stroke="rgba(23,32,48,.16)" stroke-width="1.4"/>
    <path d="M270 150 C292 140 348 140 370 150" fill="none" stroke="rgba(255,255,255,.9)"
          stroke-width="2"/>
    <g fill="rgba(23,32,48,.22)">
      <circle cx="238" cy="196" r="3"/><circle cx="402" cy="196" r="3"/>
      <circle cx="222" cy="330" r="3"/><circle cx="418" cy="330" r="3"/>
    </g>

    <!-- brow plate -->
    <path d="M236 190 C276 176 364 176 404 190 L404 206 C364 194 276 194 236 206 Z"
          fill="#f7faff" stroke="rgba(23,32,48,.18)" stroke-width="1.2"/>

    <!-- side pods, flush with the shell -->
    <g>
      <rect x="196" y="238" width="22" height="74" rx="11" fill="url(#s-shell-side)"
            stroke="rgba(23,32,48,.34)" stroke-width="1.4"/>
      <rect x="200" y="250" width="6" height="50" rx="3" fill="#5f6d82" opacity=".55"/>
      <rect x="422" y="238" width="22" height="74" rx="11" fill="url(#s-shell-dark)"
            stroke="rgba(23,32,48,.42)" stroke-width="1.4"/>
      <rect x="430" y="250" width="6" height="50" rx="3" fill="#8fa3bf" opacity=".35"/>
    </g>

    <!-- crown plate in graphite -->
    <path d="M320 122 C368 122 402 134 416 160 L424 194 C398 180 350 172 320 172
             C290 172 242 180 216 194 L224 160 C238 134 272 122 320 122 Z"
          fill="url(#s-armor)" stroke="rgba(255,255,255,.10)" stroke-width="1.2"/>
    <path d="M216 194 C242 180 290 172 320 172 C350 172 398 180 424 194"
          fill="none" stroke="rgba(127,157,255,.45)" stroke-width="1.6"/>

    <!-- visor -->
    <path d="{VISOR}" fill="url(#s-visor)" stroke="rgba(23,32,48,.55)" stroke-width="2"/>
    <g clip-path="url(#s-visor-clip)">
      <ellipse cx="300" cy="238" rx="96" ry="34" fill="{BLUE}" opacity=".26" filter="url(#s-b12)"/>
      <path d="M258 246 C286 232 354 232 382 246" fill="none" stroke="rgba(255,255,255,.18)"
            stroke-width="1.6"/>
      <rect class="sent-scanline" x="244" y="252" width="152" height="16" fill="#bcd2ff"
            opacity=".16" filter="url(#s-b5)"/>

      <!-- instrument eyes: two lit bars, not pupils -->
      <g class="sent-eye-l">
        <rect x="266" y="258" width="40" height="14" rx="7" fill="url(#s-eye)"
              filter="url(#s-b5)" opacity=".85"/>
        <rect x="268" y="260" width="30" height="10" rx="5" fill="#dce8ff"/>
        <rect x="270" y="262" width="11" height="6" rx="3" fill="#ffffff"/>
        <rect x="302" y="263" width="3" height="4" rx="1.5" fill="#dce8ff" opacity=".5"/>
      </g>
      <g class="sent-eye-r">
        <rect x="334" y="258" width="40" height="14" rx="7" fill="url(#s-eye)"
              filter="url(#s-b5)" opacity=".85"/>
        <rect x="336" y="260" width="30" height="10" rx="5" fill="#dce8ff"/>
        <rect x="338" y="262" width="11" height="6" rx="3" fill="#ffffff"/>
        <rect x="370" y="263" width="3" height="4" rx="1.5" fill="#dce8ff" opacity=".5"/>
      </g>
      <path d="M262 296 h116" stroke="rgba(255,255,255,.10)" stroke-width="1"/>
    </g>
    <!-- visor highlight -->
    <path d="M258 216 C286 206 354 206 382 216" fill="none" stroke="rgba(255,255,255,.34)"
          stroke-width="1.6" clip-path="url(#s-visor-clip)"/>

    <!-- cheeks -->
    <path d="M222 322 L258 322 L252 352 L226 346 Z" fill="#eef3fa"
          stroke="rgba(23,32,48,.20)" stroke-width="1.2"/>
    <path d="M418 322 L382 322 L388 352 L414 346 Z" fill="#c3cddc"
          stroke="rgba(23,32,48,.24)" stroke-width="1.2"/>

    <!-- chin + vents -->
    <path d="M270 336 L370 336 L356 392 L284 392 Z" fill="url(#s-armor)"
          stroke="rgba(255,255,255,.10)" stroke-width="1.4"/>
    <path d="M270 336 L370 336" stroke="rgba(127,157,255,.35)" stroke-width="1.4"/>
    <g stroke="rgba(214,228,255,.42)" stroke-width="2" stroke-linecap="round">
      <path d="M302 354 h36"/><path d="M306 366 h28"/>
    </g>

    <!-- beacon -->
    <path d="M398 148 L424 112" stroke="rgba(23,32,48,.35)" stroke-width="4"
          stroke-linecap="round"/>
    <path d="M398 148 L424 112" stroke="rgba(255,255,255,.75)" stroke-width="1.6"
          stroke-linecap="round"/>
    <g class="sent-pip">
      <circle cx="428" cy="106" r="10" fill="{AMBER}" opacity=".28" filter="url(#s-b5)"/>
      <circle cx="428" cy="106" r="5" fill="{AMBER}"/>
      <circle cx="426.5" cy="104.5" r="1.8" fill="#fff8ea"/>
    </g>

    <!-- rim light down the left edge -->
    <path d="M214 182 C226 144 264 128 320 128" fill="none" stroke="rgba(255,255,255,.95)"
          stroke-width="2.4" stroke-linecap="round"/>
    <path d="M204 240 C200 276 202 312 212 342" fill="none" stroke="rgba(127,157,255,.55)"
          stroke-width="2" stroke-linecap="round"/>
  </g>

  <ellipse cx="320" cy="642" rx="188" ry="22" fill="{BLUE}" opacity=".12" filter="url(#s-b12)"/>
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
    print(f"sentinel v3: {len(markup):,} bytes inline")


if __name__ == "__main__":
    main()
