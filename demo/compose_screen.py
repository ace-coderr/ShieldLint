#!/usr/bin/env python3
"""Stitch the screen-captured beats into one silent take with a known timeline.

Each beat may be held on its last frame so the narration has room: the result
is a constant-30-fps, keyframe-every-2s clip plus `demo/video/timeline.json`,
which `mix_voiceover.py` uses to place the voice.

    python3 demo/compose_screen.py
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import imageio_ffmpeg

HERE = Path(__file__).resolve().parent
SCREEN = HERE / "video" / "screen"
TAKE = HERE / "video" / "take.mp4"
TIMELINE = HERE / "video" / "timeline.json"
FF = imageio_ffmpeg.get_ffmpeg_exe()

# seconds of freeze-frame added after each beat (0 = none)
HOLD = {
    "01-title": 0.0,
    "02-home": 1.0,
    "03-terminal": 4.0,
    "04-scan": 2.5,
    "05-address": 2.5,
    "06-uri": 1.0,
    "07-rules": 1.0,
    "08-end": 0.0,
}


def main() -> int:
    beats = json.loads((HERE / "video" / "beats.json").read_text())
    inputs: list[str] = []
    chains: list[str] = []
    marks: list[dict] = []
    t = 0.0

    for i, b in enumerate(beats):
        src = SCREEN / b["file"]
        inputs += ["-i", str(src)]
        hold = HOLD.get(b["name"], 0.0)
        chains.append(
            f"[{i}:v]tpad=stop_mode=clone:stop_duration={hold},"
            f"setpts=PTS-STARTPTS,fps=30[v{i}]"
        )
        dur = b["seconds"] + hold
        marks.append({"name": b["name"], "start": round(t, 3),
                      "end": round(t + dur, 3), "seconds": round(dur, 3)})
        t += dur

    concat = "".join(f"[v{i}]" for i in range(len(beats))) + f"concat=n={len(beats)}:v=1:a=0[v]"
    subprocess.run(
        [FF, "-y", "-hide_banner", "-loglevel", "error", *inputs,
         "-filter_complex", ";".join(chains) + ";" + concat,
         "-map", "[v]", "-c:v", "libx264", "-preset", "medium", "-crf", "19",
         "-pix_fmt", "yuv420p", "-r", "30", "-fps_mode", "cfr",
         "-g", "60", "-keyint_min", "60", "-sc_threshold", "0",
         "-profile:v", "high", "-level", "4.1", str(TAKE)],
        check=True,
    )
    TIMELINE.write_text(json.dumps({"beats": marks, "total": round(t, 3)}, indent=2) + "\n")

    print(f"{TAKE}  ({t:.2f}s)")
    for m in marks:
        print(f"  {m['name']:12} {m['start']:6.2f} -> {m['end']:6.2f}  ({m['seconds']:.2f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
