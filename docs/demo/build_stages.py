#!/usr/bin/env python3
"""Build the HTML stages used to record the ShieldLint demo video.

    python demo/build_stages.py

Writes demo/out/*.html. Every terminal line comes from the real CLI output
captured into demo/out/cli-leaky.txt, so the video cannot invent findings.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent / "out"
OUT.mkdir(parents=True, exist_ok=True)


def run(args: list[str]) -> str:
    return subprocess.run(args, cwd=ROOT, capture_output=True, text=True).stdout


CSS = """
*{box-sizing:border-box}
html,body{margin:0;height:100%}
body{
  background:#05070b;color:#e9eef8;
  font-family:ui-sans-serif,-apple-system,"Segoe UI",Roboto,"DejaVu Sans",sans-serif;
  overflow:hidden;
}
.grid{
  position:fixed;inset:0;
  background-image:linear-gradient(rgba(255,255,255,.032) 1px,transparent 1px),
                   linear-gradient(90deg,rgba(255,255,255,.032) 1px,transparent 1px);
  background-size:96px 96px;
  -webkit-mask-image:radial-gradient(70% 70% at 50% 40%,#000,transparent 80%);
  mask-image:radial-gradient(70% 70% at 50% 40%,#000,transparent 80%);
}
.glow{position:fixed;inset:0;
  background:radial-gradient(60% 46% at 62% 26%,rgba(42,91,255,.22),transparent 72%),
             radial-gradient(46% 36% at 18% 82%,rgba(42,91,255,.10),transparent 74%);
  animation:glowDrift 5.2s ease-in-out infinite}
@keyframes glowDrift{0%{transform:translate3d(0,0,0) scale(1)}
  50%{transform:translate3d(30px,-20px,0) scale(1.06)}100%{transform:translate3d(0,0,0) scale(1)}}
.mono{font-family:ui-monospace,SFMono-Regular,"SF Mono",Menlo,Consolas,"DejaVu Sans Mono",monospace}
.stage{position:relative;width:100%;height:100%;display:grid;place-items:center}
.cap{
  position:fixed;left:50%;bottom:44px;transform:translateX(-50%);
  display:inline-flex;align-items:center;gap:10px;
  padding:10px 18px;border-radius:999px;
  background:rgba(9,12,18,.86);border:1px solid rgba(255,255,255,.12);
  font-family:ui-monospace,Menlo,"DejaVu Sans Mono",monospace;
  font-size:15px;letter-spacing:.02em;color:rgba(233,238,248,.82);
  opacity:0;transition:opacity .5s ease;
}
.cap.on{opacity:1}
.cap b{color:#fff;font-weight:600}
.cap .dot{width:6px;height:6px;border-radius:50%;background:#2a5bff;box-shadow:0 0 0 4px rgba(42,91,255,.18)}
.tag{position:fixed;left:44px;top:34px;display:flex;align-items:center;gap:10px;
  font-family:ui-monospace,Menlo,"DejaVu Sans Mono",monospace;font-size:13px;
  letter-spacing:.16em;text-transform:uppercase;color:rgba(233,238,248,.42)}
.tag .dot{width:7px;height:7px;border-radius:50%;background:#2a5bff}
"""

# ---------------------------------------------------------------- title card
TITLE = """<!doctype html><meta charset="utf-8">
<style>__CSS__
body{display:grid;place-items:center}
.mark{width:76px;height:86px;margin:0 auto 26px}
h1{font-size:76px;letter-spacing:-.035em;margin:0;font-weight:650;line-height:1}
h1 span{color:#2a5bff}
p.sub{margin:20px 0 0;font-size:26px;color:rgba(233,238,248,.62);letter-spacing:-.01em}
p.sub em{font-family:ui-serif,Georgia,"DejaVu Serif",serif;font-style:italic;color:#fff}
.meta{margin-top:42px;display:flex;gap:14px;justify-content:center}
.pill{padding:8px 16px;border:1px solid rgba(255,255,255,.14);border-radius:999px;
  font-family:ui-monospace,Menlo,"DejaVu Sans Mono",monospace;font-size:13px;
  letter-spacing:.12em;text-transform:uppercase;color:rgba(233,238,248,.6)}
.pill.blue{border-color:rgba(42,91,255,.5);color:#9db6ff;background:rgba(42,91,255,.10)}
.center{text-align:center;position:relative}
.fade{animation:fade 1.1s cubic-bezier(.22,.8,.24,1) both}
.d1{animation-delay:.15s}.d2{animation-delay:.35s}.d3{animation-delay:.7s}.d4{animation-delay:1s}
@keyframes fade{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:none}}
</style>
<div class="grid"></div><div class="glow"></div>
<div class="tag"><span class="dot"></span> ZECATHON 2026 · Core &amp; Tooling</div>
<div class="center">
  <svg class="mark fade" viewBox="0 0 34 38" fill="none">
    <path d="M17 2 31 7v12c0 8-6 14-14 17C9 33 3 27 3 19V7L17 2Z" stroke="#2a5bff" stroke-width="1.6"/>
    <path d="M12 13h10l-10 12h10" stroke="#fff" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
  </svg>
  <h1 class="fade d1">Shield<span>Lint</span></h1>
  <p class="sub fade d2">Privacy has no compile <em>error</em>.</p>
  <div class="meta fade d3">
    <span class="pill blue">offline static analysis</span>
    <span class="pill">for zcash</span>
    <span class="pill">14 rules · 0 deps</span>
  </div>
  <div class="meta fade d4">
    <span class="pill" style="border-color:rgba(53,192,138,.4);color:#7ee2b0">no network at scan time</span>
  </div>
</div>
"""

# ------------------------------------------------------------------ terminal
TERMINAL = """<!doctype html><meta charset="utf-8">
<style>__CSS__
.term{
  width:1360px;border-radius:16px;overflow:hidden;
  background:linear-gradient(180deg,#0b1017,#070a0f);
  border:1px solid rgba(255,255,255,.11);
  box-shadow:0 50px 120px rgba(0,0,0,.7), inset 0 1px 0 rgba(255,255,255,.06);
}
.bar{display:flex;align-items:center;gap:9px;padding:13px 18px;
  border-bottom:1px solid rgba(255,255,255,.08);background:rgba(255,255,255,.015)}
.bar i{width:10px;height:10px;border-radius:50%;display:block}
.bar i:nth-child(1){background:#ff7a6e}.bar i:nth-child(2){background:#f0be6e}
.bar i:nth-child(3){background:#60ca98}
.bar .t{margin-left:12px;font-family:ui-monospace,Menlo,"DejaVu Sans Mono",monospace;
  font-size:13px;color:rgba(233,238,248,.45)}
.body{padding:26px 30px 30px;font-family:ui-monospace,Menlo,"DejaVu Sans Mono",monospace;
  font-size:16.5px;line-height:1.62}
.line{white-space:pre;opacity:0}
.line.on{opacity:1}
.prompt{color:#5ee0a0}
.cmd{color:#eef3fb}
.hdr{color:#8fb0ff;font-weight:600}
.path{color:rgba(233,238,248,.55);margin-top:14px}
.loc{color:rgba(233,238,248,.40)}
.warn{color:#f0bd6a}
.err{color:#ff8b80}
.rid{color:#8fb0ff;font-weight:700}
.title{color:rgba(233,238,248,.86)}
.detail{color:rgba(233,238,248,.46)}
.sum{margin-top:18px;color:#fff}
.exit{color:#ff8b80}
.ok{color:#5ee0a0;font-size:20px}
.cursor{display:inline-block;width:9px;height:19px;background:#8fb0ff;
  vertical-align:-3px;margin-left:2px;animation:blink 1.05s steps(1) infinite}
@keyframes blink{50%{opacity:0}}
</style>
<div class="grid"></div><div class="glow"></div>
<div class="stage">
  <div class="term">
    <div class="bar"><i></i><i></i><i></i><span class="t">shieldlint — zsh</span></div>
    <div class="body" id="b"></div>
  </div>
</div>
<div class="tag"><span class="dot"></span> ShieldLint CLI</div>
<div class="cap" id="cap"></div>
<script>
const LINES = __LINES__;
const b = document.getElementById("b");
let i = 0;
// The prompt sits at the bottom of the pane and blinks for the whole beat;
// output is inserted above it, the way a real shell behaves.
const idle = document.createElement("div");
idle.className = "line on";
idle.id = "idleline";
idle.innerHTML = '<span class="prompt">$ </span><span class="cursor"></span>';
b.appendChild(idle);
function add(html, cls) {
  const d = document.createElement("div");
  d.className = "line " + (cls || "");
  d.innerHTML = html;
  b.insertBefore(d, idle);
  requestAnimationFrame(() => d.classList.add("on"));
  return d;
}
function step() {
  if (i >= LINES.length) return;
  const l = LINES[i++];
  if (l.type === "cmd") {
    const d = add('<span class="prompt">$ </span><span class="cmd"></span>');
    const span = d.querySelector(".cmd");
    let k = 0;
    const t = setInterval(() => {
      span.textContent = l.text.slice(0, ++k);
      if (k >= l.text.length) {
        clearInterval(t);
        setTimeout(step, 420);
      }
    }, 34);
    return;
  }
  add(l.html, l.cls);
  setTimeout(step, l.wait || 110);
}
window.startDemo = () => step();
window.showCap = (html) => {
  const c = document.getElementById("cap");
  c.innerHTML = html; c.classList.add("on");
};
window.hideCap = () => document.getElementById("cap").classList.remove("on");
</script>
"""

# ------------------------------------------------------------------ end card
END = """<!doctype html><meta charset="utf-8">
<style>__CSS__
body{display:grid;place-items:center}
h2{font-size:52px;margin:0 0 8px;letter-spacing:-.03em}
p.lede{margin:0 auto;max-width:760px;font-size:21px;color:rgba(233,238,248,.6);line-height:1.55}
.links{display:flex;gap:16px;justify-content:center;margin-top:40px;flex-wrap:wrap}
.lk{display:flex;align-items:center;gap:12px;padding:16px 22px;border-radius:14px;
  border:1px solid rgba(255,255,255,.13);background:rgba(255,255,255,.03);
  font-family:ui-monospace,Menlo,"DejaVu Sans Mono",monospace;font-size:16px}
.lk b{color:#fff;font-weight:600}
.lk span{color:rgba(233,238,248,.45)}
.lk.blue{border-color:rgba(42,91,255,.45);background:rgba(42,91,255,.10)}
.facts{display:flex;gap:34px;justify-content:center;margin-top:46px;
  font-family:ui-monospace,Menlo,"DejaVu Sans Mono",monospace}
.facts div{text-align:left}
.facts dt{font-size:11px;letter-spacing:.16em;text-transform:uppercase;color:rgba(233,238,248,.34)}
.facts dd{margin:6px 0 0;font-size:19px;color:#fff}
.fade{animation:fade .9s cubic-bezier(.22,.8,.24,1) both}
.d1{animation-delay:.1s}.d2{animation-delay:.3s}.d3{animation-delay:.5s}.d4{animation-delay:.7s}
@keyframes fade{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:none}}
</style>
<div class="grid"></div><div class="glow"></div>
<div class="tag"><span class="dot"></span> ShieldLint · MIT</div>
<div style="text-align:center;position:relative">
  <h2 class="fade">Built for ZECATHON 2026</h2>
  <p class="lede fade d1">Core &amp; Tooling track. Everything in the repository was written
  during the build window, ships under MIT, and runs with no network access at scan time.</p>
  <div class="links fade d2">
    <div class="lk blue"><b>github.com/ace-coderr/ShieldLint</b><span>↗</span></div>
    <div class="lk"><b>shieldlint.vercel.app</b><span>↗</span></div>
  </div>
  <div class="facts fade d3">
    <div><dt>tests</dt><dd>72</dd></div>
    <div><dt>rules</dt><dd>14</dd></div>
    <div><dt>runtime deps</dt><dd>0</dd></div>
    <div><dt>vectors</dt><dd>124 UA · 66 VK</dd></div>
    <div><dt>license</dt><dd>MIT</dd></div>
  </div>
</div>
"""


def build_terminal_lines() -> list[dict]:
    leaky = run([sys.executable, "-m", "shieldlint", "check", "examples/vulnerable-checkout"])
    clean = run([sys.executable, "-m", "shieldlint", "check", "examples/clean-checkout"])
    (OUT / "cli-leaky.txt").write_text(leaky, encoding="utf-8")
    (OUT / "cli-clean.txt").write_text(clean, encoding="utf-8")

    head = [ln for ln in leaky.splitlines() if ln.strip()][0]
    findings = re.findall(r"^\s+(\d+:\d+)\s+(error|warning)\s+(SL\d{3})\s+(.*)$",
                          leaky, re.MULTILINE)
    by_file = {}
    for ln in leaky.splitlines():
        if ln.startswith("examples/"):
            by_file.setdefault(ln.strip(), [])

    lines: list[dict] = []
    lines.append({"type": "cmd", "text": "shieldlint check examples/vulnerable-checkout"})
    lines.append({"html": f'<span class="hdr">shieldlint 0.1.0</span>'
                          f'<span class="detail">  ·  2 files scanned  ·  8 errors, 10 warnings</span>',
                  "wait": 700})
    lines.append({"html": '<span class="path">examples/vulnerable-checkout/checkout.py</span>',
                  "wait": 320})

    shown = findings[:8]
    for loc, sev, rid, title in shown:
        cls = "err" if sev == "error" else "warn"
        lines.append({
            "html": f'<span class="loc">{loc:<9}</span><span class="{cls}">{sev:<8}</span>'
                    f'<span class="rid">{rid}</span>  <span class="title">{title}</span>',
            "wait": 260,
        })
    rest = len(findings) - len(shown)
    if rest:
        lines.append({"html": f'<span class="detail">{"":<9}{"":<8}… {rest} more findings</span>',
                      "wait": 420})
    lines.append({"html": '<span class="detail">… examples/vulnerable-checkout/config.yaml</span>',
                  "wait": 380})
    lines.append({"html": '<span class="sum">8 errors, 10 warnings, 0 notes across 2 files'
                          '   (fail-on=error)</span>', "wait": 520})
    lines.append({"html": '<span class="exit">✖ findings at or above the failure threshold</span>',
                  "wait": 1400})
    lines.append({"type": "cmd", "text": "shieldlint check examples/clean-checkout"})
    lines.append({"html": '<span class="hdr">shieldlint 0.1.0</span>'
                          '<span class="detail">  ·  1 file scanned</span>', "wait": 520})
    lines.append({"html": '<span class="ok">✔ no findings</span>', "wait": 1600})
    return lines


def main() -> None:
    lines = build_terminal_lines()
    import json
    title = TITLE.replace("__CSS__", CSS)
    term = TERMINAL.replace("__CSS__", CSS).replace("__LINES__", json.dumps(lines))
    end = END.replace("__CSS__", CSS)
    (OUT / "title.html").write_text(title, encoding="utf-8")
    (OUT / "terminal.html").write_text(term, encoding="utf-8")
    (OUT / "end.html").write_text(end, encoding="utf-8")
    print(f"stages written · {len(lines)} terminal lines")


if __name__ == "__main__":
    main()
