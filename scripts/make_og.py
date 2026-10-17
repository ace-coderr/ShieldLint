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

    # ---- the scan panel, right -------------------------------------------
    # Same artefact as the hero: an editor mid-scan, with a findings card
    # dropping out of it. Draw order: halo, panel, code, badge, card.
    px0, py0, pw, ph = 700, 88, 424, 344
    px1, py1 = px0 + pw, py0 + ph

    halo = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(halo).rounded_rectangle([px0 - 40, py0 - 30, px1 + 60, py1 + 70],
                                           radius=48, fill=(30, 66, 190, 120))
    img = Image.alpha_composite(img.convert("RGBA"),
                                halo.filter(ImageFilter.GaussianBlur(60))).convert("RGB")
    d = ImageDraw.Draw(img)

    PANEL = (10, 14, 22)
    d.rounded_rectangle([px0, py0, px1, py1], radius=22, fill=PANEL, outline=(44, 52, 68), width=1)

    # title bar
    for i, c in enumerate(((58, 30, 28), (58, 46, 26), (26, 52, 40))):
        d.ellipse([px0 + 18 + i * 15, py0 + 19, px0 + 25 + i * 15, py0 + 26], fill=c)
    d.text((px0 + 66, py0 + 13), "apps/pay/checkout.py", font=font(MONO, 12), fill=(150, 160, 178))
    d.ellipse([px1 - 106, py0 + 20, px1 - 100, py0 + 26], fill=(53, 192, 138))
    d.text((px1 - 92, py0 + 13), "SCANNING", font=font(MONO, 10), fill=(120, 132, 150))
    d.line([(px0, py0 + 38), (px1, py0 + 38)], fill=(32, 39, 52), width=1)

    KW = (143, 166, 255)
    STR = (151, 232, 193)
    TXT = (225, 231, 242)
    COM = (108, 118, 136)
    NUM = (88, 96, 112)
    RED = (255, 178, 167)

    lines = [
        (11, [("import ", KW), ("logging", TXT)], False, None),
        (12, [("from ", KW), ("wallet ", TXT), ("import ", KW), ("send", TXT)], False, None),
        (13, [], False, None),
        (14, [("# checkout -> payout path", COM)], False, None),
        (15, [("def ", KW), ("payout", TXT), ("(order, vk):", TXT)], False, None),
        (16, [("    dest = ", TXT), ('"t1Yq6vF7NNbRk…u9f4"', STR)], True, "SL001"),
        (17, [('    memo = f"order {order.id}"', TXT)], False, None),
        (18, [("    key = ", TXT), ('"uview1…q4mw"', STR)], True, "SL006"),
    ]

    fcode = font(MONO, 13)
    fnum = font(MONO, 11)
    y = py0 + 56
    for num, tokens, flagged, rid in lines:
        row_top = y - 7
        if flagged:
            d.rectangle([px0 + 1, row_top, px1 - 1, row_top + 30], fill=(30, 16, 19))
            d.rectangle([px0 + 1, row_top, px0 + 3, row_top + 30], fill=(214, 78, 68))
        label = str(num)
        d.text((px0 + 22, y), label, font=fnum, fill=NUM)
        x = px0 + 56
        for text, colour in tokens:
            d.text((x, y), text, font=fcode, fill=colour)
            x += d.textlength(text, font=fcode)
        if rid:
            bw = int(d.textlength(rid, font=fnum)) + 16
            d.rounded_rectangle([px1 - 20 - bw, y - 4, px1 - 20, y + 18], radius=5,
                                fill=(38, 18, 21), outline=(96, 46, 46), width=1)
            d.text((px1 - 12 - bw, y), rid, font=fnum, fill=RED)
        y += 31

    # ---- findings card ----------------------------------------------------
    cx0, cy0, cw, ch = 748, 392, 384, 150
    cx1, cy1 = cx0 + cw, cy0 + ch
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle([cx0 + 6, cy0 + 14, cx1 - 4, cy1 + 12],
                                             radius=18, fill=(0, 0, 0, 150))
    img = Image.alpha_composite(img.convert("RGBA"),
                                shadow.filter(ImageFilter.GaussianBlur(18))).convert("RGB")
    d = ImageDraw.Draw(img)

    d.rounded_rectangle([cx0, cy0, cx1, cy1], radius=16, fill=(11, 15, 23),
                        outline=(46, 55, 72), width=1)
    d.ellipse([cx0 + 18, cy0 + 15, cx0 + 24, cy0 + 21], fill=(53, 192, 138))
    d.text((cx0 + 32, cy0 + 9), "checkout.py", font=font(MONO, 11), fill=(160, 170, 188))
    ms = "38 ms"
    d.text((cx1 - 18 - d.textlength(ms, font=font(MONO, 11)), cy0 + 9), ms,
           font=font(MONO, 11), fill=(112, 124, 142))
    d.line([(cx0, cy0 + 32), (cx1, cy0 + 32)], fill=(34, 42, 56), width=1)
    d.line([(cx0, cy1 - 34), (cx1, cy1 - 34)], fill=(34, 42, 56), width=1)

    rows = [
        ("SL006", "viewing key in source", "ERROR", (255, 139, 128)),
        ("SL001", "payment to t1… address", "ERROR", (255, 139, 128)),
        ("SL003", "UA carries a t-receiver", "WARNING", (240, 189, 106)),
    ]
    frow = font(MONO, 11)
    ry = cy0 + 42
    for rid, text, sev, sevcol in rows:
        d.text((cx0 + 18, ry), rid, font=font(MONO_B, 11), fill=(127, 157, 255))
        d.text((cx0 + 74, ry), text, font=frow, fill=(196, 206, 222))
        d.text((cx1 - 18 - d.textlength(sev, font=frow), ry), sev, font=frow, fill=sevcol)
        ry += 27

    d.text((cx0 + 18, cy1 - 27), "1 error blocked", font=font(MONO_B, 11), fill=(240, 244, 250))
    d.text((cx0 + 18 + d.textlength("1 error blocked", font=font(MONO_B, 11)) + 8, cy1 - 27),
           "· 2 warnings", font=frow, fill=(140, 150, 168))
    d.rounded_rectangle([cx1 - 56, cy1 - 30, cx1 - 18, cy1 - 12], radius=5,
                        fill=(34, 17, 20), outline=(96, 46, 46), width=1)
    d.text((cx1 - 48, cy1 - 27), "exit 1", font=font(MONO, 10), fill=(255, 139, 128))

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
