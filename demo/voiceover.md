# Demo voiceover — script and timing

Target: `ShieldLint-demo.mp4`, **119.77 s**, 1600×900.
Beat boundaries from the shipped cut: title 0:00 · home 0:05 · CLI 0:18 ·
scan 0:48 · address 1:05 · URI 1:21 · rules 1:43 · end 1:55.

Two rules for the voice: **only describe what is on screen at that moment**, and
only numbers the tool actually printed (8 errors / 10 warnings / 2 files /
exit 1; 14 rules; 7 error / 7 warning).

The first cut had gaps of 1.3–5.1 s between lines and read as broken audio, so
the script was rewritten to carry through each beat: no gap is longer than
~1.2 s, and every line starts *after* its visual cut.

| # | Speech window | Lines |
|---|---------------|-------|
| 1 | 0.45 – 4.10 | Privacy has no compile error. ShieldLint finds the ones that leak. |
| 2 | 5.19 – 17.75 | Zcash is private per transaction, not by default. One transparent payout, or one memo in a log line, and the metadata is out. ShieldLint reads the codebase and shows you exactly where that happens, before it ships. |
| 3 | 18.20 – 47.75 | Here it is on a realistic merchant checkout, run offline. No keys, no network, nothing executed. Eight errors, ten warnings, across two files, exit code one. Each finding names the rule, the line, the mechanism and the fix: a refund constant holding a transparent address, a viewing key committed to source, a spending key beside it, a memo past the five hundred twelve byte limit. The fixed checkout comes back clean. Deterministic, and clean on its own source. |
| 4 | 48.45 – 63.97 | Same engine, in the browser. Load the leaky example, scan, and each finding states the consequence, not just the pattern. This memo is dropped, or leaks off-chain. Every finding names the rule, the line and the fix. Nothing is stored server side. |
| 5 | 65.19 – 80.75 | The address decoder does the real ZIP 316 work, F4Jumble included. Every receiver inside a Unified Address, the revision, the expiry, and whether a sender can downgrade it to a transparent payment. Paste any address or viewing key. |
| 6 | 81.19 – 102.75 | Then a payment request. This one is valid: shielded recipient, an amount, a base64url memo. This one is not, and it fails for the right reason. A memo attached to a transparent address, which ZIP 321 forbids. Every parameter checked against the grammar. That is the check that stops a leaked invoice from reaching a customer. |
| 7 | 103.27 – 114.75 | Fourteen rules, each tied to a specification, with the rationale and the remediation written for whoever has to fix the bug. Seven errors, seven warnings. Filter and search without leaving the page. |
| 8 | 115.09 – 119.37 | ShieldLint. Offline, MIT licensed, zero dependencies. |

Audio: mono 48 kHz AAC 192 kbps, −16.4 dB mean, −0.7 dB peak.

## Facts the script is allowed to state

- `examples/vulnerable-checkout` → **8 errors, 10 warnings, 0 notes, 2 files**, exit 1.
- `examples/clean-checkout` → no findings, exit 0.
- Rules: **14** total — 7 error, 7 warning.
- Findings on screen: SL002, SL003, SL006, SL007, SL009, SL010, SL011, SL012.
- Nothing is written server-side; the site makes zero third-party requests.

## Build

```
demo/vo/nn-*.mp3         per-beat TTS clips (the only hand-made input)
demo/mix_voiceover.py    trim tail silence → place in slot → mix → mux
```

The mixer **re-encodes** the picture instead of stream-copying it. The recorded
master carries only **21 keyframes across 120 s** (one every ~5.7 s), which makes
players hang and skip whenever they seek or resume a buffer. The final encode is
h264 High, CRF 19, constant 30 fps, **keyframe every 2 s** (`-g 60
-keyint_min 60 -sc_threshold 0`), stereo 48 kHz AAC 192 kbps, `+faststart`.
SSIM against the master is 0.9993 — visually identical, but seekable: a seek
anywhere in the file resolves in ~55 ms.

Lines are placed after their cut, pulled at most 0.25 s earlier, and only sped
up (≤1.15×) if a line still overruns its slot.
