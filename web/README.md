# ShieldLint web UI

A single-page front door for the CLI engine: scan source, decode addresses,
validate ZIP 321 payment requests, browse the rule set.

One deployment, one origin. The FastAPI app in `web/api.py` serves both the UI
(`web/static/index.html`) and the JSON API, so the browser never makes a
cross-origin request.

## Run locally

```bash
python -m pip install -r requirements.txt
uvicorn web.api:app --reload --port 8000     # from the repository root
# open http://localhost:8000
```

The UI lives in `web/static/index.html`; the demo sources come from
`examples/`. Both are embedded into Python modules (`web/ui.py`,
`web/examples_data.py`) because a serverless bundle only ships what the code
imports, not what it reads at runtime. After editing either source, regenerate:

```bash
python scripts/make_og.py     # if you changed the social card
python scripts/embed_web.py   # always, after editing html/examples/og
```

## Deploy to Vercel

The repository root holds `vercel.json`, which builds `web/api.py` with the
Python runtime and routes every path to it.

```bash
npm i -g vercel     # once
vercel login
vercel --prod       # from the repository root
```

Or through the dashboard: **Add New → Project → Import `ace-coderr/ShieldLint`**,
set **Application Preset** to **Other** (important — the FastAPI preset assumes
`main.py`/`app.py` at the root), leave *Root Directory* at the repository root,
and deploy. `vercel.json` does the rest; no environment variables are required.

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `GET`  | `/` | the UI |
| `GET`  | `/health` | liveness + rule count |
| `POST` | `/api/scan` | `{files:[{name,content}]}` → findings |
| `POST` | `/api/address` | `{value}` → decoded address |
| `POST` | `/api/uri` | `{value}` → parsed payment request |
| `GET`  | `/api/rules` | the rule catalogue |
| `GET`  | `/api/examples/{leaky,fixed,rust}` | bundled demo sources |
| `GET`  | `/api/og` | 1200x630 social preview |
| `GET`  | `/robots.txt`, `/favicon.ico` | small niceties for crawlers |

## Limits

Requests are capped at 20 files / 200 KB per scan, and nothing is stored or
logged — each request is analysed in memory and discarded.
