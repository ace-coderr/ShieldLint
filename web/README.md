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

## Deploy to Vercel

The repository root holds `vercel.json`, which builds `web/api.py` with the
Python runtime and routes every path to it.

```bash
npm i -g vercel     # once
vercel login
vercel --prod       # from the repository root
```

Or through the dashboard: **Add New → Project → Import `ace-coderr/ShieldLint`**,
leave *Root Directory* as the repository root (the `vercel.json` handles the
rest), and deploy. No environment variables are required.

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

## Limits

Requests are capped at 20 files / 200 KB per scan, and nothing is stored or
logged — each request is analysed in memory and discarded.
