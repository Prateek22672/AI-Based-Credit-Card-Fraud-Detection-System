"""FraudLens REST API.

Run:  uvicorn fraudlens.api.main:app --port 8000
Docs: http://localhost:8000/docs (interactive Swagger UI)
"""
from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Literal

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .. import config, policy
from ..features import CATEGORIES
from .service import CATEGORY_OPTIONS, FraudService

API_KEY = os.getenv("FRAUDLENS_API_KEY")          # optional: protects state-changing endpoints
ORIGINS = os.getenv("FRAUDLENS_CORS_ORIGINS", "*").split(",")
FRONTEND = config.ROOT / "frontend" / "dist"
RESULT_FILES = {"benchmark_sparkov", "benchmark_ulb", "imbalance_sparkov", "protocol", "ablation", "unseen",
                "analysis", "explain", "dataset_sparkov", "scenarios", "policy", "latency"}

service: FraudService | None = None


def svc() -> FraudService:
    global service
    if service is None:
        service = FraudService()
    return service


@asynccontextmanager
async def lifespan(_app: FastAPI):
    svc()  # load models and the feature-store snapshot once, at startup
    yield


app = FastAPI(
    title="FraudLens API",
    version="1.0.0",
    description="Explainable hybrid credit-card fraud detection: XGBoost + Random Forest + Isolation Forest, "
                "calibrated risk score, SHAP reason codes and an auditable decision log.",
    lifespan=lifespan,
)
app.add_middleware(CORSMiddleware, allow_origins=ORIGINS, allow_methods=["*"], allow_headers=["*"])


def require_key(x_api_key: str | None = Header(default=None)) -> None:
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="missing or invalid X-API-Key")


class ScoreRequest(BaseModel):
    card_token: str = Field(..., description="Card token from /api/cards (card numbers never leave the server)")
    amount: float = Field(..., gt=0, le=100_000, description="Amount in USD")
    category: Literal[tuple(CATEGORIES)] = Field(..., description="Merchant category")
    timestamp: datetime | None = Field(None, description="Transaction time; default = 1 h after the card's last transaction")
    merchant: str | None = Field(None, max_length=120)
    known_merchant: bool = Field(False, description="Use a merchant this card has used before")
    distance_km: float | None = Field(None, ge=0, le=20_000, description="Distance of the merchant from the cardholder's home")
    merch_lat: float | None = Field(None, ge=-90, le=90)
    merch_long: float | None = Field(None, ge=-180, le=180)
    commit: bool = Field(False, description="Add to the card's history (False = what-if scoring)")


class ReviewRequest(BaseModel):
    label: Literal["fraud", "genuine"]
    note: str | None = Field(None, max_length=500)


class ScenarioRequest(BaseModel):
    card_token: str | None = None


def not_found(e: KeyError):
    return HTTPException(status_code=404, detail=str(e).strip("'"))


@app.get("/api/health", tags=["system"])
def health():
    return {"status": "ok", **svc().status()}


@app.get("/api/model", tags=["system"])
def model_card():
    s = svc()
    return s.model_card | {"meta_weights": s.engine.meta_weights(), "categories": CATEGORY_OPTIONS,
                           "policy_rules": policy.RULE_INFO, "novelty_percentile": policy.NOVELTY_PERCENTILE}


@app.get("/api/results/{name}", tags=["research"])
def results(name: str):
    if name not in RESULT_FILES:
        raise HTTPException(404, "unknown result set")
    path = config.RESULTS / f"{name}.json"
    if not path.exists():
        raise HTTPException(404, "result not generated yet")
    return json.loads(path.read_text())


@app.get("/api/cards", tags=["cards"])
def cards(limit: int = Query(60, ge=1, le=1000)):
    return svc().cards(limit)


@app.get("/api/cards/{token}", tags=["cards"])
def card(token: str):
    try:
        return svc().card_detail(token)
    except KeyError as e:
        raise not_found(e)


@app.post("/api/score", tags=["scoring"], dependencies=[Depends(require_key)])
def score(req: ScoreRequest):
    """Score one transaction in real time and explain the decision."""
    try:
        return svc().score(req)
    except KeyError as e:
        raise not_found(e)


@app.post("/api/stream/next", tags=["live demo"], dependencies=[Depends(require_key)])
def stream_next(n: int = Query(25, ge=1, le=500)):
    """Replay the next n unseen test-period transactions through the engine."""
    return svc().stream_next(n)


@app.get("/api/stream/status", tags=["live demo"])
def stream_status():
    return svc().status()


@app.post("/api/reset", tags=["live demo"], dependencies=[Depends(require_key)])
def reset():
    svc().reset()
    return svc().status()


@app.get("/api/stats", tags=["live demo"])
def stats():
    return svc().stats()


@app.get("/api/transactions", tags=["case management"])
def transactions(limit: int = Query(100, ge=1, le=1000), level: str | None = None,
                 source: str | None = None, status: str | None = None):
    return svc().decisions(limit, level, source, status)


@app.get("/api/transactions/{did}", tags=["case management"])
def transaction(did: int):
    try:
        return svc().decision(did)
    except KeyError as e:
        raise not_found(e)


@app.post("/api/transactions/{did}/review", tags=["case management"], dependencies=[Depends(require_key)])
def review(did: int, req: ReviewRequest):
    """Analyst feedback: confirm fraud or dismiss as genuine (stored as a label for retraining)."""
    try:
        return svc().review(did, req.label, req.note)
    except KeyError as e:
        raise not_found(e)


@app.get("/api/scenarios", tags=["scenarios"])
def scenarios():
    return svc().scenarios()


@app.post("/api/scenarios/{sid}/run", tags=["scenarios"], dependencies=[Depends(require_key)])
def run_scenario(sid: str, req: ScenarioRequest | None = None):
    try:
        return svc().run_scenario(sid, req.card_token if req else None)
    except KeyError as e:
        raise not_found(e)


# ---------------------------------------------------------------- static files
app.mount("/figures", StaticFiles(directory=config.FIGURES), name="figures")

if FRONTEND.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        target = FRONTEND / path
        if path and target.is_file():
            return FileResponse(target)
        return FileResponse(FRONTEND / "index.html")
