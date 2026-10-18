#!/usr/bin/env python3
"""Record the ShieldLint demo video, segment by segment.

    python demo/record.py

Each segment is a separate Playwright video (1600x900, 30 fps). `compose.sh`
stitches them into the final MP4. The browser segments drive the real site on
http://127.0.0.1:8010 — nothing is staged except the caption bar and the
on-screen cursor, which exist to make the clicks readable at video size.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
VID = HERE / "video"
VID.mkdir(parents=True, exist_ok=True)
SITE = "http://127.0.0.1:8010"
W, H = 1600, 900

UA = ("zu175e9thzutjjcqe9u3ca0n98msdagd8hp5vpl2zex065dzmmkf8pftgklq4upnrm"
      "5v3et4t89pffvat49xp3xw6mp2yzf9te8tjr7hhsz03x9w30vapxzh3u5eewdmrtc0"
      "7fsepvnarvvma9tvvuw3ke57unafx2tg9l728h3m5uhhle3")
URI_GOOD = ("zcash:" + UA + "?amount=0.5&memo=b3JkZXI6T1JELTIyOTE")
URI_BAD = "zcash:t1cN2ZVWzWcVRrnfeTvY3nBqXxLjHhBnGfW?amount=1&memo=b3JkZXI6MQ"

# injected into every page: a readable cursor + caption bar
OVERLAY = """
() => {
  const boot = () => {
  if (document.getElementById("demo-cursor")) return;
  const c = document.createElement("div");
  c.id = "demo-cursor";
  Object.assign(c.style, {
    position: "fixed", left: "0", top: "0", width: "22px", height: "22px",
    borderRadius: "50%", background: "rgba(42,91,255,.9)",
    border: "3px solid rgba(255,255,255,.92)",
    boxShadow: "0 0 0 8px rgba(42,91,255,.18), 0 6px 22px rgba(0,0,0,.55)",
    zIndex: 2147483647, pointerEvents: "none",
    transform: "translate(-50%,-50%) scale(1)",
    transition: "left .55s cubic-bezier(.22,.8,.24,1), top .55s cubic-bezier(.22,.8,.24,1), transform .12s ease",
  });
  // A parked cursor freezes the picture. Keep a very slow idle drift on the
  // dot so the frame is never byte-identical to the one before it: a static
  // tail is what reads as "the video stalled" even at a perfect 30 fps.
  const st = document.createElement("style");
  st.textContent = "@keyframes demoIdle{" +
    "0%{translate:0 0}25%{translate:5px -3px}50%{translate:1px -5px}" +
    "75%{translate:-4px -2px}100%{translate:0 0}}" +
    "#demo-cursor{animation:demoIdle 4.6s linear infinite}";
  document.head.appendChild(st);
  document.body.appendChild(c);

  const cap = document.createElement("div");
  cap.id = "demo-cap";
  Object.assign(cap.style, {
    position: "fixed", left: "50%", bottom: "40px", transform: "translateX(-50%) translateY(10px)",
    display: "inline-flex", alignItems: "center", gap: "10px",
    padding: "11px 20px", borderRadius: "999px",
    background: "rgba(9,12,18,.9)", border: "1px solid rgba(255,255,255,.13)",
    backdropFilter: "blur(14px)", color: "rgba(233,238,248,.85)",
    font: "15px ui-monospace,Menlo,Consolas,monospace", letterSpacing: ".01em",
    opacity: "0", transition: "opacity .4s ease, transform .4s ease",
    zIndex: 2147483646, pointerEvents: "none", whiteSpace: "nowrap",
    boxShadow: "0 20px 50px rgba(0,0,0,.5)",
  });
  cap.innerHTML = '<span style="width:6px;height:6px;border-radius:50%;background:#2a5bff;' +
                  'box-shadow:0 0 0 4px rgba(42,91,255,.18)"></span><span></span>';
  document.body.appendChild(cap);

  window.__point = (x, y) => {
    c.style.left = x + "px"; c.style.top = y + "px";
  };
  window.__press = () => {
    c.style.transform = "translate(-50%,-50%) scale(.78)";
    setTimeout(() => { c.style.transform = "translate(-50%,-50%) scale(1)"; }, 130);
  };
  window.__cap = (text) => {
    cap.lastChild.textContent = text;
    cap.style.opacity = "1"; cap.style.transform = "translateX(-50%) translateY(0)";
  };
  };
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
}
"""


def smooth_scroll(page, to: int, ms: int = 900) -> None:
    page.evaluate(
        """([to, ms]) => new Promise(r => {
            const from = window.scrollY, t0 = performance.now();
            const tick = (t) => {
                const k = Math.min(1, (t - t0) / ms);
                const e = 1 - Math.pow(1 - k, 3);
                window.scrollTo(0, from + (to - from) * e);
                if (k < 1) requestAnimationFrame(tick); else r();
            };
            requestAnimationFrame(tick);
        })""",
        [to, ms],
    )


def click_at(page, selector: str, hold: int = 260) -> None:
    el = page.wait_for_selector(selector, state="visible")
    box = el.bounding_box()
    x, y = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
    page.evaluate("([x,y]) => window.__point(x,y)", [x, y])
    page.wait_for_timeout(620)
    page.evaluate("() => window.__press()")
    page.wait_for_timeout(140)
    page.mouse.click(x, y)
    page.wait_for_timeout(hold)



def expect_result(page, selector: str, needle: str, retry=None) -> None:
    """Wait for a result panel to show `needle`; retry the action once if not."""
    try:
        page.wait_for_function(
            "([sel, n]) => { const e = document.querySelector(sel);"
            " return e && e.innerText.toLowerCase().includes(n.toLowerCase()); }",
            arg=[selector, needle], timeout=6000)
    except Exception:
        if retry:
            retry()
            page.wait_for_function(
                "([sel, n]) => { const e = document.querySelector(sel);"
                " return e && e.innerText.toLowerCase().includes(n.toLowerCase()); }",
                arg=[selector, needle], timeout=8000)
        else:
            raise


def record(name: str, fn, url: str | None = None) -> Path:
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox", "--force-color-profile=srgb"])
        ctx = browser.new_context(
            viewport={"width": W, "height": H},
            record_video_dir=str(VID),
            record_video_size={"width": W, "height": H},
            device_scale_factor=1,
            reduced_motion="no-preference",
        )
        page = ctx.new_page()
        if url and url.startswith("http"):
            page.add_init_script("(" + OVERLAY + ")()")
            page.goto(url, wait_until="networkidle")
            page.wait_for_function("() => typeof window.__cap === 'function'")
            page.wait_for_timeout(700)
        else:
            page.goto("file://" + str(url), wait_until="load")
            page.wait_for_timeout(500)
        fn(page)
        page.wait_for_timeout(400)
        video = page.video
        ctx.close()
        browser.close()
        path = Path(video.path())
        dst = VID / f"{name}.webm"
        shutil.move(str(path), dst)
        print(f"  {name}: {dst.stat().st_size/1024:.0f} KB")
        return dst


# ---------------------------------------------------------------- segments
def seg_title(page) -> None:
    page.wait_for_timeout(4600)


def seg_terminal(page) -> None:
    page.wait_for_timeout(500)
    page.evaluate("() => window.startDemo()")
    page.evaluate("() => window.showCap('A real CLI run — every line below is untouched output')")
    page.wait_for_timeout(1500)
    page.evaluate("() => window.showCap('14 rules · 0 runtime dependencies · no network at scan time')")
    page.wait_for_timeout(11000)
    page.evaluate("() => window.showCap('exit 1 — and CI stops here, before the code ships')")
    page.wait_for_timeout(5200)
    page.evaluate("() => window.showCap('The same flow, written correctly: clean')")
    page.wait_for_timeout(6000)


def seg_home(page) -> None:
    page.wait_for_timeout(2200)
    page.evaluate("() => window.__cap('ShieldLint — the privacy diagnostic Zcash was missing')")
    page.wait_for_timeout(2600)
    smooth_scroll(page, 780, 1100)
    page.wait_for_timeout(400)
    page.evaluate("() => window.__cap('Zcash privacy is opt-in. Code decides whether it happens.')")
    page.wait_for_timeout(3200)
    smooth_scroll(page, 0, 900)


def seg_scan(page) -> None:
    smooth_scroll(page, 560, 800)
    page.wait_for_timeout(500)
    page.evaluate("() => window.__cap('The same engine in the browser — nothing is stored')")
    page.wait_for_timeout(900)
    click_at(page, "#load-leaky")
    page.wait_for_timeout(900)
    page.evaluate("() => window.__cap('Load the leaky checkout, then scan')")
    click_at(page, "#do-scan", hold=400)
    page.wait_for_timeout(2600)
    page.evaluate("() => window.__cap('Rule, line, mechanism and fix — written for the person fixing it')")
    page.wait_for_timeout(5200)


def seg_address(page) -> None:
    smooth_scroll(page, 300, 800)
    page.wait_for_timeout(400)
    page.evaluate("() => window.__cap('Decode any address or viewing key offline')")
    page.fill("#addr", "")
    page.wait_for_timeout(300)
    page.type("#addr", UA, delay=3)
    page.wait_for_timeout(600)
    page.evaluate("() => window.__cap('ZIP 316 revision 2: Sapling + Orchard, no transparent receiver')")
    click_at(page, "#do-addr", hold=400)
    expect_result(page, "#addr-out", "shielded",
                  retry=lambda: (page.fill("#addr", UA), page.click("#do-addr")))
    page.wait_for_timeout(2400)
    page.evaluate("() => window.__cap('shielded: yes — nothing here can be downgraded to public')")
    page.wait_for_timeout(4200)


def seg_uri(page) -> None:
    smooth_scroll(page, 300, 800)
    page.wait_for_timeout(400)
    page.evaluate("() => window.__cap('Validate a ZIP 321 payment request')")
    page.fill("#uri", "")
    page.type("#uri", URI_GOOD, delay=2)
    page.wait_for_timeout(500)
    click_at(page, "#do-uri", hold=400)
    expect_result(page, "#uri-out", "valid request",
                  retry=lambda: (page.fill("#uri", URI_GOOD), page.click("#do-uri")))
    page.wait_for_timeout(2200)
    page.evaluate("() => window.__cap('Shielded recipient, 0.5 ZEC, 14-byte memo — valid')")
    page.wait_for_timeout(2600)
    page.evaluate("() => window.__cap('Now the same request against a transparent address…')")
    page.fill("#uri", "")
    page.type("#uri", URI_BAD, delay=2)
    page.wait_for_timeout(400)
    click_at(page, "#do-uri", hold=400)
    expect_result(page, "#uri-out", "rejected",
                  retry=lambda: (page.fill("#uri", URI_BAD), page.click("#do-uri")))
    page.wait_for_timeout(1800)
    page.evaluate("() => window.__cap('…rejected at the boundary, before a wallet ever sees it')")
    page.wait_for_timeout(4200)


def seg_rules(page) -> None:
    smooth_scroll(page, 560, 900)
    page.wait_for_timeout(600)
    page.evaluate("() => window.__cap('14 rules, each tied to a specification')")
    page.wait_for_timeout(2400)
    # open the first rule to show the explanation, not just the headline
    first = page.query_selector("#rules-out details")
    if first:
        box = first.bounding_box()
        page.evaluate("([x,y]) => window.__point(x,y)",
                      [box["x"] + 60, box["y"] + box["height"] / 2])
        page.wait_for_timeout(520)
        page.evaluate("() => window.__press()")
        page.wait_for_timeout(140)
        first.click()
        page.wait_for_timeout(900)
        smooth_scroll(page, 700, 700)
    page.evaluate("() => window.__cap('Why it leaks, and what to write instead — in the tool')")
    page.wait_for_timeout(3600)


def seg_end(page) -> None:
    page.wait_for_timeout(4600)


def main() -> None:
    only = set(sys.argv[1:])
    OUT.mkdir(exist_ok=True)

    def want(name: str) -> bool:
        return not only or any(name.split("-")[0] == o or name.split("-")[1] == o for o in only)

    print("recording…")
    if want("01-title"): record("01-title", seg_title, str(OUT / "title.html"))
    if want("02-home"): record("02-home", seg_home, SITE + "/")
    if want("03-terminal"): record("03-terminal", seg_terminal, str(OUT / "terminal.html"))
    if want("04-scan"): record("04-scan", seg_scan, SITE + "/scan")
    if want("05-address"): record("05-address", seg_address, SITE + "/address")
    if want("06-uri"): record("06-uri", seg_uri, SITE + "/uri")
    if want("07-rules"): record("07-rules", seg_rules, SITE + "/rules")
    if want("08-end"): record("08-end", seg_end, str(OUT / "end.html"))
    print("done")


if __name__ == "__main__":
    main()
