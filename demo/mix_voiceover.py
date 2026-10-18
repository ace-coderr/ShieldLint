#!/usr/bin/env python3
"""Mix the recorded narration onto the silent demo cut.

Each beat has a slot: it may start no earlier than the previous line finished
(+ a breath) and must end before the next visual cut. TTS clips vary in length
by a few hundred milliseconds, so this trims tail silence, then shifts a clip
earlier if it overruns — and only as a last resort speeds it up.

    python3 demo/mix_voiceover.py

Reads   demo/vo/NN-*.mp3
Writes  ../ShieldLint-demo-voiced.mp4
"""
from __future__ import annotations

import array
import subprocess
import sys
import wave
from pathlib import Path

import imageio_ffmpeg

HERE = Path(__file__).resolve().parent
VO = HERE / "vo"
VIDEO = HERE.parent.parent / "ShieldLint-demo.mp4"
OUT = HERE.parent.parent / "ShieldLint-demo-voiced.mp4"
SR = 48_000
FF = imageio_ffmpeg.get_ffmpeg_exe()

# (clip, slot start, hard stop = next visual cut)
BEATS = [
    ("01-title.mp3", 0.45, 5.0),
    ("02-home.mp3", 5.45, 18.0),
    ("03-cli.mp3", 18.45, 48.0),
    ("04-scan.mp3", 48.45, 65.0),
    ("05-address.mp3", 65.45, 81.0),
    ("06-uri.mp3", 81.45, 103.0),
    ("07-rules.mp3", 103.45, 115.0),
    ("08-end.mp3", 115.35, 119.62),
]
BREATH = 0.20          # minimum gap between two lines
MAX_TEMPO = 1.15       # never push the voice faster than this


def run(args: list[str]) -> None:
    subprocess.run(args, check=True, stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL)


def duration(path: Path) -> float:
    with wave.open(str(path)) as w:
        return w.getnframes() / w.getframerate()


def trim(src: Path, dst: Path, tempo: float = 1.0) -> None:
    """Decode to 48 kHz mono, cut leading/trailing silence, optional tempo."""
    # stop_periods stops writing at the first internal pause, so trim the tail
    # by reversing: head-trim, reverse, head-trim, reverse.
    af = (
        "silenceremove=start_periods=1:start_duration=0.05:start_threshold=-45dB,"
        "areverse,"
        "silenceremove=start_periods=1:start_duration=0.30:start_threshold=-45dB,"
        "areverse"
    )
    if tempo > 1.0:
        af += f",atempo={tempo:.4f}"
    run([FF, "-y", "-i", str(src), "-af", af, "-ac", "1", "-ar", str(SR),
         str(dst)])


def video_length() -> float:
    out = subprocess.run([FF, "-hide_banner", "-i", str(VIDEO)],
                         capture_output=True, text=True).stderr
    stamp = out.split("Duration: ")[1].split(",")[0]
    h, m, s = stamp.split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def main() -> int:
    total = video_length()
    n = int(round(total * SR))
    track = array.array("h", bytes(2 * n))          # silence, 16-bit mono

    prev_end = 0.0
    for name, slot, stop in BEATS:
        src = VO / name
        tmp = VO / (name + ".wav")
        stop -= 0.25                                # never slam into the cut
        trim(src, tmp)
        dur = duration(tmp)
        start = slot
        if start + dur > stop:                      # nudge earlier, 0.25 s max
            start = max(prev_end + BREATH, slot - 0.25, stop - dur)
        if start + dur > stop:                      # still long: lift the tempo
            tempo = min(MAX_TEMPO, dur / (stop - start))
            trim(src, tmp, tempo)
            dur = duration(tmp)
            start = max(prev_end + BREATH, stop - dur)
        if start < prev_end + 0.05:                 # never overlap
            print(f"  !! {name} collides with the previous line", file=sys.stderr)
        off = int(round(start * SR))
        with wave.open(str(tmp)) as w:
            samples = array.array("h", w.readframes(w.getnframes()))
        for i, s in enumerate(samples):
            j = off + i
            if j >= n:
                break
            v = track[j] + s
            track[j] = 32767 if v > 32767 else (-32768 if v < -32768 else v)
        prev_end = start + dur
        print(f"  {name:14} {dur:5.2f}s  at {start:6.2f}s  ends {start + dur:6.2f}s "
              f"(cut {stop:6.2f})")

    peak = max(abs(min(track)), abs(max(track))) or 1
    if peak > 29_000:                               # headroom to ~-1 dBFS
        gain = 29_000 / peak
        track = array.array("h", (int(s * gain) for s in track))
        print(f"  peak {peak} -> scaled by {gain:.3f}")

    mixed = VO / "_mix.wav"
    with wave.open(str(mixed), "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(track.tobytes())

    # TTS lands around -20 dB mean; lift it to web level and catch the peaks.
    loud = "volume=3dB,alimiter=limit=0.891:attack=5:release=80:level=disabled"
    run([FF, "-y", "-i", str(VIDEO), "-i", str(mixed),
         "-map", "0:v:0", "-map", "1:a:0",
         "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
         "-af", loud, "-movflags", "+faststart", "-shortest", str(OUT)])

    out_len = subprocess.run([FF, "-hide_banner", "-i", str(OUT)],
                             capture_output=True, text=True).stderr
    print("\n" + str(OUT))
    print([ln for ln in out_len.splitlines() if "Duration" in ln][0].strip())
    print([ln for ln in out_len.splitlines() if "Stream #0:1" in ln][0].strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
