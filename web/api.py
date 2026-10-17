"""ShieldLint web service.

A stateless HTTP skin over the same engine the CLI uses. Nothing is stored,
nothing is logged: every request is analysed in memory and discarded.

Deployed as a Vercel Python function; `vercel.json` routes every path here so
the site and the API share one origin.

Run locally from the repository root:

    uvicorn web.api:app --reload --port 8000
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi import FastAPI, HTTPException  # noqa: E402
from fastapi.responses import HTMLResponse, JSONResponse, Response  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

from shieldlint import address as addr  # noqa: E402
from shieldlint.engine import Config, run  # noqa: E402
from shieldlint.rules import RULES  # noqa: E402
from shieldlint.uri import parse_payment_uri  # noqa: E402

from web.assets import FAVICON_SVG, favicon_png, og_png  # noqa: E402
from web.examples_data import EXAMPLES  # noqa: E402
from web.pages import PAGES  # noqa: E402

MAX_SOURCE_BYTES = 200_000
MAX_FILES = 20
EXTENSIONS = {
    ".py", ".js", ".mjs", ".ts", ".tsx", ".jsx", ".rs", ".go", ".java", ".kt",
    ".cs", ".c", ".h", ".cpp", ".rb", ".php", ".swift", ".sh", ".bash",
    ".yaml", ".yml", ".toml", ".json",
}

app = FastAPI(
    title="ShieldLint",
    version="0.1.0",
    description="Offline Zcash privacy linting: transparent recipients, memo and key "
    "exposure, ZIP 316 decoding and ZIP 321 validation.",
    docs_url="/api/docs",
    redoc_url=None,
    openapi_url="/api/openapi.json",
)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class ScanFile(BaseModel):
    name: str = Field(default="snippet.py")
    content: str = ""


class ScanRequest(BaseModel):
    files: list[ScanFile] = Field(default_factory=list)
    fail_on: str = "never"


class AddressRequest(BaseModel):
    value: str


class UriRequest(BaseModel):
    value: str


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------

CACHE_HTML = {"Cache-Control": "public, max-age=0, must-revalidate"}


def _page(path: str, status_code: int = 200) -> HTMLResponse:
    entry = PAGES.get(path) or PAGES["/404"]
    return HTMLResponse(entry["html"], status_code=status_code, headers=CACHE_HTML)


@app.get("/", response_class=HTMLResponse)
def home() -> HTMLResponse:
    return _page("/")


@app.get("/scan", response_class=HTMLResponse)
def page_scan() -> HTMLResponse:
    return _page("/scan")


@app.get("/address", response_class=HTMLResponse)
def page_address() -> HTMLResponse:
    return _page("/address")


@app.get("/uri", response_class=HTMLResponse)
def page_uri() -> HTMLResponse:
    return _page("/uri")


@app.get("/rules", response_class=HTMLResponse)
def page_rules() -> HTMLResponse:
    return _page("/rules")


@app.get("/docs", response_class=HTMLResponse)
def page_docs() -> HTMLResponse:
    return _page("/docs")


@app.get("/install", response_class=HTMLResponse)
def page_install() -> HTMLResponse:
    return _page("/install")


@app.get("/404", response_class=HTMLResponse)
def page_404() -> HTMLResponse:
    return _page("/404", status_code=404)


# ---------------------------------------------------------------------------
# Static assets
# ---------------------------------------------------------------------------


@app.get("/favicon.svg")
def favicon_svg() -> Response:
    return Response(FAVICON_SVG, media_type="image/svg+xml",
                    headers={"Cache-Control": "public, max-age=604800"})


@app.get("/favicon-32.png")
def favicon_32() -> Response:
    return Response(favicon_png(), media_type="image/png",
                    headers={"Cache-Control": "public, max-age=604800"})


@app.get("/favicon.ico")
def favicon_ico() -> Response:
    return Response(favicon_png(), media_type="image/png",
                    headers={"Cache-Control": "public, max-age=604800"})


@app.get("/api/og")
def og_image() -> Response:
    """1200x630 social preview (Open Graph / Twitter card)."""
    return Response(og_png(), media_type="image/png",
                    headers={"Cache-Control": "public, max-age=86400, immutable"})


@app.get("/robots.txt")
def robots() -> Response:
    body = "User-agent: *\nAllow: /\nSitemap: https://shieldlint.vercel.app/sitemap.xml\n"
    return Response(body, media_type="text/plain")


@app.get("/sitemap.xml")
def sitemap() -> Response:
    urls = "".join(
        f"<url><loc>https://shieldlint.vercel.app{path}</loc></url>"
        for path in PAGES
        if path != "/404"
    )
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        f"{urls}</urlset>"
    )
    return Response(xml, media_type="application/xml")


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------


@app.get("/health")
def health() -> dict[str, Any]:
    return {"ok": True, "version": "0.1.0", "rules": len(RULES), "pages": len(PAGES)}


@app.post("/api/scan")
def scan(request: ScanRequest) -> dict[str, Any]:
    files = [f for f in request.files if f.content.strip()]
    if not files:
        raise HTTPException(400, "nothing to scan: provide at least one non-empty file")
    if len(files) > MAX_FILES:
        raise HTTPException(400, f"too many files (limit {MAX_FILES})")
    total = sum(len(f.content.encode("utf-8")) for f in files)
    if total > MAX_SOURCE_BYTES:
        raise HTTPException(400, f"payload too large (limit {MAX_SOURCE_BYTES // 1000} KB)")

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        for i, item in enumerate(files):
            name = Path(item.name or f"snippet{i}.py").name
            if Path(name).suffix.lower() not in EXTENSIONS:
                name += ".py"
            (root / name).write_text(item.content, encoding="utf-8")
        config = Config(fail_on=request.fail_on)
        report = run([root], config, root=root)

    return {
        "summary": {
            "files_scanned": report.files_scanned,
            "files_with_findings": report.files_with_findings,
            "errors": report.errors,
            "warnings": report.warnings,
            "notes": report.notes,
            "by_rule": report.counts_by_rule(),
            "exceeds_threshold": report.exceeds_threshold(),
        },
        "findings": [f.to_dict() for f in report.findings],
    }


@app.post("/api/address")
def decode_address(request: AddressRequest) -> dict[str, Any]:
    value = request.value.strip()
    if not value:
        raise HTTPException(400, "empty address")
    if len(value) > 2000:
        raise HTTPException(400, "address too long")
    info = addr.classify(value)
    return {
        "input": value,
        "kind": info.kind,
        "network": info.network,
        "hrp": info.hrp,
        "revision": info.revision,
        "receivers": [
            {
                "name": r.name,
                "typecode": f"0x{r.typecode:02x}",
                "bytes": len(r.data),
                "transparent": r.transparent,
            }
            for r in info.receivers
        ],
        "metadata": [{"kind": m.kind, "value": m.value} for m in info.metadata],
        "shielded": bool(info.shielded_receivers) or info.kind == "sapling",
        "has_transparent_receiver": info.has_transparent_receiver,
        "notes": info.notes,
        "errors": info.errors,
        "ok": info.ok and info.is_address,
    }


@app.post("/api/uri")
def validate_uri(request: UriRequest) -> dict[str, Any]:
    value = request.value.strip()
    if not value:
        raise HTTPException(400, "empty URI")
    if len(value) > 4000:
        raise HTTPException(400, "URI too long")
    parsed = parse_payment_uri(value)
    return {
        "input": value,
        "ok": parsed.ok,
        "errors": parsed.errors,
        "warnings": parsed.warnings,
        "payments": [
            {
                "index": p.index,
                "address": (p.address or "")[:48],
                "kind": p.info.kind if p.info else None,
                "network": p.info.network if p.info else None,
                "amount": p.amount_text or None,
                "memo_bytes": len(p.memo) if p.memo else 0,
                "label": p.label,
                "message": p.message,
                "transparent": p.is_transparent,
            }
            for p in parsed.payments
        ],
    }


@app.get("/api/rules")
def list_rules() -> dict[str, Any]:
    return {
        "rules": [
            {
                "id": r.id,
                "slug": r.slug,
                "severity": r.severity,
                "title": r.title,
                "summary": r.summary,
                "rationale": r.rationale,
                "remediation": r.remediation,
                "references": [{"label": label, "url": url} for label, url in r.refs],
            }
            for r in RULES
        ]
    }


@app.get("/api/examples/{name}")
def example(name: str) -> dict[str, str]:
    """Serve the bundled demo sources so the UI can preload them."""
    entry = EXAMPLES.get(name)
    if entry is None:
        raise HTTPException(404, "unknown example")
    return dict(entry)


# ---------------------------------------------------------------------------
# Fallback
# ---------------------------------------------------------------------------


@app.exception_handler(404)
def not_found(_request: Any, _exc: Any) -> Any:
    if _request.url.path.startswith("/api/"):
        return JSONResponse({"detail": "not found"}, status_code=404)
    return _page("/404", status_code=404)
