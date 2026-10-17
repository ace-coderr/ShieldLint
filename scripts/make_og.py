#!/usr/bin/env python3
"""Render the 1200x630 social preview image (Open Graph / Twitter card).

    python scripts/make_og.py

Writes `web/og.png`. The palette and type match the site: ink background, one
signal blue, mono labels. `scripts/build_site.py` inlines the PNG so the
serverless bundle can serve it without filesystem access.
"""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "web" / "og.png"

W, H = 1200, 630
BG = (7, 9, 13)
BLUE = (42, 91, 255)
BLUE_SOFT = (127, 157, 255)
LINE = (34, 42, 55)
TEXT = (245, 247, 251)
MUTED = (150, 160, 176)

FONTS = Path("/usr/share/fonts/truetype/dejavu")
MONO_B = "DejaVuSansMono-Bold.ttf"
MONO = "DejaVuSansMono.ttf"
SANS_B = "DejaVuSans-Bold.ttf"
SANS = "DejaVuSans.ttf"


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONTS / name), size)


def shield(draw: ImageDraw.ImageDraw, x: float, y: float, scale: float = 1.0,
           filled: bool = False) -> None:
    """The ShieldLint mark: a shield with a Z, sized from a 34x38 viewbox."""
    w, h = 34 * scale, 38 * scale
    pts = [
        (x + w * 0.5, y),
        (x + w, y + h * 0.145),
        (x + w, y + h * 0.45),
        (x + w * 0.5, y + h),
        (x, y + h * 0.45),
        (x, y + h * 0.145),
    ]
    if filled:
        draw.polygon(pts, fill=(255, 255, 255))
    else:
        draw.polygon(pts, outline=BLUE_SOFT)
        inner = [(x + (px - x) * 0.88 + w * 0.06, y + (py - y) * 0.88 + h * 0.06) for px, py in pts]
        draw.polygon(inner, outline=(42, 52, 70))
    lw = max(2, int(2.4 * scale))
    zx0, zx1 = x + w * 0.27, x + w * 0.73
    zy0, zy1 = y + h * 0.33, y + h * 0.65
    col = (7, 9, 13) if filled else (255, 255, 255)
    draw.line([(zx0, zy0), (zx1, zy0)], fill=col, width=lw)
    draw.line([(zx1, zy0), (zx0, zy1)], fill=col, width=lw)
    draw.line([(zx0, zy1), (zx1, zy1)], fill=col, width=lw)


def glow(size: tuple[int, int], centre: tuple[float, float], radius: float,
         colour: tuple[int, int, int], alpha: int, blur: int) -> Image.Image:
    """A soft radial light, as an RGBA layer that can be composited cleanly."""
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    cx, cy = centre
    ld.ellipse([cx - radius, cy - radius, cx + radius, cy + radius],
               fill=(*colour, alpha))
    return layer.filter(ImageFilter.GaussianBlur(blur))


def main() -> None:
    img = Image.new("RGB", (W, H), BG)

    # ---- blue bloom ------------------------------------------------------
    img = Image.alpha_composite(
        img.convert("RGBA"),
        glow((W, H), (1040, 90), 330, BLUE, 96, 160),
    ).convert("RGB")
    img = Image.alpha_composite(
        img.convert("RGBA"),
        glow((W, H), (420, 700), 420, (26, 52, 140), 60, 220),
    ).convert("RGB")

    d = ImageDraw.Draw(img)

    # ---- grid -------------------------------------------------------------
    for gx in range(0, W, 72):
        d.line([(gx, 0), (gx, H)], fill=(11, 14, 20))
    for gy in range(0, H, 72):
        d.line([(0, gy), (W, gy)], fill=(11, 14, 20))

    # ---- the sentinel, right ---------------------------------------------
    # Rendered from the same SVG the hero uses (scripts/render_sentinel.py),
    # so the card and the homepage can never disagree.
    art = Image.open(ROOT / "web" / "static" / "sentinel-art.png").convert("RGBA")
    art.thumbnail((548, 596), Image.LANCZOS)

    # fade the figure's lower edge into the card instead of cropping it
    fade = Image.new("L", art.size, 255)
    fd = ImageDraw.Draw(fade)
    tail = int(art.height * 0.26)
    for i in range(tail):
        fd.line([(0, art.height - tail + i), (art.width, art.height - tail + i)],
                fill=int(255 * (1 - i / tail)))
    art.putalpha(Image.composite(art.getchannel("A"), Image.new("L", art.size, 0), fade))

    img = Image.alpha_composite(
        img.convert("RGBA"),
        glow((W, H), (966, 214), 268, BLUE, 62, 170),
    ).convert("RGB")
    d = ImageDraw.Draw(img)
    img.paste(art, (W - 58 - art.width, 58), art)
    d = ImageDraw.Draw(img)

    # ---- left column ------------------------------------------------------
    x0 = 72
    d.text((x0, 56), "ZECATHON 2026", font=font(MONO_B, 16), fill=BLUE_SOFT)
    d.text((x0 + 168, 56), "·  CORE & TOOLING", font=font(MONO, 16), fill=MUTED)
    d.line([(x0, 92), (W - x0, 92)], fill=LINE, width=1)

    shield(d, x0, 122, 1.35)
    d.text((x0 + 62, 126), "ShieldLint", font=font(SANS_B, 40), fill=TEXT)

    d.text((x0, 218), "Privacy has", font=font(SANS_B, 54), fill=TEXT)
    d.text((x0, 276), "no compile error.", font=font(SANS_B, 54), fill=TEXT)

    d.text((x0, 356), "Offline static analysis for Zcash. Finds transparent",
           font=font(SANS, 22), fill=MUTED)
    d.text((x0, 386), "recipients, memo and viewing-key leaks, and broken",
           font=font(SANS, 22), fill=MUTED)
    d.text((x0, 416), "ZIP 316 / ZIP 321 encodings before they ship.",
           font=font(SANS, 22), fill=MUTED)

    chips = ["14 RULES", "72 TESTS", "0 DEPS", "ZIP 316", "ZIP 321", "SARIF", "MIT"]
    x, y = x0, 470
    f = font(MONO_B, 13)
    for chip in chips:
        w = d.textlength(chip, font=f) + 26
        if x + w > W - x0:
            break
        d.rounded_rectangle([x, y, x + w, y + 32], radius=16, outline=(60, 72, 92), width=1)
        d.text((x + 13, y + 9), chip, font=f, fill=(196, 208, 226))
        x += w + 10

    # ---- footer -----------------------------------------------------------
    d.line([(x0, H - 76), (W - x0, H - 76)], fill=LINE, width=1)
    d.text((x0, H - 54), "github.com/ace-coderr/ShieldLint", font=font(MONO, 17), fill=BLUE_SOFT)
    label = "shieldlint.vercel.app"
    d.text((W - x0 - d.textlength(label, font=font(MONO, 17)), H - 54), label,
           font=font(MONO, 17), fill=MUTED)

    img.save(OUT, "PNG", optimize=True)
    print(f"wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
