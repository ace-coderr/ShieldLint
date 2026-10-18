#!/usr/bin/env python3
"""Record the demo from a real X display at a constant 30 fps.

Why this exists: Playwright's own video recorder only writes a frame when the
page repaints. The resulting file had **745 unique frames in 120 s** (~6 fps)
and 52 frozen stretches — every scroll and typing burst moved in steps, which
reads as stuttering. x11grab samples the screen on a clock, so motion is smooth.

    python3 demo/record_screen.py            # all beats
    python3 demo/record_screen.py 01 08      # just the title and end cards

Needs Xvfb (`Xvfb :99 -screen 0 1600x900x24`) and the site on :8010.
Writes demo/video/screen/NN-name.mp4 plus demo/video/beats.json.
"""
from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import imageio_ffmpeg
from playwright.sync_api import sync_playwright

import record as rec                      # reuse the beats and the overlay

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
VID = HERE / "video" / "screen"
W, H = rec.W, rec.H
DISPLAY = os.environ.get("DISPLAY", ":99")
FF = imageio_ffmpeg.get_ffmpeg_exe()

BEATS = [
    ("01-title", rec.seg_title, str(OUT / "title.html")),
    ("02-home", rec.seg_home, rec.SITE + "/"),
    ("03-terminal", rec.seg_terminal, str(OUT / "terminal.html")),
    ("04-scan", rec.seg_scan, rec.SITE + "/scan"),
    ("05-address", rec.seg_address, rec.SITE + "/address"),
    ("06-uri", rec.seg_uri, rec.SITE + "/uri"),
    ("07-rules", rec.seg_rules, rec.SITE + "/rules"),
    ("08-end", rec.seg_end, str(OUT / "end.html")),
]


def start_capture(dst: Path) -> subprocess.Popen:
    return subprocess.Popen(
        [FF, "-y", "-hide_banner", "-loglevel", "error",
         "-f", "x11grab", "-draw_mouse", "0",
         "-video_size", f"{W}x{H}", "-framerate", "30", "-i", f"{DISPLAY}.0",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "14",
         "-pix_fmt", "yuv420p", str(dst)],
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
    )


def stop_capture(proc: subprocess.Popen) -> None:
    proc.send_signal(signal.SIGINT)       # ffmpeg finalises the moov box
    try:
        proc.wait(timeout=20)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()


def main() -> int:
    only = set(sys.argv[1:])
    VID.mkdir(parents=True, exist_ok=True)
    keep = [(n, fn, u) for n, fn, u in BEATS
            if not only or n.split("-")[0] in only or n.split("-")[1] in only]

    marks: list[dict] = []
    os.environ["DISPLAY"] = DISPLAY
    # Playwright's own launch leaves the browser window with tabs and an
    # address bar in the capture. Instead we drive a Chromium started with
    # `--kiosk --app=...` (see demo/capture.sh) over CDP.
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        ctx = browser.contexts[0]
        page = ctx.pages[0]

        for name, fn, url in keep:
            dst = VID / f"{name}.mp4"
            if dst.exists():
                dst.unlink()
            if url.startswith("http"):
                page.evaluate("() => 1") if False else None
                page.goto(url, wait_until="networkidle")
                page.evaluate("(" + rec.OVERLAY + ")()")
                page.wait_for_function("() => typeof window.__cap === 'function'")
            else:
                page.goto("file://" + url, wait_until="load")
            page.wait_for_timeout(700)

            cap = start_capture(dst)
            time.sleep(0.4)                       # let the first frames settle
            fn(page)
            page.wait_for_timeout(250)
            stop_capture(cap)

            dur = float(subprocess.run([FF, "-hide_banner", "-i", str(dst)],
                                       capture_output=True, text=True)
                        .stderr.split("Duration: ")[1].split(",")[0]
                        .split(":")[-1])
            marks.append({"name": name, "file": dst.name, "seconds": round(dur, 2)})
            print(f"  {name}: {dur:5.2f}s  {dst.stat().st_size/1024:6.0f} KB", flush=True)

        browser.close()          # detaches; the kiosk window keeps running

    # Merge, never overwrite: recording `01 03` to redo one beat must not drop
    # the other six from the timeline.
    meta = HERE / "video" / "beats.json"
    merged = {}
    if meta.exists():
        merged = {m["name"]: m for m in json.loads(meta.read_text())}
    merged.update({m["name"]: m for m in marks})
    out = [merged[k] for k in sorted(merged)]
    meta.write_text(json.dumps(out, indent=2) + "\n")
    print(f"\n{meta}  ({sum(m['seconds'] for m in marks):.2f}s total)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
