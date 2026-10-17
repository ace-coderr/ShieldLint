#!/usr/bin/env python3
"""Render the 1200x630 social preview image (Open Graph / Twitter card).

    python scripts/make_og.py

Writes `web/og.png`; `scripts/embed_web.py` then inlines it so the serverless
bundle can serve it without filesystem access.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "web" / "og.png"

W, H = 1200, 630
BG = (8, 13, 11)
GREEN = (74, 222, 128)
GREEN_DIM = (31, 111, 69)
TEXT = (215, 229, 221)
MUTED = (122, 144, 135)
LINE = (29, 47, 39)

FONTS = Path("/usr/share/fonts/truetype/dejavu")


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONTS / name), size)


def shield(draw: ImageDraw.ImageDraw, x: int, y: int, scale: float = 1.0) -> None:
    """Draw the shield mark with the Z inside, sized from a 34x38 viewbox."""
    w, h = 34 * scale, 38 * scale
    pts = [
        (x + w / 2, y),
        (x + w, y + h * 0.132),
        (x + w, y + h * 0.447),
        (x + w / 2, y + h),
        (x, y + h * 0.447),
        (x, y + h * 0.132),
    ]
    draw.polygon(pts, outline=GREEN)
    lw = max(2, int(2.2 * scale))
    # Z
    zx0, zx1 = x + w * 0.26, x + w * 0.74
    zy0, zy1 = y + h * 0.32, y + h * 0.64
    draw.line([(zx0, zy0), (zx1, zy0)], fill=GREEN, width=lw)
    draw.line([(zx1, zy0), (zx0, zy1)], fill=GREEN, width=lw)
    draw.line([(zx0, zy1), (zx1, zy1)], fill=GREEN, width=lw)


def main() -> None:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    # subtle grid
    for gx in range(0, W, 60):
        d.line([(gx, 0), (gx, H)], fill=(13, 21, 18))
    for gy in range(0, H, 60):
        d.line([(0, gy), (W, gy)], fill=(13, 21, 18))

    # green glow, top-left
    glow = Image.new("RGB", (W, H), BG)
    gd = ImageDraw.Draw(glow)
    for i in range(220, 0, -4):
        a = int(10 * (1 - i / 220))
        gd.ellipse([(-i, -i), (i * 2.4, i * 1.8)], fill=(a, a * 4, a * 3))
    img = Image.blend(img, glow, 0.55)
    d = ImageDraw.Draw(img)

    # top bar
    d.text((64, 54), "ZECATHON 2026", font=font("DejaVuSansMono-Bold.ttf", 19), fill=GREEN)
    d.text((W - 210, 54), "CORE & TOOLING", font=font("DejaVuSansMono-Bold.ttf", 19), fill=MUTED)
    d.line([(64, 92), (W - 64, 92)], fill=LINE, width=2)

    # logo + name
    shield(d, 64, 132, 2.1)
    d.text((188, 132), "Shield", font=font("DejaVuSansMono-Bold.ttf", 74), fill=TEXT)
    d.text((188 + d.textlength("Shield", font=font("DejaVuSansMono-Bold.ttf", 74)), 132),
           "Lint", font=font("DejaVuSansMono-Bold.ttf", 74), fill=GREEN)

    # tagline
    d.text((64, 262), "Privacy has no compile error.", font=font("DejaVuSans-Bold.ttf", 42), fill=TEXT)
    d.text((64, 320), "Offline static analysis for Zcash — transparent recipients,",
           font=font("DejaVuSans.ttf", 27), fill=MUTED)
    d.text((64, 358), "memo & viewing-key leaks, broken ZIP 316 / ZIP 321 encodings.",
           font=font("DejaVuSans.ttf", 27), fill=MUTED)

    # chips
    chips = ["14 rules", "70 tests", "ZIP 316", "ZIP 321", "SARIF", "MIT"]
    x, y = 64, 428
    f = font("DejaVuSansMono.ttf", 20)
    for chip in chips:
        w = d.textlength(chip, font=f) + 34
        if x + w > W - 64:
            x, y = 64, y + 58
        d.rounded_rectangle([x, y, x + w, y + 42], radius=21, outline=GREEN_DIM, width=2)
        d.text((x + 17, y + 10), chip, font=f, fill=TEXT)
        x += w + 12

    # footer
    d.line([(64, H - 92), (W - 64, H - 92)], fill=LINE, width=2)
    d.text((64, H - 66), "github.com/ace-coderr/ShieldLint", font=font("DejaVuSansMono.ttf", 21), fill=GREEN)
    d.text((W - 300, H - 66), "shieldlint.vercel.app", font=font("DejaVuSansMono.ttf", 21), fill=MUTED)

    img.save(OUT, "PNG", optimize=True)
    print(f"wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
