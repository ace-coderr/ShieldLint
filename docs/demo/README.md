# The demonstration video

`ShieldLint-demo.mp4` at the repository root is **1:39**, narrated and captioned.
This directory is the toolchain that produced it.

It is checked in on purpose. Every finding that appears on screen came out of the
real CLI or the real web app — nothing is mocked, staged or typed by hand. The
scripts below are the proof of that, and they rebuild the video byte-for-byte
from the same captured frames.

```
build_stages.py     terminal + title/end cards rendered from real CLI output
record.py           the beats: what gets clicked, scrolled and typed
record_screen.py    30 fps capture from a real X display over CDP
motion.py           sub-pixel push-in so the picture is never a still frame
compose_screen.py   cross-dissolve the beats, emit timeline.json
mix_voiceover.py    place the narration on that timeline, master the audio
captions.py         burned-in captions + captions.srt
build_demo.sh       all of the above, in order
voiceover.md        the script, the measured timings, and the reasoning
```

`captions.srt` is the subtitle sidecar for the published video.

## Why the picture was rebuilt

Three separate things made earlier cuts read as stuttering, and each one was
measured before it was fixed:

1. **Freeze-holds.** Padding a beat with its own last frame so the narration fits
   produced a perfect constant-30-fps file that still hitched at every cut — the
   picture stopped for 1–4 s while the voice kept going. Holds are gone; the
   mixer fits each line to its beat instead.
2. **A dead beat head.** The terminal stage starts typing on `DOMContentLoaded`,
   so the first ~1.1 s of that capture is an empty panel. Trimmed, so the beat
   opens on the first prompt.
3. **A still picture.** This was the big one. A screen recording of a web page is
   mostly a photograph: on the flat cut the median frame had **4 pixels changing
   out of 230 000**. `motion.py` gives every beat a continuous sub-pixel push-in;
   the median is now **1223 px/frame** and the longest still stretch is 0.07 s,
   down from 6.40 s.

Full measurements are in [voiceover.md](voiceover.md).

## Rebuilding

Captured frames are not committed (they are large and reproducible). To rebuild
from beats you already have:

```bash
./docs/demo/build_demo.sh
```

To re-capture as well, you need an X display and a kiosk Chromium — see the
header of `record_screen.py`.
