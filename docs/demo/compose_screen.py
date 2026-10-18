#!/usr/bin/env python3
"""Stitch the screen-captured beats into one silent take with a known timeline.

Beats are joined with a short cross-dissolve instead of a hard cut. A cut is one
frame of complete stillness followed by a jump; on a screen recording that reads
as a skip. The dissolve keeps the picture in motion across the join.

The result is constant-30-fps, keyframe-every-2s, plus `demo/video/timeline.json`
(beat in/out points) which `mix_voiceover.py` uses to place the voice.

    python3 demo/compose_screen.py
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import imageio_ffmpeg

HERE = Path(__file__).resolve().parent
SCREEN = HERE / "video" / "screen"
# Motion-graded beats (see demo/motion.py); falls back to the raw capture.
MOTION = HERE / "video" / "motion"
TAKE = HERE / "video" / "take.mp4"
TIMELINE = HERE / "video" / "timeline.json"
FF = imageio_ffmpeg.get_ffmpeg_exe()

# Seconds to cut from the head of a segment. The terminal stage renders an
# empty panel for its first ~1.1 s (the typewriter starts on startDemo), which
# showed up as a black flash on the cut.
TRIM_HEAD = {"03-terminal": 1.15}

# No freeze-frames. Holding the last frame of a beat and then cutting reads as
# "hangs, then jumps" — every complaint landed on one of those holds.
HOLD = {k: 0.0 for k in (
    "01-title", "02-home", "03-terminal", "04-scan",
    "05-address", "06-uri", "07-rules", "08-end",
)}

# cross-dissolve between beats, seconds
XF = 0.30


def main() -> int:
    beats = json.loads((HERE / "video" / "beats.json").read_text())
    inputs: list[str] = []
    chains: list[str] = []
    durs: list[float] = []

    for i, b in enumerate(beats):
        graded = MOTION / b["file"]
        src = graded if graded.exists() else SCREEN / b["file"]
        inputs += ["-i", str(src)]
        hold = HOLD.get(b["name"], 0.0)
        head = TRIM_HEAD.get(b["name"], 0.0)
        chains.append(
            f"[{i}:v]trim=start={head},tpad=stop_mode=clone:stop_duration={hold},"
            f"setpts=PTS-STARTPTS,fps=30[v{i}]"
        )
        durs.append(b["seconds"] - head + hold)

    # [v0][v1]xfade -> [x1]; [x1][v2]xfade -> [x2]; ...
    prev = "v0"
    acc = durs[0]
    for i in range(1, len(beats)):
        out = f"x{i}"
        chains.append(
            f"[{prev}][v{i}]xfade=transition=fade:duration={XF}"
            f":offset={acc - XF:.3f}[{out}]"
        )
        acc += durs[i] - XF
        prev = out

    marks = []
    for i, (b, d) in enumerate(zip(beats, durs)):
        start = sum(durs[:i]) - XF * i
        marks.append({"name": b["name"], "start": round(start, 3),
                      "end": round(start + d, 3), "seconds": round(d, 3)})
    total = acc

    subprocess.run(
        [FF, "-y", "-hide_banner", "-loglevel", "error", *inputs,
         "-filter_complex", ";".join(chains),
         "-map", f"[{prev}]",
         "-c:v", "libx264", "-preset", "medium", "-crf", "19",
         "-pix_fmt", "yuv420p", "-r", "30", "-fps_mode", "cfr",
         "-g", "60", "-keyint_min", "60", "-sc_threshold", "0",
         "-profile:v", "high", "-level", "4.1", str(TAKE)],
        check=True,
    )
    TIMELINE.write_text(json.dumps({"beats": marks, "total": round(total, 3)}, indent=2) + "\n")

    print(f"{TAKE}  ({total:.2f}s)")
    for m in marks:
        print(f"  {m['name']:12} {m['start']:6.2f} -> {m['end']:6.2f}  ({m['seconds']:.2f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
