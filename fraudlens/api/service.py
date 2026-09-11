"""Scoring service used by the API: model, live feature store and decision log."""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import pickle
import threading
import time
from collections import Counter
from datetime import datetime, timezone

import joblib
import numpy as np
import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import config, policy
from ..explain import CATEGORY_LABELS, explain_row, shap_values
from ..features import ALL_FEATURES, CATEGORIES, FeatureStore, Txn
from . import db
from .scenarios import SCENARIOS, normal_steps, offset_point

TOKEN_SECRET = os.getenv("FRAUDLENS_TOKEN_SECRET", "fraudlens-demo-secret").encode()


def card_token(cc_num: str) -> str:
    """Keyed hash of the card number: the real number never leaves the server."""
    return hmac.new(TOKEN_SECRET, cc_num.encode(), hashlib.sha256).hexdigest()[:16]


def iso(unix: int) -> str:
    return datetime.fromtimestamp(int(unix), tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


class FraudService:
    def __init__(self):
        self.lock = threading.RLock()
        self.engine = joblib.load(config.ARTIFACTS / "engine.joblib")
        for m in (self.engine.xgb, self.engine.rf, self.engine.iso):
            m.set_params(n_jobs=1)
        self.features = self.engine.feature_names
        # The feature store computes every feature; the deployed model uses a subset
        # (protected attributes such as age and gender are left out).
        self._cols = [ALL_FEATURES.index(f) for f in self.features]
        self._snapshot = (config.ARTIFACTS / "feature_store.pkl").read_bytes()
        self.stream = pd.read_parquet(config.ARTIFACTS / "stream.parquet")
        self.model_card = json.loads((config.ARTIFACTS / "model_card.json").read_text())
        self.reset()

    # ------------------------------------------------------------ lifecycle
    def reset(self) -> None:
        with self.lock:
            self.store: FeatureStore = pickle.loads(self._snapshot)
            self.pointer = 0
            self.tokens = {card_token(cc): cc for cc in self.store.profiles}
            db.init_db(reset=True)

    def status(self) -> dict:
        return {
            "model_version": self.engine.version, "cards": len(self.store.profiles),
            "stream_position": self.pointer, "stream_total": len(self.stream),
            "simulated_clock": iso(self.stream["unix"].iat[max(self.pointer - 1, 0)]),
            "thresholds": {"alert": self.engine.t_alert, "block": self.engine.t_block},
        }

    # --------------------------------------------------------------- scoring
    def _score_batch(self, txns: list[Txn], X: np.ndarray, summaries: list[dict],
                     explain_all: bool = True) -> list[dict]:
        """Score a batch. Exact TreeSHAP over ~1,000 trees costs far more than the models
        themselves, so the live stream explains alerts immediately and approved
        transactions on demand (see ``decision``); single scores always explain."""
        t0 = time.perf_counter()
        comps = self.engine.component_scores(X)
        prob = self.engine.predict_proba(X, comps)
        risk = self.engine.risk_score(prob)
        ml_levels, hits_all = [], []
        for i in range(len(txns)):
            ml_levels.append(self.engine.decide(float(prob[i]))[0])
            # defence in depth: documented policy rules + novelty alarm can only raise the decision
            hits_all.append(policy.evaluate(dict(zip(self.features, map(float, X[i]))), float(comps["iforest"][i])))
        levels = [policy.combine(m, h) for m, h in zip(ml_levels, hits_all)]
        need = [i for i, (lvl, _) in enumerate(levels) if explain_all or lvl != "LOW"]
        contribs = {}
        if need:
            sv, base = shap_values(self.engine.xgb, X[need])   # one batched TreeSHAP call
            contribs = {i: (sv[k], base[k]) for k, i in enumerate(need)}
        per_txn_ms = (time.perf_counter() - t0) * 1e3 / len(txns)
        out = []
        for i, t in enumerate(txns):
            t1 = time.perf_counter()
            ml_level, hits = ml_levels[i], hits_all[i]
            level, decision = levels[i]
            exp = (explain_row(self.engine.xgb, self.features, X[i], t.category, summaries[i], contrib=contribs[i])
                   if i in contribs else {"reasons": [], "mitigating": [], "features": [], "groups": []})
            ml_risk = round(float(risk[i]), 1)
            shown_risk = ml_risk if level == ml_level else max(ml_risk, config.RISK_BAND_MEDIUM + 1)
            prof = self.store.profiles[t.cc_num]
            out.append({
                "card_token": card_token(t.cc_num), "card_last4": t.cc_num[-4:],
                "txn_time": iso(t.unix), "unix": t.unix, "amount": round(t.amt, 2), "category": t.category,
                "category_label": CATEGORY_LABELS.get(t.category, t.category), "merchant": t.merchant,
                "merch_lat": t.merch_lat, "merch_long": t.merch_long,
                "home": {"city": prof.city, "state": prof.state, "lat": prof.lat, "long": prof.long},
                "probability": float(prob[i]), "risk_score": shown_risk,
                "risk_level": level, "decision": decision,
                "ml_risk_score": ml_risk, "ml_risk_level": ml_level, "policy": hits,
                "components": {"xgboost": float(comps["xgb"][i]), "random_forest": float(comps["rf"][i]),
                               "anomaly_percentile": float(comps["iforest"][i])},
                "reasons": [h["reason"] for h in hits] + exp["reasons"], "mitigating": exp["mitigating"],
                "shap": exp["features"],
                "groups": exp["groups"], "card": summaries[i],
                "features": {k: round(float(v), 4) for k, v in zip(self.features, X[i]) if not k.startswith("cat_")},
                "explained": i in contribs,
                "latency_ms": round(per_txn_ms + (time.perf_counter() - t1) * 1e3, 2),
                "model_version": self.engine.version,
            })
        return out

    def explain_record(self, d: db.Decision) -> dict:
        """On-demand explanation of a logged decision, rebuilt from its stored feature vector."""
        x = np.array([d.features.get(f, 1.0 if f == f"cat_{d.category}" else 0.0) for f in self.features], dtype=float)
        return explain_row(self.engine.xgb, self.features, x, d.category)

    def _log(self, results: list[dict], source: str, labels: list[int | None] | None = None) -> None:
        with Session(db.engine) as s:
            rows = [db.Decision(
                source=source, card_token=r["card_token"], card_last4=r["card_last4"],
                txn_time=datetime.fromisoformat(r["txn_time"]), amount=r["amount"], category=r["category"],
                merchant=r["merchant"], probability=r["probability"], risk_score=r["risk_score"],
                risk_level=r["risk_level"], decision=r["decision"], p_xgb=r["components"]["xgboost"],
                p_rf=r["components"]["random_forest"], anomaly_pct=r["components"]["anomaly_percentile"],
                reasons=r["reasons"], mitigating=r["mitigating"], features=r["features"], policy=r["policy"],
                model_version=r["model_version"], latency_ms=r["latency_ms"],
                label=labels[i] if labels else None,
                # only live traffic opens review cases; what-if scores are logged for the audit trail only
                review_status="open" if r["risk_level"] != "LOW" and source == "stream" else "n/a",
            ) for i, r in enumerate(results)]
            s.add_all(rows)
            s.flush()                                   # assigns ids in one round trip
            for i, (r, row) in enumerate(zip(results, rows)):
                r["id"] = row.id
                if labels:
                    r["label"] = labels[i]
            s.commit()

    def _process(self, store: FeatureStore, txns: list[Txn], commit: bool = True):
        X, summaries = [], []
        for t in txns:
            summaries.append(store.card_summary(t.cc_num))
            X.append(store.features(t))
            if commit:
                store.update(t)
        return np.vstack(X)[:, self._cols], summaries

    def stream_next(self, n: int) -> list[dict]:
        with self.lock:
            rows = self.stream.iloc[self.pointer:self.pointer + n]
            if rows.empty:
                return []
            txns = [Txn(r.cc_num, int(r.unix), float(r.amt), r.category, r.merchant, float(r.merch_lat),
                        float(r.merch_long)) for r in rows.itertuples()]
            X, summaries = self._process(self.store, txns)
            self.pointer += len(rows)
            results = self._score_batch(txns, X, summaries, explain_all=False)
            self._log(results, "stream", rows["is_fraud"].astype(int).tolist())
            return results

    def resolve_card(self, token: str) -> str:
        if token not in self.tokens:
            raise KeyError("unknown card")
        return self.tokens[token]

    def build_txn(self, req, store: FeatureStore) -> Txn:
        cc = self.resolve_card(req.card_token)
        prof = self.store.profiles[cc]
        st = store.states.get(cc)
        if req.timestamp is not None:
            unix = int(req.timestamp.replace(tzinfo=timezone.utc).timestamp()) if req.timestamp.tzinfo is None \
                else int(req.timestamp.timestamp())
        else:
            unix = (st.last_ts if st else int(self.stream["unix"].iat[0])) + 3600
        if req.merch_lat is not None and req.merch_long is not None:
            lat, lon = req.merch_lat, req.merch_long
        else:
            lat, lon = offset_point(prof.lat, prof.long, req.distance_km if req.distance_km is not None else 5.0)
        merchant = req.merchant or ""
        if not merchant and req.known_merchant and st and st.merchants:
            merchant = sorted(st.merchants)[0]
        return Txn(cc, unix, float(req.amount), req.category, merchant or "Unknown merchant", lat, lon)

    def score(self, req) -> dict:
        with self.lock:
            t = self.build_txn(req, self.store)
            X, summaries = self._process(self.store, [t], commit=req.commit)
            res = self._score_batch([t], X, summaries)
            self._log(res, "manual")
            return res[0]

    # ------------------------------------------------------------- scenarios
    def scenarios(self) -> list[dict]:
        return [{"id": k, **{f: v[f] for f in ("title", "scam", "signals")},
                 "n_steps": 3 if v["steps"] == "normal" else len(v["steps"])} for k, v in SCENARIOS.items()]

    def default_card(self) -> str:
        """A long-history, mostly-daytime card: a typical genuine customer."""
        best = max(self.store.states.items(),
                   key=lambda kv: kv[1].n * (1.0 - kv[1].night_n / max(kv[1].n, 1)))
        return card_token(best[0])

    def run_scenario(self, sid: str, token: str | None) -> dict:
        spec = SCENARIOS[sid]
        with self.lock:
            token = token or self.default_card()
            cc = self.resolve_card(token)
            sandbox = self.store.sandbox([cc])
        summary = sandbox.card_summary(cc)
        prof = sandbox.profiles[cc]
        steps = normal_steps(summary) if spec["steps"] == "normal" else spec["steps"]
        last = sandbox.states[cc].last_ts if cc in sandbox.states else int(self.stream["unix"].iat[0])
        h, m = spec["start"]
        start = (last // 86400 + 1) * 86400 + h * 3600 + m * 60
        known = sorted(sandbox.states[cc].merchants) if cc in sandbox.states else []
        results = []
        for k, (minute, amt, cat, km, use_known) in enumerate(steps):
            lat, lon = offset_point(prof.lat, prof.long, km)
            merchant = known[k % len(known)] if use_known and known else f"New merchant #{1000 + 37 * k}"
            t = Txn(cc, int(start + minute * 60), float(amt), cat, merchant, lat, lon)
            X, summaries = self._process(sandbox, [t])
            r = self._score_batch([t], X, summaries)[0]
            r["step"] = k + 1
            r["minutes_from_start"] = minute
            results.append(r)
        return {"scenario": {"id": sid, **{f: spec[f] for f in ("title", "scam", "signals")}},
                "card": {"token": token, "last4": cc[-4:], "home_city": prof.city, "state": prof.state,
                         **summary},
                "steps": results,
                "verdict": max((r["risk_level"] for r in results), key=policy.LEVELS.index)}

    # ------------------------------------------------------------ read models
    def cards(self, limit: int = 60) -> list[dict]:
        rows = []
        for cc, st in self.store.states.items():
            prof = self.store.profiles[cc]
            rows.append({"token": card_token(cc), "last4": cc[-4:], "city": prof.city, "state": prof.state,
                         "n_txns": st.n, "mean_amt": round(st.mean, 2),
                         "night_share": round(st.night_n / max(st.n, 1), 3)})
        rows.sort(key=lambda r: -r["n_txns"])
        return rows[:limit]

    def card_detail(self, token: str) -> dict:
        cc = self.resolve_card(token)
        prof = self.store.profiles[cc]
        with Session(db.engine) as s:
            recent = s.scalars(select(db.Decision).where(db.Decision.card_token == token)
                               .order_by(db.Decision.id.desc()).limit(20)).all()
        return {"token": token, "last4": cc[-4:], "city": prof.city, "state": prof.state,
                "home": {"lat": prof.lat, "long": prof.long}, **self.store.card_summary(cc),
                "recent": [decision_dict(d) for d in recent]}

    def decisions(self, limit: int = 100, level: str | None = None, source: str | None = None,
                  status: str | None = None) -> list[dict]:
        q = select(db.Decision).order_by(db.Decision.id.desc()).limit(limit)
        if level:
            q = q.where(db.Decision.risk_level.in_(level.split(",")))
        if source:
            q = q.where(db.Decision.source == source)
        if status:
            q = q.where(db.Decision.review_status == status)
        with Session(db.engine) as s:
            return [decision_dict(d) for d in s.scalars(q).all()]

    def decision(self, did: int) -> dict:
        with Session(db.engine) as s:
            d = s.get(db.Decision, did)
            if d is None:
                raise KeyError("not found")
            out = decision_dict(d, full=True)
            exp = self.explain_record(d)            # SHAP chart for the audit view, computed on demand
            out["shap"], out["groups"] = exp["features"], exp["groups"]
            if not d.reasons and not d.mitigating:  # approved in the stream without an explanation
                out["reasons"] = [h["reason"] for h in (d.policy or [])] + exp["reasons"]
                out["mitigating"] = exp["mitigating"]
                out["explained_on_demand"] = True
            return out

    def review(self, did: int, label: str, note: str | None) -> dict:
        with Session(db.engine) as s:
            d = s.get(db.Decision, did)
            if d is None:
                raise KeyError("not found")
            d.review_status = "confirmed" if label == "fraud" else "dismissed"
            d.review_note = note
            d.reviewed_at = datetime.now(timezone.utc)
            s.commit()
            return decision_dict(d, full=True)

    def stats(self) -> dict:
        with Session(db.engine) as s:
            rows = s.execute(select(db.Decision.txn_time, db.Decision.risk_level, db.Decision.label,
                                    db.Decision.amount, db.Decision.risk_score, db.Decision.review_status,
                                    db.Decision.latency_ms, db.Decision.category)
                             .where(db.Decision.source == "stream")).all()
            reviews = Counter(s.scalars(select(db.Decision.review_status)).all())
        base = {"stream": self.status(), "reviews": dict(reviews)}
        if not rows:
            return base | {"total": 0}
        df = pd.DataFrame(rows, columns=["t", "level", "label", "amt", "risk", "review", "latency", "category"])
        fraud = df["label"] == 1
        alert = df["level"] != "LOW"
        block = df["level"] == "HIGH"
        tp, fp = int((fraud & alert).sum()), int((~fraud & alert).sum())
        df["day"] = df["t"].dt.strftime("%Y-%m-%d")
        timeline = df.groupby("day").agg(transactions=("level", "size"),
                                         alerts=("level", lambda s: int((s != "LOW").sum())),
                                         blocked=("level", lambda s: int((s == "HIGH").sum())),
                                         frauds=("label", "sum")).reset_index().tail(30)
        hist = np.histogram(df["risk"], bins=np.arange(0, 101, 10))[0]
        return native(base | {
            "total": len(df), "levels": df["level"].value_counts().to_dict(),
            "alerts": int(alert.sum()), "blocked": int(block.sum()),
            "frauds_seen": int(fraud.sum()), "frauds_caught": tp, "frauds_blocked": int((fraud & block).sum()),
            "frauds_missed": int((fraud & ~alert).sum()), "false_alarms": fp,
            "precision": tp / (tp + fp) if tp + fp else None,
            "recall": tp / int(fraud.sum()) if fraud.any() else None,
            "fraud_amount": float(df.loc[fraud, "amt"].sum()),
            "fraud_amount_stopped": float(df.loc[fraud & alert, "amt"].sum()),
            "false_alarm_rate": fp / int((~fraud).sum()) if (~fraud).any() else None,
            "avg_latency_ms": float(df["latency"].mean()),
            "risk_histogram": [{"bucket": f"{b}-{b + 10}", "count": int(c)} for b, c in zip(range(0, 100, 10), hist)],
            "timeline": timeline.to_dict("records"),
            "alerts_by_category": df.loc[alert, "category"].value_counts().head(8).to_dict(),
        })


def native(obj):
    """Convert NumPy scalars (from pandas aggregations) into plain JSON-serialisable Python types."""
    return json.loads(json.dumps(obj, default=lambda o: o.item() if hasattr(o, "item") else str(o)))


def decision_dict(d: db.Decision, full: bool = False) -> dict:
    out = {
        "id": d.id, "source": d.source, "card_token": d.card_token, "card_last4": d.card_last4,
        "txn_time": d.txn_time.isoformat(), "amount": d.amount, "category": d.category,
        "category_label": CATEGORY_LABELS.get(d.category, d.category), "merchant": d.merchant,
        "probability": d.probability, "risk_score": d.risk_score, "risk_level": d.risk_level,
        "decision": d.decision, "components": {"xgboost": d.p_xgb, "random_forest": d.p_rf,
                                               "anomaly_percentile": d.anomaly_pct},
        "reasons": d.reasons, "policy": d.policy or [], "label": d.label, "review_status": d.review_status,
        "latency_ms": d.latency_ms,
    }
    if full:
        out |= {"mitigating": d.mitigating, "features": d.features, "model_version": d.model_version,
                "review_note": d.review_note, "reviewed_at": d.reviewed_at.isoformat() if d.reviewed_at else None,
                "created_at": d.created_at.isoformat()}
    return out


CATEGORY_OPTIONS = [{"value": c, "label": CATEGORY_LABELS[c]} for c in CATEGORIES]
