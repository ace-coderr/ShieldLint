#!/usr/bin/env python3
"""Add a continuous, sub-pixel push-in to every beat.

Why: a screen recording of a web page is mostly a still image. Measured on the
flat cut, the median frame had **4 pixels** changing out of 230 000 — more than
half the runtime is a photograph of a page, and on playback that reads as a
frozen video, no matter how clean the encode is.

`zoompan` is the obvious ffmpeg answer and it does not work here: it crops in
whole pixels, so a 5 % push over 11 s lands 129 of 330 frames on an identical
crop and the picture steps once a second — judder, which is the bug we are
trying to kill. Instead each frame is sampled from a 1.2x master with a bicubic
affine transform, so the motion is genuinely sub-pixel.

Direction alternates beat to beat — in, out, in, out — so the zoom is continuous
across every cut: the beat that ends at 5.5 % meets a beat that starts at 5.5 %.
No reset, nothing to see at the join.

    python3 demo/motion.py                       # all beats -> video/motion/
    python3 demo/motion.py --in a.mp4 --out b.mp4 --amp 0.06
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import imageio_ffmpeg
from PIL import Image

HERE = Path(__file__).resolve().parent
VID = HERE / "video"
SCREEN = VID / "screen"
OUTDIR = VID / "motion"
FF = imageio_ffmpeg.get_ffmpeg_exe()

W, H = 1600, 900
SRC_SCALE = 1.2          # decode master at 1.2x so the transform always downsamples
FPS = 30


def seconds(path: Path) -> float:
    err = subprocess.run([FF, "-hide_banner", "-i", str(path)],
                         capture_output=True, text=True).stderr
    dur = err.split("Duration: ")[1].split(",")[0]
    h, m, s = dur.split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def ramp(src: Path, out: Path, z0: float, z1: float, drift: float) -> int:
    secs = seconds(src)
    n = int(round(secs * FPS))
    sw, sh = int(W * SRC_SCALE), int(H * SRC_SCALE)

    dec = subprocess.Popen(
        [FF, "-v", "error", "-i", str(src),
         "-vf", f"scale={sw}:{sh}:flags=lanczos,fps={FPS}", "-f", "rawvideo",
         "-pix_fmt", "rgb24", "-"],
        stdout=subprocess.PIPE,
    )
    enc = subprocess.Popen(
        [FF, "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
         "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
         "-c:v", "libx264", "-preset", "medium", "-crf", "18",
         "-pix_fmt", "yuv420p", "-r", str(FPS), "-fps_mode", "cfr",
         "-g", "60", "-keyint_min", "60", "-sc_threshold", "0",
         "-profile:v", "high", "-level", "4.1", str(out)],
        stdin=subprocess.PIPE,
    )

    fsz = sw * sh * 3
    i = 0
    while True:
        buf = dec.stdout.read(fsz)
        if len(buf) < fsz:
            break
        k = i / max(n - 1, 1)
        zoom = z0 + (z1 - z0) * k
        cx = sw / 2 + drift * (k - 0.5) * (sw / W)
        cy = sh / 2
        s = (sw / W) / zoom
        coeffs = (s, 0.0, cx - (W / 2) * s,
                  0.0, s, cy - (H / 2) * s)
        frame = Image.frombuffer("RGB", (sw, sh), buf, "raw", "RGB", 0, 1)
        enc.stdin.write(frame.transform((W, H), Image.AFFINE, coeffs,
                                        resample=Image.BICUBIC).tobytes())
        i += 1

    enc.stdin.close()
    dec.stdout.close()
    dec.wait()
    if enc.wait():
        print(f"encode failed: {out}", file=sys.stderr)
        return 1
    print(f"  {out.name:18} {secs:6.2f}s  zoom {z0:.3f} -> {z1:.3f}", flush=True)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="src", type=Path)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--amp", type=float, default=0.055, help="fixed swing per beat")
    ap.add_argument("--rate", type=float, default=0.0,
                    help="zoom per second (wins over --amp; keeps long beats alive)")
    ap.add_argument("--cap", type=float, default=0.11, help="max swing per beat")
    ap.add_argument("--min", dest="minamp", type=float, default=0.045,
                    help="a short beat still needs enough travel to live")
    ap.add_argument("--drift", type=float, default=9.0, help="lateral drift, px")
    a = ap.parse_args()

    if a.src:                                   # single file
        return ramp(a.src, a.out or VID / "take-motion.mp4", 1.0, 1.0 + a.amp, a.drift)

    beats = json.loads((VID / "beats.json").read_text())
    OUTDIR.mkdir(parents=True, exist_ok=True)
    # Beats are graded in pairs: the odd beat pulls back out from exactly the
    # zoom the even beat pushed in to, so no cut ever shows a scale jump.
    for i in range(0, len(beats), 2):
        pair = beats[i:i + 2]
        amp = a.amp
        if a.rate:
            amp = max(a.minamp, min(a.cap, a.rate * pair[0]["seconds"]))
        for j, b in enumerate(pair):
            src = SCREEN / b["file"]
            inward = (j == 0)
            z0, z1 = (1.0, 1.0 + amp) if inward else (1.0 + amp, 1.0)
            if ramp(src, OUTDIR / b["file"], z0, z1, a.drift):
                return 1
    print(f"{OUTDIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
