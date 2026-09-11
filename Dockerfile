# FraudLens: one container serving the API and the built React dashboard.
#   docker build -t fraudlens .
#   docker run -p 8000:8000 fraudlens        ->  http://localhost:8000
# Needs the trained artifacts in artifacts/ (committed to the repo, or produced by
# `python -m fraudlens.pipeline all`).

FROM node:22-alpine AS web
WORKDIR /app
COPY frontend/package*.json frontend/
RUN cd frontend && npm ci
COPY frontend frontend
COPY reports reports
RUN cd frontend && npm run build

FROM python:3.11-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 && rm -rf /var/lib/apt/lists/*
COPY requirements-api.txt .
RUN pip install --no-cache-dir -r requirements-api.txt
COPY fraudlens fraudlens
COPY artifacts artifacts
COPY reports reports
COPY --from=web /app/frontend/dist frontend/dist
EXPOSE 8000
CMD ["uvicorn", "fraudlens.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
