# ShieldLint web app

The browser front door for the CLI engine. Same rules, same decoders, same
engine — one deployment, one origin.

```
web/
  api.py              FastAPI app: pages, assets, JSON API
  site/               page sources (one HTML fragment per route + _layout.html)
  static/app.css      design system
  static/app.js       behaviour (scan, decode, validate, rules search)
  pages.py            generated — routes rendered into HTML strings
  assets.py           generated — favicon and social image bytes
  ui.py               generated
  examples_data.py    generated — demo sources
```

## Routes

| Path | Page |
|------|------|
| `/` | landing page: hero, problem, how it works, rules, evidence, adopt |
| `/scan` | paste source, get findings |
| `/address` | decode an address or viewing key |
| `/uri` | validate a ZIP 321 payment request |
| `/rules` | searchable rule index |
| `/docs` | quickstart, CLI, config, suppression, CI, limitations |
| `/install` | source, Docker, CI, pre-commit, rollout order |

| Method | API |
|--------|-----|
| `POST` | `/api/scan` `{files:[{name,content}]}` → findings |
| `POST` | `/api/address` `{value}` → decoded address |
| `POST` | `/api/uri` `{value}` → parsed payment request |
| `GET` | `/api/rules` · `/api/examples/{leaky,fixed,rust}` · `/api/og` · `/health` |

## Build

Pages, CSS and JS are **inlined into each page** — no external stylesheet, no
CDN, no extra request, and nothing for a serverless bundle to fetch at runtime.

```bash
python scripts/build_site.py     # web/site/* → web/pages.py, web/assets.py
python scripts/make_og.py        # web/og.png (social card), then rebuild
```

Edit `web/site/*.html` or `web/static/app.css`, run `build_site.py`, commit both
the source and the generated modules. Self-linting stays clean because generated
files carry a `# shieldlint: disable-file` directive.

## Run locally

```bash
python -m pip install -r requirements.txt
uvicorn web.api:app --reload --port 8000
```

## Deploy

Vercel, preset **Other**, root directory `./`. `vercel.json` builds `web/api.py`
with `@vercel/python` and routes everything to it. No environment variables.

```bash
vercel --prod
```
