"""FraudLens hybrid risk engine.

Three detectors look at every transaction:

* XGBoost: main supervised classifier (known fraud patterns)
* Random Forest: second supervised opinion with a different bias
* Isolation Forest: unsupervised novelty detector trained on genuine
  transactions only, so it flags behaviour unlike normal spending even when
  no similar fraud was ever labelled (Liu et al., 2008; Carcillo et al., 2021).

A logistic-regression meta-learner (stacked generalisation, Wolpert 1992)
learns how much to trust each detector. It is fitted on the untouched,
naturally imbalanced validation period, so its output is a calibrated fraud
probability (Niculescu-Mizil & Caruana, 2005) and not an artefact of class
re-weighting. Thresholds are then chosen on out-of-fold validation
predictions:

* alert threshold: minimises expected money lost (missed fraud + alert costs)
* block threshold: lowest score at which alerts are >= 90% precise.
"""
from __future__ import annotations

import time

import numpy as np
import xgboost as xgb
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_predict

from . import config
from .metrics import cost_optimal_threshold, precision_threshold
from .models import RF_PARAMS, XGB_PARAMS, make_isolation_forest, pos_weight

EPS = 1e-6
COMPONENTS = ("xgb", "rf", "iforest")


def logit(p: np.ndarray) -> np.ndarray:
    p = np.clip(p, EPS, 1 - EPS)
    return np.log(p / (1 - p))


class HybridRiskEngine:
    def __init__(self, feature_names: list[str], components: tuple[str, ...] = COMPONENTS,
                 iforest_features: list[str] | None = None, seed: int = config.SEED):
        self.feature_names = list(feature_names)
        self.components = tuple(components)
        self.iforest_features = list(iforest_features or feature_names)
        self._if_idx = [self.feature_names.index(f) for f in self.iforest_features]
        self.seed = seed
        self.xgb = self.rf = self.iso = self.meta = None
        self.t_alert = self.t_block = None
        self.fit_seconds: dict[str, float] = {}
        self.version = config.MODEL_VERSION

    # ------------------------------------------------------------ training
    def fit_base(self, X_tr: np.ndarray, y_tr: np.ndarray, X_val: np.ndarray, y_val: np.ndarray):
        spw = pos_weight(y_tr)
        if "xgb" in self.components:
            t0 = time.perf_counter()
            self.xgb = xgb.XGBClassifier(**{**XGB_PARAMS, "n_estimators": 1500}, scale_pos_weight=spw,
                                         early_stopping_rounds=50, random_state=self.seed,
                                         n_jobs=config.N_JOBS)
            self.xgb.fit(X_tr, y_tr, eval_set=[(X_val, y_val)], verbose=False)
            self.fit_seconds["xgb"] = time.perf_counter() - t0
        if "rf" in self.components:
            t0 = time.perf_counter()
            self.rf = RandomForestClassifier(**RF_PARAMS, class_weight="balanced_subsample",
                                             random_state=self.seed, n_jobs=config.N_JOBS)
            self.rf.fit(X_tr, y_tr)
            self.fit_seconds["rf"] = time.perf_counter() - t0
        if "iforest" in self.components:
            t0 = time.perf_counter()
            genuine = X_tr[y_tr == 0][:, self._if_idx]
            self.iso = make_isolation_forest(self.seed).fit(genuine)
            rng = np.random.default_rng(self.seed)
            ref = genuine[rng.choice(len(genuine), size=min(50_000, len(genuine)), replace=False)]
            self._if_ref = np.sort(-self.iso.score_samples(ref))
            self._if_mu, self._if_sd = float(self._if_ref.mean()), float(self._if_ref.std() + 1e-9)
            self.fit_seconds["iforest"] = time.perf_counter() - t0
        return self

    def fit_meta(self, X_val: np.ndarray, y_val: np.ndarray, amt_val: np.ndarray):
        t0 = time.perf_counter()
        Z = self.meta_features(X_val)
        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=self.seed)
        self.val_oof = cross_val_predict(LogisticRegression(C=1.0, max_iter=1000), Z, y_val,
                                         cv=cv, method="predict_proba")[:, 1]
        self.meta = LogisticRegression(C=1.0, max_iter=1000).fit(Z, y_val)
        self.t_alert = cost_optimal_threshold(y_val, self.val_oof, amt_val, config.ALERT_COST)
        self.t_block = max(precision_threshold(y_val, self.val_oof, config.BLOCK_MIN_PRECISION),
                           self.t_alert)
        self.fit_seconds["meta"] = time.perf_counter() - t0
        return self

    def fit(self, X_tr, y_tr, X_val, y_val, amt_val):
        return self.fit_base(X_tr, y_tr, X_val, y_val).fit_meta(X_val, y_val, amt_val)

    # ----------------------------------------------------------- inference
    def anomaly_raw(self, X: np.ndarray) -> np.ndarray:
        return -self.iso.score_samples(X[:, self._if_idx])

    def anomaly_percentile(self, raw: np.ndarray) -> np.ndarray:
        """Share of normal transactions that look *less* unusual than this one."""
        return np.searchsorted(self._if_ref, raw, side="right") / len(self._if_ref)

    def component_scores(self, X: np.ndarray) -> dict[str, np.ndarray]:
        out = {}
        if self.xgb is not None:
            out["xgb"] = self.xgb.predict_proba(X)[:, 1]
        if self.rf is not None:
            out["rf"] = self.rf.predict_proba(X)[:, 1]
        if self.iso is not None:
            raw = self.anomaly_raw(X)
            out["iforest_raw"] = raw
            out["iforest"] = self.anomaly_percentile(raw)
        return out

    def meta_features(self, X: np.ndarray, scores: dict | None = None) -> np.ndarray:
        s = scores or self.component_scores(X)
        cols = []
        if "xgb" in s:
            cols.append(logit(s["xgb"]))
        if "rf" in s:
            cols.append(logit(s["rf"]))
        if "iforest_raw" in s:
            cols.append((s["iforest_raw"] - self._if_mu) / self._if_sd)
        return np.column_stack(cols)

    def predict_proba(self, X: np.ndarray, scores: dict | None = None) -> np.ndarray:
        return self.meta.predict_proba(self.meta_features(X, scores))[:, 1]

    # ----------------------------------------------------------- decisions
    def risk_score(self, p: np.ndarray | float) -> np.ndarray:
        """Monotone map of probability onto 0-100 so that the team's bands
        (Low <=30 < Medium <=60 < High) sit exactly on the learned thresholds."""
        p = np.asarray(p, dtype=float)
        xs = [0.0, self.t_alert, self.t_block, 1.0]
        ys = [0.0, config.RISK_BAND_MEDIUM, config.RISK_BAND_HIGH, 100.0]
        if self.t_block <= self.t_alert:  # degenerate: no medium band
            xs, ys = [0.0, self.t_alert, 1.0], [0.0, config.RISK_BAND_HIGH, 100.0]
        return np.interp(p, xs, ys)

    def decide(self, p: float) -> tuple[str, str]:
        if p >= self.t_block:
            return "HIGH", "BLOCK"
        if p >= self.t_alert:
            return "MEDIUM", "STEP_UP"
        return "LOW", "APPROVE"

    def meta_weights(self) -> dict[str, float]:
        names = [c for c in ("xgb", "rf", "iforest") if getattr(self, {"xgb": "xgb", "rf": "rf", "iforest": "iso"}[c]) is not None]
        return {n: float(w) for n, w in zip(names, self.meta.coef_[0])} | {"intercept": float(self.meta.intercept_[0])}
