#!/usr/bin/env python3
"""Assemble the static site into modules the serverless bundle can import.

Sources
    web/site/_layout.html   shell: nav, footer, icon sprite
    web/site/*.html         page bodies (one per route)
    web/static/app.css      design system
    web/static/app.js       page behaviour

Output
    web/pages.py            PAGES: route -> (html, title, description)
    web/assets.py           favicon + social image bytes

Everything is inlined into each page: no external stylesheet, no CDN, no extra
request — which also keeps the Arena preview and a cold serverless request cheap.

    python scripts/build_site.py
"""

from __future__ import annotations

import base64
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "web" / "site"

ROUTES = [
    ("/", "index", "ShieldLint — offline privacy linting for Zcash",
     "Static analysis that finds transparent recipients, memo and viewing-key leaks, "
     "and broken ZIP 316 / ZIP 321 encodings in a Zcash codebase."),
    ("/scan", "scan", "Scan a file for privacy leaks — ShieldLint",
     "Paste source and get rule-by-rule findings with locations, consequences and fixes. "
     "Nothing is stored."),
    ("/address", "address", "Decode a Zcash address — ShieldLint",
     "Decode Unified Addresses, viewing keys, Sapling, Sprout and transparent addresses "
     "offline, with receivers, revision and downgrade risk."),
    ("/uri", "uri", "Validate a ZIP 321 payment request — ShieldLint",
     "Check a zcash: URI against the ZIP 321 grammar: parameters, memos, amounts and the "
     "privacy consequences."),
    ("/rules", "rules", "The rule index — ShieldLint",
     "Fourteen checks for Zcash privacy, each with a rationale, a bad example and a fix."),
    ("/docs", "docs", "Documentation — ShieldLint",
     "Quickstart, CLI reference, configuration, suppression, CI integration and limitations."),
    ("/install", "install", "Install ShieldLint",
     "Install from source, run in Docker, or add one CI step. Python 3.11+, no runtime "
     "dependencies."),
    ("/404", "404", "Page not found — ShieldLint",
     "That page does not decode."),
]

FAVICON_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 34 38">
  <rect width="34" height="38" rx="7" fill="#0a0c10"/>
  <path d="M17 4.2 28.6 8v9.2c0 6.3-4.7 11-11.6 13.3C10.1 28.2 5.4 23.5 5.4 17.2V8L17 4.2Z"
        fill="none" stroke="#2a5bff" stroke-width="2"/>
  <path d="M12.2 14.1h9.6l-9.6 9.8h9.6" fill="none" stroke="#ffffff"
        stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round"/>
</svg>
"""


def main() -> None:
    layout = (SITE / "_layout.html").read_text(encoding="utf-8")
    css = (ROOT / "web" / "static" / "app.css").read_text(encoding="utf-8")
    js = (ROOT / "web" / "static" / "app.js").read_text(encoding="utf-8")
    hero_art = (SITE / "_hero.svg").read_text(encoding="utf-8")

    pages: dict[str, tuple[str, str, str]] = {}
    for path, name, title, description in ROUTES:
        body = (SITE / f"{name}.html").read_text(encoding="utf-8")
        body = body.replace("{{hero_art}}", hero_art)
        nav_key = "nav_" + (name if name not in ("index", "404") else "home")
        html = (
            layout.replace("{{title}}", title)
            .replace("{{description}}", description)
            .replace("{{path}}", "/" if path == "/" else path)
            .replace("{{css}}", css)
            .replace("{{js}}", js)
            .replace("{{body}}", body)
        )
        # mark the active nav item
        for key in ("scan", "address", "uri", "rules", "docs"):
            marker = ' aria-current="page"' if path == "/" + key else ""
            html = html.replace("{{nav_%s}}" % key, marker)
        for leftover in ("{{nav_scan}}", "{{nav_address}}", "{{nav_uri}}",
                         "{{nav_rules}}", "{{nav_docs}}", "{{nav_home}}"):
            html = html.replace(leftover, "")
        pages[path] = (html, title, description)

    out = [
        '"""Generated pages (do not edit — run scripts/build_site.py)."""',
        "# shieldlint: disable-file -- generated: HTML, CSS and JS as strings",
        "",
        "PAGES = {",
    ]
    for path, (html, title, description) in pages.items():
        out.append(f"    {path!r}: {{")
        out.append(f'        "html": {html!r},')
        out.append(f'        "title": {title!r},')
        out.append(f'        "description": {description!r},')
        out.append("    },")
    out.append("}")
    out.append("")
    (ROOT / "web" / "pages.py").write_text("\n".join(out), encoding="utf-8")

    # --- binary assets -----------------------------------------------------
    og = (ROOT / "web" / "og.png").read_bytes()
    fav_png = (ROOT / "web" / "static" / "favicon-32.png").read_bytes()
    assets = [
        '"""Generated assets (do not edit — run scripts/build_site.py)."""',
        "# shieldlint: disable-file -- generated: base64 asset bundles",
        "",
        "import base64",
        "",
        f"FAVICON_SVG = {FAVICON_SVG!r}",
        "",
        "",
        "def og_png() -> bytes:",
        '    """1200x630 social preview."""',
        "    return base64.b64decode(_OG_B64)",
        "",
        "",
        "def favicon_png() -> bytes:",
        '    """32x32 PNG favicon for browsers that ignore SVG."""',
        "    return base64.b64decode(_FAVICON_B64)",
        "",
        "",
        "_OG_B64 = (",
    ]
    og_b64 = base64.b64encode(og).decode("ascii")
    for i in range(0, len(og_b64), 100):
        assets.append(f'    "{og_b64[i:i + 100]}"')
    assets.append(")")
    assets.append("")
    assets.append("_FAVICON_B64 = (")
    fav_b64 = base64.b64encode(fav_png).decode("ascii")
    for i in range(0, len(fav_b64), 100):
        assets.append(f'    "{fav_b64[i:i + 100]}"')
    assets.append(")")
    assets.append("")
    (ROOT / "web" / "assets.py").write_text("\n".join(assets), encoding="utf-8")

    total = sum(len(v[0]) for v in pages.values())
    print(f"built {len(pages)} pages, {total / 1024:.0f} KB of HTML, "
          f"{len(og) / 1024:.0f} KB og image")


if __name__ == "__main__":
    main()
