# Deploying FraudLens

Two parts: the **API** (Python, holds the models and the per-card state; needs a persistent host)
and the **dashboard** (static React build; any static host, e.g. Vercel).

## 1. API on a VPS (Docker, recommended)

```bash
git clone https://github.com/Prateek22672/AI-Based-Credit-Card-Fraud-Detection-System.git
cd AI-Based-Credit-Card-Fraud-Detection-System
docker build -t fraudlens .
docker run -d --name fraudlens --restart unless-stopped -p 8000:8000 \
  -e FRAUDLENS_CORS_ORIGINS="https://<your-vercel-domain>,https://<your-custom-domain>" \
  -e FRAUDLENS_TOKEN_SECRET="<long random string>" \
  fraudlens
```

* Health check: `curl http://<vps-ip>:8000/api/health`
* The container also serves the built dashboard at `http://<vps-ip>:8000/`, so a single VPS works without Vercel.
* Put Nginx/Caddy or a Cloudflare Tunnel in front for HTTPS (browsers block a `https://` dashboard calling an
  `http://` API). Example Caddyfile: `api.your-domain.com { reverse_proxy localhost:8000 }`.
* Optional: `-e FRAUDLENS_API_KEY=<key>` protects all POST endpoints; then build the dashboard with the same
  `VITE_API_KEY`.
* Optional: `-e FRAUDLENS_DB_URL=postgresql+psycopg://user:pw@host/db` for a PostgreSQL decision log
  (add `psycopg[binary]` to `requirements-api.txt`).

Without Docker: `pip install -r requirements-api.txt` and
`uvicorn fraudlens.api.main:app --host 0.0.0.0 --port 8000` (Python 3.11).

Free hosts with a sleeping tier (Render, Railway, Fly.io) also work: the image is ~1.5 GB and needs ~1 GB RAM.
Serverless platforms are not suitable: the API keeps card state in memory and loads ~50 MB of models at start.

## 2. Dashboard on Vercel

1. Import the GitHub repository in Vercel.
2. **Root Directory:** `frontend` (Framework preset: Vite; build `npm run build`; output `dist` — all read from
   `frontend/vercel.json`).
3. Environment variables: `VITE_API_URL = https://api.your-domain.com` (the API host, no trailing slash) and,
   if the API uses a key, `VITE_API_KEY`.
4. Deploy. The research results, figures and the PDF/DOCX reports are committed under `frontend/public/`, so
   the Results and Project Report pages work even before the API is up; the live pages show
   "Backend offline" until `VITE_API_URL` points at a running API whose `FRAUDLENS_CORS_ORIGINS` includes the
   Vercel domain.

## 3. Updating

* Research results changed: `python -m fraudlens.pipeline ...`, `python -m fraudlens.plots`,
  `python -m reporting.build`, then `cd frontend && npm run sync-data` and commit `frontend/public/`.
* Model changed: commit `artifacts/` (engine, feature-store snapshot, stream, model card) and redeploy the API.
