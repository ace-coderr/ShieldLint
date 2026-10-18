# Demo voiceover — script and timing

Target: `ShieldLint-demo.mp4`, **101.09 s**, 1600×900, 30 fps.
Beat boundaries: title 0.00 · home 5.53 · CLI 17.06 · scan 40.94 · address
54.97 · URI 67.00 · rules 84.53 · end 95.56.

Two rules for the voice: **only describe what is on screen at that moment**, and
only numbers the tool actually printed (8 errors / 10 warnings / 2 files /
exit 1; 14 rules; 7 error / 7 warning).

| # | Speech window | Lines |
|---|---------------|-------|
| 1 | 0.45 – 4.10 | Privacy has no compile error. ShieldLint finds the ones that leak. |
| 2 | 5.73 – 16.82 | Zcash is private per transaction, not by default. One transparent payout, or one memo in a log line, and the metadata is out. ShieldLint reads the codebase and shows you exactly where that happens. |
| 3 | 17.51 – 40.29 | Here it is on a realistic merchant checkout, run offline. Eight errors, ten warnings, across two files, exit code one. Each finding names the rule, the line, the mechanism and the fix: a transparent refund address held in a constant, a viewing key committed to source, a memo past the five hundred twelve byte limit. The fixed checkout comes back clean. |
| 4 | 41.39 – 53.46 | Same engine, in the browser. Load the leaky example, scan, and each finding states the consequence, not just the pattern. This memo is dropped, or leaks off-chain. Nothing is stored server side. |
| 5 | 55.17 – 66.75 | The address decoder does the real ZIP 316 work, F4Jumble included: every receiver, the revision, the expiry, and whether a sender can downgrade it to a transparent payment. |
| 6 | 67.20 – 84.28 | Then a payment request. This one is valid: shielded recipient, an amount, a base64url memo. This one is not, and it fails for the right reason. A memo attached to a transparent address, which ZIP 321 forbids. Every parameter checked against the grammar. |
| 7 | 84.73 – 95.32 | Fourteen rules, each tied to a specification, with the rationale and the remediation written for whoever has to fix the bug. Seven errors, seven warnings. |
| 8 | 96.01 – 100.39 | ShieldLint. Offline, MIT licensed, zero dependencies. |

Audio: stereo 48 kHz AAC 192 kbps, **−16.2 LUFS integrated**, true peak ≤ −1.5 dB.

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

### No holds, no dead heads

The picture is no longer padded with `tpad` freeze-frames. A perfectly constant
30 fps file still looked like it stuttered when the last frame of a beat was
cloned for 1–4 s while the narration kept going: the cut was in the voice, not
in the file. The mixer now fits each line into its beat instead — a line starts
at most 0.25 s before its cue, and if it still does not fit it is time-compressed
to at most 1.15×. Anything longer is a script bug, and the mixer fails loudly.

The terminal beat also opened on an empty panel: the stage page starts its
typewriter on `DOMContentLoaded`, so the first ~0.9 s of the capture is
near-black. `TRIM_HEAD` in `compose_screen.py` cuts 1.15 s off that beat, and
the beat now opens on the first command prompt. Beat boundaries are audited by
pulling frames ±0.15 s around every cut and checking none of them is blank.

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
