# Demo voiceover — script and timing

Target: `ShieldLint-demo.mp4`, **98.99 s**, 1600×900, 30 fps, captions burned in.
Beat boundaries (0.30 s cross-dissolve at each join): title 0.00 · home 5.23 ·
CLI 16.46 · scan 40.04 · address 53.77 · URI 65.50 · rules 82.73 · end 93.46.

Two rules for the voice: **only describe what is on screen at that moment**, and
only numbers the tool actually printed (8 errors / 10 warnings / 2 files /
exit 1; 14 rules; 7 error / 7 warning).

| # | Speech window | Lines |
|---|---------------|-------|
| 1 | 0.45 – 4.10 | Privacy has no compile error. ShieldLint finds the ones that leak. |
| 2 | 5.43 – 16.21 | Zcash is private per transaction, not by default. One transparent payout, or one memo in a log line, and the metadata is out. ShieldLint reads the codebase and shows you exactly where that happens. |
| 3 | 16.91 – 39.69 | Here it is on a realistic merchant checkout, run offline. Eight errors, ten warnings, across two files, exit code one. Each finding names the rule, the line, the mechanism and the fix: a transparent refund address held in a constant, a viewing key committed to source, a memo past the five hundred twelve byte limit. The fixed checkout comes back clean. |
| 4 | 40.49 – 52.56 | Same engine, in the browser. Load the leaky example, scan, and each finding states the consequence, not just the pattern. This memo is dropped, or leaks off-chain. Nothing is stored server side. |
| 5 | 53.97 – 65.25 | The address decoder does the real ZIP 316 work, F4Jumble included: every receiver, the revision, the expiry, and whether a sender can downgrade it to a transparent payment. |
| 6 | 65.70 – 82.49 | Then a payment request. This one is valid: shielded recipient, an amount, a base64url memo. This one is not, and it fails for the right reason. A memo attached to a transparent address, which ZIP 321 forbids. Every parameter checked against the grammar. |
| 7 | 82.93 – 93.22 | Fourteen rules, each tied to a specification, with the rationale and the remediation written for whoever has to fix the bug. Seven errors, seven warnings. |
| 8 | 93.91 – 98.29 | ShieldLint. Offline, MIT licensed, zero dependencies. |

Audio: stereo 48 kHz AAC 179 kbps, **−16.2 LUFS integrated**, true peak ≤ −1.5 dB.

## Why the picture was re-recorded

Playwright's own video recorder only emits a frame when the page repaints. The
first cut had **745 unique frames in 120 s** — about 6 per second — and 52
frozen stretches. Motion was sampled so sparsely that every scroll and typing
burst stepped, which reads as stuttering no matter how the file is encoded.

The demo is now captured from a real X display:

```
Xvfb :99 -screen 0 1600x900x24
Chromium --kiosk --app=http://127.0.0.1:8010/ --remote-debugging-port=9222
ffmpeg -f x11grab -framerate 30 -i :99.0
```

`record_screen.py` drives that window over CDP and `compose_screen.py`
concatenates the beats and emits `timeline.json`; `mix_voiceover.py` places the
voice on that timeline. Measured result: **14–15 unique frames per 0.5 s during
motion (28–30 fps)**, where the old recorder managed 5–7.

### No holds, no dead heads, no still frames

Three separate things were making the picture read as stalled, and each one was
measured before it was fixed.

1. **Freeze-holds.** The first cut padded every beat with `tpad=stop_mode=clone`
   so the narration would fit. The file was perfect CFR — 3428 frames, zero
   irregular deltas — and it still hitched at all eight cuts, because the picture
   stopped for 1–4 s while the voice kept going. Holds are gone; the mixer fits
   each line to its beat instead (≤0.25 s early start, ≤1.15× compression, loud
   failure if it still does not fit).
2. **A dead beat head.** The terminal stage starts its typewriter on
   `DOMContentLoaded`, so the first ~1.1 s of that capture is a near-black panel
   (YAVG flatlined at 24.775). Landing on the cut, it read as a black flash.
   `TRIM_HEAD` cuts 1.15 s off that beat, so it opens on the first prompt.
3. **A still picture.** This was the big one. On a screen recording the page
   simply does not move once the typing stops: measured on the flat cut, the
   **median frame had 4 pixels changing out of 230 000**, and half the runtime was
   a photograph of a page. Every static card, every idle tail, is a frozen image.

`demo/motion.py` gives every beat a continuous sub-pixel push-in (1.0 → 1.055,
1.11 over the long terminal beat), alternating direction so the scale is
continuous across each dissolve: the beat that ends pushed in meets a beat that
starts pushed in. `zoompan` was tried first and rejected — it crops in whole
pixels, so 129 of 330 frames came out on an identical crop and the picture
stepped once a second.

Measured on the shipped file, at 640×360, counting pixels that visibly change
between consecutive frames:

| | flat cut | shipped |
|---|---|---|
| median px changing / frame | 4 | **1223** |
| frames with < 50 px moving | 1435 | 3 |
| longest stretch with < 50 px moving | 6.40 s | **0.07 s** |

2970 frames, 0 irregular PTS deltas, keyframe every 2 s, `moov` before `mdat`.

Beats are also joined with a 0.30 s cross-dissolve rather than a hard cut: a cut
is one frame of complete stillness followed by a jump.

### Captions

`demo/captions.py` writes both the burned-in track and `demo/captions.srt`.
Cues are cut from the same script the voice reads and each one lives inside the
speech window `mix_voiceover.py` actually used (`video/vo-timings.json`), so a
caption cannot drift ahead of or behind the voice. 38 cues, ≤46 characters,
opaque plate so they read over the light sections too.

## Facts the script is allowed to state

- `examples/vulnerable-checkout` → **8 errors, 10 warnings, 0 notes, 2 files**, exit 1.
- `examples/clean-checkout` → no findings, exit 0.
- Rules: **14** total — 7 error, 7 warning.
- Findings on screen: SL002, SL003, SL006, SL007, SL009, SL010, SL011, SL012.
- Nothing is written server-side; the site makes zero third-party requests.

## Build

```
demo/build_stages.py      title/terminal/end cards from real CLI output
demo/record_screen.py     x11grab capture of the real site, one file per beat
demo/compose_screen.py    holds + concat -> take.mp4 + timeline.json
demo/mix_voiceover.py     voice onto the timeline, loudnorm, mux
```

The mixer keeps the picture as encoded by `compose_screen.py` (`-c:v copy`):
constant 30 fps, keyframe every 2 s, h264 High CRF 19. Lines start 0.45 s after
their cut, are pulled at most 0.25 s earlier, and are only sped up (≤1.15×) if
a line still overruns its slot.