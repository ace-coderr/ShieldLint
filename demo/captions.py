#!/usr/bin/env python3
"""Burn captions into the narrated cut, timed off the real voice placement.

Cues are cut from the same script the voice reads, and every cue lives inside
the speech window that `mix_voiceover.py` actually used — so a caption can never
drift ahead of or behind the voice. Long lines are chunked by words and the
chunks are given duration in proportion to their length.

    python3 demo/captions.py                       # write demo/video/captions.ass
    python3 demo/captions.py --video in.mp4 --out out.mp4
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

import imageio_ffmpeg

HERE = Path(__file__).resolve().parent
TIMINGS = HERE / "video" / "vo-timings.json"
SCRIPT = HERE / "voiceover.md"
ASS_OUT = HERE / "video" / "captions.ass"
SRT_OUT = HERE / "captions.srt"      # tracked: sidecar subtitles for the repo
FF = imageio_ffmpeg.get_ffmpeg_exe()

W, H = 1600, 900
MAX_CHARS = 46          # a cue should read in one breath
MAX_WORDS = 8
MIN_CUE = 1.15          # seconds

HEADER = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,DejaVu Sans,32,&H00FFFFFF,&H00FFFFFF,&H38120C0A,&H38120C0A,-1,0,0,0,100,100,.2,0,3,11,0,2,190,190,136,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def ts(sec: float) -> str:
    if sec < 0:
        sec = 0.0
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h):d}:{int(m):02d}:{s:05.2f}"


def ts_srt(sec: float) -> str:
    if sec < 0:
        sec = 0.0
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{int(round((s % 1) * 1000)):03d}"


def read_script() -> dict[str, str]:
    """`| 3 | 18.51 - 46.70 | text |` rows from the voiceover table."""
    rows: dict[str, str] = {}
    for line in SCRIPT.read_text().splitlines():
        m = re.match(r"^\|\s*(\d+)\s*\|[^|]*\|\s*(.+?)\s*\|\s*$", line)
        if m:
            rows[m.group(1)] = m.group(2)
    return rows


def chunk(text: str) -> list[str]:
    """Break a line into short cues, preferring punctuation breaks."""
    words = text.split()
    out: list[str] = []
    cur: list[str] = []
    for w in words:
        trial = " ".join(cur + [w])
        if cur and (len(trial) > MAX_CHARS or len(cur) + 1 > MAX_WORDS):
            out.append(" ".join(cur))
            cur = [w]
        else:
            cur.append(w)
        if w.endswith((",", ".", ":", ";", "?")) and len(" ".join(cur)) > MAX_CHARS * 0.55:
            out.append(" ".join(cur))
            cur = []
    if cur:
        out.append(" ".join(cur))
    # do not leave a one-word orphan dangling off the previous cue
    if len(out) > 1 and len(out[-1].split()) == 1:
        out[-2] = out[-2] + " " + out.pop()
    return out


def cues() -> list[tuple[float, float, str]]:
    script = read_script()
    timings = json.loads(TIMINGS.read_text())
    out: list[tuple[float, float, str]] = []
    for t in timings:
        key = str(int(Path(t["clip"]).stem.split("-")[0]))   # 03-cli.mp3 -> "3"
        text = script.get(key)
        if not text:
            raise SystemExit(f"no script row for {t['clip']}")
        pieces = chunk(text)
        span = t["end"] - t["start"]
        weights = [max(len(p), 12) for p in pieces]
        total = sum(weights)
        at = t["start"]
        for piece, wgt in zip(pieces, weights):
            dur = max(MIN_CUE, span * wgt / total)
            out.append((at, min(at + dur, t["end"]), piece))
            at += span * wgt / total
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", type=Path)
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()

    lines = [HEADER]
    for start, end, text in cues():
        lines.append(f"Dialogue: 0,{ts(start)},{ts(end)},Cap,,0,0,0,,{text.replace('&', '&amp;')}")
    ASS_OUT.write_text("\n".join(lines) + "\n")

    all_cues = cues()
    srt = []
    for i, (start, end, text) in enumerate(all_cues, 1):
        srt.append(f"{i}\n{ts_srt(start)} --> {ts_srt(end)}\n{text}\n")
    SRT_OUT.write_text("\n".join(srt) + "\n")
    print(f"{ASS_OUT}  {SRT_OUT}  ({len(all_cues)} cues)")

    if a.video:
        out = a.out or a.video.with_name(a.video.stem + "-captioned.mp4")
        subprocess.run(
            [FF, "-y", "-hide_banner", "-loglevel", "error", "-i", str(a.video),
             "-vf", f"ass={ASS_OUT}", "-c:v", "libx264", "-preset", "medium",
             "-crf", "19", "-pix_fmt", "yuv420p", "-r", "30", "-fps_mode", "cfr",
             "-g", "60", "-keyint_min", "60", "-sc_threshold", "0",
             "-c:a", "copy", "-movflags", "+faststart", str(out)],
            check=True,
        )
        print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
