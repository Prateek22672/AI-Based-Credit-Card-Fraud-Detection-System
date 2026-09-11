# FraudLens dashboard (frontend)

React 18 + Vite + Tailwind CSS v4 + Recharts single-page app for the FraudLens API
(`fraudlens/api/main.py`). Pages: Overview, Live Monitor, Transaction Tester, Scam Scenarios,
Case Queue, Model & Research Results, Project Report, Architecture.

## Development

```bash
cd frontend
npm install
npm run dev            # http://localhost:5173
```

The dev server proxies `/api`, `/figures` and `/docs` to the FastAPI backend
(`http://localhost:8000` by default). To point it elsewhere:

```powershell
$env:VITE_PROXY_TARGET = "http://localhost:8010"; npm run dev      # PowerShell
VITE_PROXY_TARGET=http://localhost:8010 npm run dev                 # bash
```

Start the API from the project root first: `uvicorn fraudlens.api.main:app --port 8000`
(it needs the trained artifacts: `python -m fraudlens.pipeline all`).

## Build

```bash
npm run build          # runs sync-data, then writes frontend/dist
npm run preview        # serve the build locally for a quick check
```

Vite `base` is `/`. FastAPI serves `frontend/dist` automatically when it exists:
`/assets/*` as static files and `index.html` for every other route (SPA fallback), so after
`npm run build` the whole app is available at `http://localhost:8000/`.

## Environment variables (build time, `VITE_*`)

| Variable | Default | Meaning |
|---|---|---|
| `VITE_API_URL` | `""` (same origin) | Base URL of the FraudLens API, e.g. `https://api.example.com`. Leave empty when FastAPI serves the build. |
| `VITE_API_KEY` | unset | Sent as `X-API-Key` on every POST when the API runs with `FRAUDLENS_API_KEY`. Note: anything baked into a public build is visible to users; use it only for demos/internal deployments. |
| `VITE_PROXY_TARGET` | `http://localhost:8000` | Dev-server proxy target (dev only). |

Put them in a `.env` / `.env.production` file in `frontend/` or set them in the shell before
`npm run build`.

## `npm run sync-data` (static fallback for research pages)

`scripts/sync-data.mjs` copies `../reports/results/*.json` (never `*.npz`) into
`public/data/results/`, `../reports/figures/*.png` into `public/data/figures/` and the
`../docs/*.pdf|*.docx` reports into `public/docs/` (so the Report page's download links work). It runs
automatically before every `build`. The data layer tries the API first
(`/api/results/<name>`, `/figures/<name>.png`) and falls back to these static copies, so the
**Results**, **Report** and **About** pages work on plain static hosting without the API. Live
pages (Monitor, Tester, Scenarios, Cases) show a "Backend offline — start the API" state when
the API is unreachable.

The Project Report page reads `public/data/project.json`; the team edits that file to update
team members, milestones, work distribution, deliverables and the changelog. No code changes
are needed.

## Deployment options

### (a) FastAPI serves the build (simplest: one server / VPS)

```bash
cd frontend && npm run build
cd .. && uvicorn fraudlens.api.main:app --host 0.0.0.0 --port 8000
```

Put nginx/Caddy in front for TLS. No `VITE_API_URL` needed (same origin), no CORS
configuration needed.

### (b) Static hosting of `dist/` + API on another host

Build with the API location baked in:

```bash
VITE_API_URL=https://api.your-domain.com npm run build
```

Upload the contents of `dist/` to shared hosting (cPanel), Netlify, Vercel, GitHub Pages, S3,
etc. Then:

* On the API host set `FRAUDLENS_CORS_ORIGINS` to the site origin, e.g.
  `FRAUDLENS_CORS_ORIGINS=https://fraudlens.your-domain.com` (comma-separate several origins).
  Without it the browser blocks cross-origin requests.
* SPA fallback rewrites: deep links such as `/monitor` must serve `index.html`.
  * Apache / cPanel: `public/.htaccess` (copied into `dist/`) already contains the rewrite rules.
  * Netlify: `public/_redirects` (copied into `dist/`) contains `/* /index.html 200`.
  * Vercel: `vercel.json` (already in this folder) contains the rewrite.
  * GitHub Pages: copy `dist/index.html` to `dist/404.html` before publishing.
* Figures and research JSON are served from the static copy (`/data/...`) when the API
  is unreachable, so the Results page keeps working even if the API is down.

### Deploy on Vercel (static dashboard + separately hosted API)

`frontend/vercel.json` is already configured (framework `vite`, build `npm run build`,
output `dist`, SPA rewrite of every non-file route to `/index.html`).

1. Import the repository in Vercel and set **Root Directory** to `frontend`.
2. Environment variables (Production and Preview):
   * `VITE_API_URL=https://<api-host>` — the public URL of the FastAPI service
     (no trailing slash).
   * `VITE_API_KEY=<key>` only if the API runs with `FRAUDLENS_API_KEY`.
3. Deploy. `npm run build` runs `sync-data` first; when `../reports` is not part of the
   checkout it skips the copy and uses the committed files in `public/data/results` and
   `public/data/figures`, so the Results page still works. Re-run `npm run sync-data` locally
   and commit `public/data` whenever the research results or figures change.
4. On the API host set `FRAUDLENS_CORS_ORIGINS` to the Vercel domain(s), e.g.
   `FRAUDLENS_CORS_ORIGINS=https://fraudlens.vercel.app,https://fraudlens.your-domain.com`.
   Preview deployments have their own `*.vercel.app` origins; add them too if you need the
   live pages there.

`public/data/**` must stay committed (it is not ignored) for this to work.

## Screenshots

`screenshots/` contains desktop (1440 px) captures of every page and mobile (420 px)
captures of the overview and tester, for use in the project report.
