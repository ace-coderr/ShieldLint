/* ShieldLint UI — nav, copy buttons, scanner, decoder, URI validator, rules. */
// shieldlint: disable-file -- sample addresses and invalid URIs are demo fixtures

(function () {
  "use strict";

  var $ = function (id) { return document.getElementById(id); };
  var esc = function (s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  };

  /* ---------------------------------------------------------------- nav */
  var toggle = $("nav-toggle");
  var links = $("nav-links");
  if (toggle && links) {
    toggle.addEventListener("click", function () {
      var open = links.classList.toggle("open");
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
    });
    links.addEventListener("click", function (e) {
      if (e.target.tagName === "A") { links.classList.remove("open"); }
    });
  }

  /* ------------------------------------------------------- copy buttons */
  document.addEventListener("click", function (e) {
    var btn = e.target.closest("[data-copy]");
    if (!btn) return;
    var block = btn.closest("pre");
    if (!block) return;
    var text = block.cloneNode(true);
    var b = text.querySelector(".copy");
    if (b) b.remove();
    var body = text.textContent.replace(/^\s+|\s+$/g, "");
    var done = function () {
      btn.textContent = "Copied";
      setTimeout(function () { btn.textContent = "Copy"; }, 1400);
    };
    if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard.writeText(body).then(done, done);
    } else {
      var ta = document.createElement("textarea");
      ta.value = body; ta.style.position = "fixed"; ta.style.opacity = "0";
      document.body.appendChild(ta); ta.select();
      try { document.execCommand("copy"); } catch (err) {}
      document.body.removeChild(ta); done();
    }
  });

  /* -------------------------------------------------------------- api */
  function post(url, body) {
    return fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    }).then(function (res) {
      return res.json().catch(function () { return {}; }).then(function (data) {
        if (!res.ok) throw new Error(data.detail || ("HTTP " + res.status));
        return data;
      });
    });
  }

  function getJSON(url) {
    return fetch(url).then(function (res) {
      if (!res.ok) throw new Error("HTTP " + res.status);
      return res.json();
    });
  }

  function loading(el, label) {
    el.innerHTML = '<p class="small"><span class="spin"></span> ' + esc(label) + "</p>";
  }

  function error(el, message) {
    el.innerHTML = '<div class="banner" style="border-color:#f6d7d3;background:var(--red-wash);color:var(--red)">' +
      '<svg aria-hidden="true"><use href="#i-alert"/></svg><div>' + esc(message) + "</div></div>";
  }

  var RULE_INFO = null;
  function loadRuleInfo() {
    if (RULE_INFO) return Promise.resolve(RULE_INFO);
    return getJSON("/api/rules").then(function (data) {
      RULE_INFO = {};
      (data.rules || []).forEach(function (r) { RULE_INFO[r.id] = r; });
      return RULE_INFO;
    }).catch(function () { RULE_INFO = {}; return RULE_INFO; });
  }

  var EXAMPLES = {
    ua: "zu175e9thzutjjcqe9u3ca0n98msdagd8hp5vpl2zex065dzmmkf8pftgklq4upnrm5v3et4t89pffvat49xp3xw6mp2yzf9te8tjr7hhsz03x9w30vapxzh3u5eewdmrtc07fsepvnarvvma9tvvuw3ke57unafx2tg9l728h3m5uhhle3",
    mixed: "u1pg2aaph7jp8rpf6yhsza25722sg5fcn3vaca6ze27hqjw7jvvhhuxkpcg0ge9xh6drsgdkda8qjq5chpehkcpxf87rnjryjqwymdheptpvnljqqrjqzjwkc2ma6hcq666kgwfytxwac8eyex6ndgr6ezte66706e3vaqrd25dzvzkc69kw0jgywtd0cmq52q5lkw6uh7hyvzjse8ksx",
    sapling: "zs1mrhc9n8v8p9ukv0f8lqz9m7rj7fxd6fhnrr4f2wq7vqvxqzg6xkf3fkg3kq3e0g8m8xpx4v0jqk6m0ru2n7j8l7dwkwn",
    taddr: "t1cN2ZVWzWcVRrnfeQzmkpLhzQ4dYRv8yRY"
  };

  var URI_EXAMPLES = {
    good: "zcash:zu175e9thzutjjcqe9u3ca0n98msdagd8hp5vpl2zex065dzmmkf8pftgklq4upnrm5v3et4t89pffvat49xp3xw6mp2yzf9te8tjr7hhsz03x9w30vapxzh3u5eewdmrtc07fsepvnarvvma9tvvuw3ke57unafx2tg9l728h3m5uhhle3?amount=0.5&memo=b3JkZXI6MQ",
    memo: "zcash:t1cN2ZVWzWcVRrnfeQzmkpLhzQ4dYRv8yRY?amount=1&memo=b3JkZXI6MQ",
    dupe: "zcash:zu175e9thzutjjcqe9u3ca0n98msdagd8hp5vpl2zex065dzmmkf8pftgklq4upnrm5v3et4t89pffvat49xp3xw6mp2yzf9te8tjr7hhsz03x9w30vapxzh3u5eewdmrtc07fsepvnarvvma9tvvuw3ke57unafx2tg9l728h3m5uhhle3?amount=1&amount=2"
  };

  document.addEventListener("click", function (e) {
    var btn = e.target.closest("[data-fill]");
    if (!btn) return;
    var key = btn.getAttribute("data-fill");
    if ($("addr") && EXAMPLES[key]) $("addr").value = EXAMPLES[key];
    if ($("uri") && URI_EXAMPLES[key]) $("uri").value = URI_EXAMPLES[key];
  });

  /* ----------------------------------------------------------- scanner */
  var scanBtn = $("do-scan");
  if (scanBtn) {
    var loadExample = function (kind) {
      return getJSON("/api/examples/" + kind).then(function (data) {
        $("code").value = data.content;
        $("fname").value = data.name;
        $("scan-out").innerHTML = '<div class="empty">Example loaded. Press <strong>Scan for leaks</strong>.</div>';
      }).catch(function (err) { error($("scan-out"), err.message); });
    };
    if ($("load-leaky")) $("load-leaky").addEventListener("click", function () { loadExample("leaky"); });
    if ($("load-fixed")) $("load-fixed").addEventListener("click", function () { loadExample("fixed"); });

    var runScan = function () {
      var content = $("code").value;
      var out = $("scan-out");
      var t0 = performance.now();
      if (!content.trim()) {
        out.innerHTML = '<div class="empty">Nothing to scan — paste some code or load an example.</div>';
        return;
      }
      loading(out, "scanning…");
      Promise.all([
        post("/api/scan", { files: [{ name: $("fname").value, content: content }] }),
        loadRuleInfo()
      ])
        .then(function (both) {
          var data = both[0];
          var ms = Math.round(performance.now() - t0);
          var time = $("scan-time");
          if (time) { time.hidden = false; time.textContent = ms + " ms"; }
          out.innerHTML = renderScan(data);
        })
        .catch(function (err) { error(out, err.message); });
    };
    scanBtn.addEventListener("click", runScan);

    /* keyboard shortcut: cmd/ctrl + enter */
    var codeBox = $("code");
    if (codeBox) {
      codeBox.addEventListener("keydown", function (e) {
        if ((e.metaKey || e.ctrlKey) && e.key === "Enter") { e.preventDefault(); runScan(); }
      });
    }
  }

  function renderScan(data) {
    var s = data.summary;
    var findings = data.findings || [];
    var head = '<div class="result-head">';
    if (!findings.length) {
      head += '<span class="stat ok"><b>0</b><span>findings</span></span>' +
        '<span class="tag ok" style="margin-left:auto">clean</span>';
    } else {
      head += '<span class="stat err"><b>' + s.errors + "</b><span>errors</span></span>" +
        '<span class="stat warn"><b>' + s.warnings + "</b><span>warnings</span></span>";
      if (s.notes) head += '<span class="stat"><b>' + s.notes + "</b><span>notes</span></span>";
      head += '<span class="tag" style="margin-left:auto">' + s.files_scanned + " file" +
        (s.files_scanned === 1 ? "" : "s") + "</span>";
    }
    head += "</div>";

    if (!findings.length) {
      return head + '<div class="empty ok"><strong>No findings.</strong><br>' +
        "Shielded recipients, no memo or key exposure, valid payment requests.</div>";
    }

    var body = findings.map(function (f) {
      var detail = f.detail ? "<p>" + esc(f.detail) + "</p>" : "";
      var info = RULE_INFO && RULE_INFO[f.rule];
      var fix = info && info.remediation
        ? '<div class="fix"><b>Fix:</b> ' + esc(info.remediation) + "</div>"
        : "";
      var ref = '<div class="fix"><a class="link" href="https://github.com/ace-coderr/ShieldLint/blob/main/' +
        esc(f.help || "") + '" target="_blank" rel="noopener">' + esc(f.rule) +
        " — full rule reference</a></div>";
      return '<article class="finding ' + esc(f.severity) + '">' +
        '<div class="finding-top">' +
          '<span class="id">' + esc(f.rule) + "</span>" +
          '<span class="sev ' + esc(f.severity) + '">' + esc(f.severity) + "</span>" +
          '<span class="loc">' + esc(f.path) + ":" + f.line + ":" + f.column + "</span>" +
        "</div>" +
        "<h4>" + esc(f.title) + "</h4>" +
        "<p>" + esc(f.message) + "</p>" + detail + fix + ref +
      "</article>";
    }).join("");

    return head + body;
  }

  /* ------------------------------------------------------------ address */
  var addrBtn = $("do-addr");
  if (addrBtn) {
    addrBtn.addEventListener("click", function () {
      var value = ($("addr").value || "").trim();
      var out = $("addr-out");
      if (!value) { out.innerHTML = '<div class="empty">Paste an address first.</div>'; return; }
      loading(out, "decoding…");
      post("/api/address", { value: value }).then(function (d) {
        out.innerHTML = renderAddress(d);
      }).catch(function (err) { error(out, err.message); });
    });
  }

  function renderAddress(d) {
    var rows = "";
    rows += row("Kind", '<span class="tag ' + (d.shielded ? "blue" : "red") + '">' + esc(d.kind) + "</span>");
    rows += row("Network", esc(d.network));
    if (d.hrp) rows += row("Prefix", "<code>" + esc(d.hrp) + "</code>");
    if (d.revision != null) rows += row("Revision", esc(d.revision));
    rows += row("Shielded", d.shielded
      ? '<span class="tag ok">yes — private</span>'
      : '<span class="tag red">no — public on-chain</span>');
    if (d.receivers && d.receivers.length) {
      var list = d.receivers.map(function (r) {
        return '<div class="row" style="gap:8px;margin:2px 0">' +
          '<span class="tag ' + (r.transparent ? "red" : "ok") + '">' + esc(r.name) + "</span>" +
          '<span class="tiny mono">' + esc(r.typecode) + " · " + r.bytes + " bytes" +
          (r.transparent ? " · visible on-chain" : "") + "</span></div>";
      }).join("");
      rows += row("Receivers", list);
    }
    if (d.metadata && d.metadata.length) {
      rows += row("Metadata", d.metadata.map(function (m) {
        return esc(m.kind) + " = " + esc(m.value);
      }).join("<br>"));
    }
    var html = "<dl class=\"kv\">" + rows + "</dl>";
    if (d.has_transparent_receiver) {
      html += '<div class="banner mt20" style="border-color:#f3e3c2;background:var(--amber-wash);color:var(--amber)">' +
        '<svg aria-hidden="true"><use href="#i-alert"/></svg><div><strong>Downgrade risk.</strong> ' +
        "This address carries a transparent receiver. A sender that cannot do shielded will " +
        "fall back to it, which makes the amount and both parties public.</div></div>";
    }
    if (d.notes && d.notes.length) {
      html += '<ul class="small mt14">' + d.notes.map(function (n) { return "<li>" + esc(n) + "</li>"; }).join("") + "</ul>";
    }
    if (d.errors && d.errors.length) {
      html += '<div class="banner mt20" style="border-color:#f6d7d3;background:var(--red-wash);color:var(--red)">' +
        '<svg aria-hidden="true"><use href="#i-x"/></svg><div>' +
        d.errors.map(function (e) { return esc(e); }).join("<br>") + "</div></div>";
    }
    return html;
  }

  function row(label, value) {
    return "<dt>" + esc(label) + "</dt><dd>" + value + "</dd>";
  }

  /* ---------------------------------------------------------------- uri */
  var uriBtn = $("do-uri");
  if (uriBtn) {
    uriBtn.addEventListener("click", function () {
      var value = ($("uri").value || "").trim();
      var out = $("uri-out");
      if (!value) { out.innerHTML = '<div class="empty">Paste a <code>zcash:</code> URI first.</div>'; return; }
      loading(out, "validating…");
      post("/api/uri", { value: value }).then(function (d) {
        out.innerHTML = renderUri(d);
      }).catch(function (err) { error(out, err.message); });
    });
  }

  function renderUri(d) {
    var html = '<div class="result-head">' +
      (d.ok ? '<span class="tag ok">valid request</span>'
            : '<span class="tag red">invalid request</span>') +
      '<span class="tag" style="margin-left:auto">' + d.payments.length +
      " payment" + (d.payments.length === 1 ? "" : "s") + "</span></div>";

    if (d.payments.length) {
      html += '<table class="t"><thead><tr><th>#</th><th>Recipient</th><th>Amount</th><th>Memo</th><th>Exposure</th></tr></thead><tbody>';
      html += d.payments.map(function (p) {
        return "<tr>" +
          "<td class='mono'>" + esc(p.index || "—") + "</td>" +
          "<td><span class='tag " + (p.transparent ? "red" : "ok") + "'>" + esc(p.kind || "?") + "</span></td>" +
          "<td class='mono'>" + esc(p.amount || "—") + "</td>" +
          "<td class='mono'>" + (p.memo_bytes ? p.memo_bytes + " B" : "—") + "</td>" +
          "<td>" + (p.transparent ? "<span class='sev error'>public</span>" : "<span class='sev note'>shielded</span>") + "</td>" +
        "</tr>";
      }).join("");
      html += "</tbody></table>";
    }

    if (d.errors && d.errors.length) {
      html += '<div class="banner mt20" style="border-color:#f6d7d3;background:var(--red-wash);color:var(--red)">' +
        '<svg aria-hidden="true"><use href="#i-x"/></svg><div><strong>Rejected.</strong><br>' +
        d.errors.map(function (e) { return esc(e); }).join("<br>") + "</div></div>";
    }
    if (d.warnings && d.warnings.length) {
      html += '<div class="banner mt20" style="border-color:#f3e3c2;background:var(--amber-wash);color:var(--amber)">' +
        '<svg aria-hidden="true"><use href="#i-alert"/></svg><div>' +
        d.warnings.map(function (w) { return esc(w); }).join("<br>") + "</div></div>";
    }
    if (d.ok && !(d.errors || []).length) {
      html += '<p class="small mt14">Parsed cleanly. Remember that a syntactically valid request ' +
        "can still be a public payment if the recipient is transparent.</p>";
    }
    return html;
  }

  /* -------------------------------------------------------------- rules */
  var rulesOut = $("rules-out");
  if (rulesOut) {
    var ALL = [];
    var state = { filter: "all", query: "" };

    var count = function (sev) {
      return ALL.filter(function (r) { return sev === "all" || r.severity === sev; }).length;
    };

    var renderRules = function () {
      var q = state.query.toLowerCase();
      var list = ALL.filter(function (r) {
        if (state.filter !== "all" && r.severity !== state.filter) return false;
        if (!q) return true;
        return (r.id + " " + r.title + " " + r.summary + " " + r.rationale).toLowerCase().indexOf(q) >= 0;
      });
      if (!list.length) {
        rulesOut.innerHTML = '<div class="empty">No rule matches “' + esc(state.query) + "”.</div>";
        return;
      }
      rulesOut.innerHTML = list.map(function (r) {
        return '<details class="rule">' +
          "<summary>" +
            '<span class="rid">' + esc(r.id) + "</span>" +
            '<span class="sev ' + esc(r.severity) + '">' + esc(r.severity) + "</span>" +
            '<span class="rname">' + esc(r.title) + "</span>" +
            '<svg class="chev" width="16" height="16" aria-hidden="true"><use href="#i-chev"/></svg>' +
          "</summary>" +
          '<div class="body">' +
            "<p>" + esc(r.summary) + "</p>" +
            '<span class="lbl">Why it matters</span><p>' + esc(r.rationale) + "</p>" +
            '<span class="lbl">What to do instead</span><p>' + esc(r.remediation) + "</p>" +
            ((r.references || []).length
              ? '<span class="lbl">References</span><p class="mono tiny">' +
                r.references.map(function (ref) {
                  return '<a class="link" href="' + esc(ref.url) + '" target="_blank" rel="noopener">' + esc(ref.label) + "</a>";
                }).join(" · ") + "</p>"
              : "") +
          "</div>" +
        "</details>";
      }).join("");
    };

    getJSON("/api/rules").then(function (data) {
      ALL = data.rules || [];
      ["all", "error", "warning", "note"].forEach(function (k) {
        var el = $("n-" + k);
        if (el) el.textContent = count(k);
      });
      renderRules();
    }).catch(function (err) { error(rulesOut, "Could not load rules — " + err.message); });

    document.querySelectorAll("[data-filter]").forEach(function (chip) {
      chip.addEventListener("click", function () {
        document.querySelectorAll("[data-filter]").forEach(function (c) {
          c.setAttribute("aria-pressed", c === chip ? "true" : "false");
        });
        state.filter = chip.getAttribute("data-filter");
        renderRules();
      });
    });

    var search = $("rule-search");
    if (search) {
      search.addEventListener("input", function () {
        state.query = search.value.trim();
        renderRules();
      });
    }
  }
})();
