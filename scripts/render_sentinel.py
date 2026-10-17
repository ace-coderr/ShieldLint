#!/usr/bin/env python3
"""Rasterise the hero sentinel to a transparent PNG for the social card.

    python scripts/render_sentinel.py

`scripts/make_og.py` composites the result into `web/og.png`. The SVG is the
source of truth (`web/site/_sentinel.svg`, written by `make_sentinel.py`), so
the social card can never drift away from the hero again.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SVG = ROOT / "web" / "site" / "_sentinel.svg"
OUT = ROOT / "web" / "static" / "sentinel-art.png"

HTML = """<!doctype html>
<html><head><meta charset="utf-8">
<style>
  html, body {{ margin: 0; background: transparent; }}
  body {{ width: {w}px; height: {h}px; display: grid; place-items: center; }}
  svg {{ width: {w}px; height: auto; display: block; }}
</style></head>
<body>{svg}</body></html>
"""


def main() -> None:
    from playwright.sync_api import sync_playwright

    svg = SVG.read_text(encoding="utf-8")
    w, h = 640, 660
    page_html = HTML.format(w=w, h=h, svg=svg)

    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox"])
        page = browser.new_page(viewport={"width": w, "height": h},
                                device_scale_factor=2)
        page.set_content(page_html, wait_until="load")
        page.wait_for_timeout(400)
        page.screenshot(path=str(OUT), omit_background=True)
        browser.close()

    print(f"wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size:,} bytes, {w * 2}x{h * 2})")


if __name__ == "__main__":
    main()
