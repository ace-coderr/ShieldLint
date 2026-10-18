# Demo voiceover — script and timing

Target: `ShieldLint-demo-final.mp4`, **114.30 s**, 1600×900, 30 fps.
Beat boundaries: title 0.00 · home 5.53 · CLI 18.06 · scan 47.09 · address
63.62 · URI 78.15 · rules 96.68 · end 108.71.

Two rules for the voice: **only describe what is on screen at that moment**, and
only numbers the tool actually printed (8 errors / 10 warnings / 2 files /
exit 1; 14 rules; 7 error / 7 warning).

| # | Speech window | Lines |
|---|---------------|-------|
| 1 | 0.45 – 4.10 | Privacy has no compile error. ShieldLint finds the ones that leak. |
| 2 | 5.98 – 17.59 | Zcash is private per transaction, not by default. One transparent payout, or one memo in a log line, and the metadata is out. ShieldLint reads the codebase and shows you exactly where that happens. |
| 3 | 18.51 – 46.70 | Here it is on a realistic merchant checkout, run offline. No keys, no network, nothing executed. Eight errors, ten warnings, across two files, exit code one. Each finding names the rule, the line, the mechanism and the fix: a refund constant holding a transparent address, a viewing key committed to source, a spending key beside it, a memo past the five hundred twelve byte limit. The fixed checkout comes back clean. |
| 4 | 47.54 – 63.06 | Same engine, in the browser. Load the leaky example, scan, and each finding states the consequence, not just the pattern. This memo is dropped, or leaks off-chain. Every finding names the rule, the line and the fix. Nothing is stored server side. |
| 5 | 64.07 – 77.84 | The address decoder does the real ZIP 316 work, F4Jumble included. Every receiver inside a Unified Address, the revision, the expiry, and whether a sender can downgrade it to a transparent payment. |
| 6 | 78.60 – 95.85 | Then a payment request. This one is valid: shielded recipient, an amount, a base64url memo. This one is not, and it fails for the right reason. A memo attached to a transparent address, which ZIP 321 forbids. Every parameter checked against the grammar. |
| 7 | 96.98 – 108.46 | Fourteen rules, each tied to a specification, with the rationale and the remediation written for whoever has to fix the bug. Seven errors, seven warnings. |
| 8 | 109.16 – 113.54 | ShieldLint. Offline, MIT licensed, zero dependencies. |

Audio: stereo 48 kHz AAC 192 kbps, **−16.3 LUFS integrated**, true peak ≤ −1.5 dB.

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

`record_screen.py` drives that window over CDP, `compose_screen.py` holds the
last frame of each beat to give the narration room and emits `timeline.json`,
and `mix_voiceover.py` places the voice on that timeline. Measured result:
**14–15 unique frames per 0.5 s during motion (28–30 fps)**, where the old
recorder managed 5–7.

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
