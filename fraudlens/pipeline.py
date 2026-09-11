"""Research pipeline. Run stages with:  python -m fraudlens.pipeline <stage> [<stage> ...]

  features   replay Sparkov through the FeatureStore -> feature matrix + API snapshot
  benchmark  E1  every model on the same chronological split (saves the deployed engine)
  imbalance  E2  no balancing vs class weighting vs undersampling vs SMOTE
  protocol   E3  how common evaluation shortcuts inflate results (ULB + Sparkov)
  ablation   E4  which parts of the hybrid and of the feature set matter
  unseen     E5  catching a fraud type the supervised models never saw
  ulb        E6  benchmark on the European (ULB) dataset
  analysis   E7  statistical tests, cost sensitivity, risk tiers, monthly drift
  explain    global SHAP importance + case studies
  artifacts  files the API needs (stream of test transactions, model card)
  all        everything above in order
"""
from __future__ import annotations

import json
import pickle
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
from imblearn.over_sampling import SMOTE
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss
from sklearn.model_selection import StratifiedKFold, cross_val_predict, train_test_split

from . import config, data, policy
from . import features as F
from .hybrid import HybridRiskEngine
from .metrics import (best_f1_threshold, bootstrap_ci, cost_optimal_threshold, evaluate,
                      paired_bootstrap, ranking_metrics, threshold_metrics)
from .models import (MODEL_LABELS, STRATEGIES, make_classifier, make_isolation_forest, make_model,
                     pos_weight)
from .rules import RULES, rule_scores

FEATS_PATH = config.DATA_PROCESSED / "sparkov_features.parquet"
META_PATH = config.DATA_PROCESSED / "sparkov_meta.parquet"
ENGINE_PATH = config.ARTIFACTS / "engine.joblib"
MODELS_DIR = config.ARTIFACTS / "models"        # benchmark models, kept so latency can be re-measured
STORE_PATH = config.ARTIFACTS / "feature_store.pkl"
PREDS_PATH = config.RESULTS / "preds_sparkov.npz"

FEATURE_SETS = {"raw": F.RAW_FEATURES, "deployed": F.DEPLOYED_FEATURES, "all": F.ALL_FEATURES}

# Isolation Forest looks at behaviour-deviation signals rather than one-hot
# categories, which carry no notion of "distance from normal".
IF_FEATURES = [
    "amt", "hour", "is_night", "is_online", "dist_home_km", "log_secs_since_last", "cnt_1h",
    "cnt_24h", "cnt_7d", "sum_24h", "cnt_24h_vs_usual", "amt_to_card_mean", "amt_zscore",
    "amt_to_cat_mean", "cat_share", "is_new_category", "night_share", "speed_kmh",
]


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def save_json(name: str, obj) -> None:
    path = config.RESULTS / f"{name}.json"
    path.write_text(json.dumps(obj, indent=2, default=lambda o: o.item() if hasattr(o, "item") else str(o)))
    log(f"wrote {path.relative_to(config.ROOT)}")


def load_json(name: str):
    return json.loads((config.RESULTS / f"{name}.json").read_text())


# ======================================================================= data
@dataclass
class SplitData:
    X: dict
    y: dict
    amt: dict
    frame: dict
    meta: dict
    features: list


def load_sparkov_data(feature_set: str = "deployed") -> SplitData:
    Xall = pd.read_parquet(FEATS_PATH)
    meta = pd.read_parquet(META_PATH)
    cols = FEATURE_SETS[feature_set]
    X, y, amt, frame, m = {}, {}, {}, {}, {}
    for s in ("train", "val", "test"):
        mask = (meta["split"] == s).to_numpy()
        frame[s] = Xall.loc[mask]
        X[s] = frame[s][cols].to_numpy(np.float32)
        m[s] = meta.loc[mask].reset_index(drop=True)
        y[s] = m[s]["is_fraud"].to_numpy(np.int8)
        amt[s] = m[s]["amt"].to_numpy(np.float64)
    return SplitData(X, y, amt, frame, m, list(cols))


def stage_features() -> None:
    log("loading Sparkov")
    df = data.load_sparkov()
    masks = data.sparkov_split(df)
    test_start = int(np.argmax(masks["test"]))
    store = F.FeatureStore(F.build_profiles(df))
    t0 = time.perf_counter()
    X_pre, store = F.build_feature_matrix(df.iloc[:test_start], store)
    with open(STORE_PATH, "wb") as fh:           # card state at the start of the test period
        pickle.dump(store, fh)
    X_post, store = F.build_feature_matrix(df.iloc[test_start:], store)
    secs = time.perf_counter() - t0
    X = pd.concat([X_pre, X_post]).astype("float32")
    X.to_parquet(FEATS_PATH)
    meta = df[["ts", "unix", "cc_num", "merchant", "category", "amt", "merch_lat", "merch_long",
               "is_fraud"]].copy()
    meta["split"] = np.select([masks["train"], masks["val"], masks["test"]], ["train", "val", "test"], "gap")
    meta.to_parquet(META_PATH)
    summary = {
        "rows": len(df), "frauds": int(df["is_fraud"].sum()), "fraud_rate": float(df["is_fraud"].mean()),
        "cards": int(df["cc_num"].nunique()), "merchants": int(df["merchant"].nunique()),
        "start": str(df["ts"].min()), "end": str(df["ts"].max()),
        "feature_seconds": secs, "microseconds_per_txn": secs / len(df) * 1e6,
        "n_features_all": len(F.ALL_FEATURES), "n_features_deployed": len(F.DEPLOYED_FEATURES),
        "splits": {s: {"rows": int((meta["split"] == s).sum()),
                       "frauds": int(meta.loc[meta["split"] == s, "is_fraud"].sum()),
                       "start": str(meta.loc[meta["split"] == s, "ts"].min()),
                       "end": str(meta.loc[meta["split"] == s, "ts"].max())}
                   for s in ("train", "val", "test", "gap")},
        "fraud_by_hour": df.groupby(df["ts"].dt.hour)["is_fraud"].mean().round(5).to_dict(),
        "fraud_by_category": df.groupby("category")["is_fraud"].agg(["mean", "sum", "size"]).to_dict("index"),
        "amount_by_class": df.groupby("is_fraud")["amt"].describe().to_dict("index"),
        "frauds_per_compromised_card": float(df[df.is_fraud == 1].groupby("cc_num").size().mean()),
        "compromised_cards": int(df.loc[df.is_fraud == 1, "cc_num"].nunique()),
    }
    save_json("dataset_sparkov", summary)
    log(f"features built in {secs:.1f}s ({summary['microseconds_per_txn']:.1f} us/txn)")


# ================================================================== helpers
def fit_gbdt_early_stopping(name: str, X_tr, y_tr, X_val, y_val, seed: int = config.SEED):
    """XGBoost / LightGBM with class weighting and early stopping on validation PR-AUC."""
    model = make_classifier(name, weighted=True, spw=pos_weight(y_tr), seed=seed)
    if name == "xgb":
        model.set_params(n_estimators=1500, early_stopping_rounds=50)
        model.fit(X_tr, y_tr, eval_set=[(X_val, y_val)], verbose=False)
    else:
        # Stop on PR-AUC only: with class weighting the default log-loss on the
        # (unweighted) validation data rises from the first rounds and would
        # end training almost immediately.
        # (the capped leaf step makes the first ~100 rounds slow, hence the longer patience)
        model.set_params(n_estimators=2000, metric="average_precision")
        model.fit(X_tr, y_tr, eval_X=(X_val,), eval_y=(y_val,),
                  callbacks=[lgb.early_stopping(100, first_metric_only=True, verbose=False)])
    return model


def latency(predict, X: np.ndarray, n: int = 300) -> dict:
    times = []
    for i in range(min(n, len(X))):
        t0 = time.perf_counter()
        predict(X[i:i + 1])
        times.append(time.perf_counter() - t0)
    t0 = time.perf_counter()
    batch = X[:20000]
    predict(batch)
    thr = len(batch) / (time.perf_counter() - t0)
    return {"p50_ms": float(np.median(times) * 1e3), "p95_ms": float(np.quantile(times, 0.95) * 1e3),
            "throughput_per_s": float(thr)}


def single_thread(model) -> None:
    """Online scoring is one transaction at a time: thread fan-out only adds overhead."""
    for m in (model, getattr(model, "xgb", None), getattr(model, "rf", None), getattr(model, "iso", None)):
        if m is not None and hasattr(m, "n_jobs"):
            try:
                m.set_params(n_jobs=1)
            except Exception:
                m.n_jobs = 1


def report_row(label, y_val, p_val, y_te, p_te, amt_val, amt_te, fit_s, lat=None, extra=None):
    thr_f1 = best_f1_threshold(y_val, p_val)
    thr_cost = cost_optimal_threshold(y_val, p_val, amt_val)
    row = {
        "label": label, "fit_seconds": fit_s,
        "val": ranking_metrics(y_val, p_val),
        "test": evaluate(y_te, p_te, thr_f1, amt_te),
        "test_cost_threshold": threshold_metrics(y_te, p_te, thr_cost, amt_te),
    }
    if lat:
        row["latency"] = lat
    if extra:
        row.update(extra)
    return row


# ================================================================ E1 benchmark
def stage_benchmark(models: list[str] | None = None) -> None:
    from .deep import TorchClassifier

    d = load_sparkov_data("deployed")
    names = models or ["rules", "lr", "dt", "rf", "xgb", "lgbm", "iforest", "mlp", "cnn", "hybrid"]
    path = config.RESULTS / "benchmark_sparkov.json"
    results = json.loads(path.read_text()) if path.exists() and models else {}
    preds = ({k: v for k, v in np.load(PREDS_PATH).items() if k.startswith(("val_", "test_"))}
             if PREDS_PATH.exists() and models else {})
    Xtr, ytr, Xv, yv, Xte, yte = d.X["train"], d.y["train"], d.X["val"], d.y["val"], d.X["test"], d.y["test"]
    for name in names:
        log(f"benchmark: {name}")
        t0 = time.perf_counter()
        model, extra = None, {}
        if name == "rules":
            pv, pt = rule_scores(d.frame["val"]), rule_scores(d.frame["test"])
            extra["rules"] = list(RULES)
        elif name == "iforest":
            cols = [d.features.index(f) for f in IF_FEATURES]
            model = make_isolation_forest().fit(Xtr[ytr == 0][:, cols])
            pv, pt = -model.score_samples(Xv[:, cols]), -model.score_samples(Xte[:, cols])
        elif name in ("mlp", "cnn"):
            # The CNN is several times slower per epoch on CPU, so it gets a smaller epoch budget.
            model = TorchClassifier(name, epochs=15 if name == "mlp" else 8).fit(Xtr, ytr, Xv, yv)
            pv, pt = model.predict_proba(Xv)[:, 1], model.predict_proba(Xte)[:, 1]
            extra["val_pr_auc_by_epoch"] = model.history
            extra["max_epochs"] = model.epochs
        elif name == "hybrid":
            model = HybridRiskEngine(d.features, iforest_features=IF_FEATURES).fit(Xtr, ytr, Xv, yv, d.amt["val"])
            pv, pt = model.val_oof, model.predict_proba(Xte)
            extra.update(thresholds={"alert": model.t_alert, "block": model.t_block},
                         meta_weights=model.meta_weights(), component_fit_seconds=model.fit_seconds,
                         xgb_best_iteration=int(model.xgb.best_iteration))
        elif name in ("xgb", "lgbm"):
            model = fit_gbdt_early_stopping(name, Xtr, ytr, Xv, yv)
            pv, pt = model.predict_proba(Xv)[:, 1], model.predict_proba(Xte)[:, 1]
        else:
            model = make_model(name, "weight", ytr).fit(Xtr, ytr)
            pv, pt = model.predict_proba(Xv)[:, 1], model.predict_proba(Xte)[:, 1]
        fit_s = time.perf_counter() - t0
        lat = None
        if model is not None:
            single_thread(model)
            if name == "iforest":
                lat = latency(lambda x: model.score_samples(x[:, cols]), Xte)
            else:
                lat = latency(model.predict_proba, Xte)
        results[name] = report_row(MODEL_LABELS[name], yv, pv, yte, pt, d.amt["val"], d.amt["test"],
                                   fit_s, lat, extra)
        preds[f"val_{name}"], preds[f"test_{name}"] = pv.astype(np.float32), pt.astype(np.float32)
        if name == "hybrid":
            joblib.dump(model, ENGINE_PATH, compress=3)
            results[name]["model_size_mb"] = ENGINE_PATH.stat().st_size / 1e6
        elif model is not None:
            MODELS_DIR.mkdir(exist_ok=True)
            joblib.dump(model, MODELS_DIR / f"{name}.joblib", compress=3)
        log(f"  {name}: test PR-AUC={results[name]['test']['pr_auc']:.4f} "
            f"F1={results[name]['test']['f1']:.4f} fit={fit_s:.0f}s")
        save_json("benchmark_sparkov", results)
        np.savez_compressed(PREDS_PATH, y_val=yv, y_test=yte, amt_val=d.amt["val"], amt_test=d.amt["test"], **preds)


# ================================================================ E2 imbalance
def stage_imbalance() -> None:
    d = load_sparkov_data("deployed")
    Xtr, ytr, Xv, yv, Xte, yte = d.X["train"], d.y["train"], d.X["val"], d.y["val"], d.X["test"], d.y["test"]
    out = {}
    for name in ("lr", "rf", "xgb"):
        for strat in STRATEGIES:
            key = f"{name}/{strat}"
            log(f"imbalance: {key}")
            t0 = time.perf_counter()
            model = make_model(name, strat, ytr).fit(Xtr, ytr)
            fit_s = time.perf_counter() - t0
            pv, pt = model.predict_proba(Xv)[:, 1], model.predict_proba(Xte)[:, 1]
            thr = best_f1_threshold(yv, pv)
            out[key] = {
                "model": MODEL_LABELS[name], "strategy": STRATEGIES[strat], "fit_seconds": fit_s,
                **ranking_metrics(yte, pt),
                "brier": float(brier_score_loss(yte, pt)),
                "mean_predicted_prob": float(pt.mean()), "actual_fraud_rate": float(yte.mean()),
                "at_0.5": threshold_metrics(yte, pt, 0.5),
                "at_tuned": threshold_metrics(yte, pt, thr),
            }
            log(f"  PR-AUC={out[key]['pr_auc']:.4f} F1@tuned={out[key]['at_tuned']['f1']:.4f} "
                f"F1@0.5={out[key]['at_0.5']['f1']:.4f} brier={out[key]['brier']:.5f}")
            save_json("imbalance_sparkov", out)


# ================================================================= E3 protocol
def protocol_experiment(X: np.ndarray, y: np.ndarray, masks: dict, name: str) -> dict:
    """Same XGBoost model, four evaluation protocols of increasing rigour."""
    seed = config.SEED
    params = dict(n_estimators=300, learning_rate=0.1, max_depth=6, tree_method="hist",
                  random_state=seed, n_jobs=config.N_JOBS)
    import xgboost as xgb
    rows = {}
    te = masks["test"]
    rows["dummy"] = {"protocol": "Predict 'genuine' for everything (no model)",
                     **threshold_metrics(y[te], np.zeros(te.sum()), 0.5), "pr_auc": float(y[te].mean())}
    log(f"protocol[{name}] A: SMOTE before random split")
    Xs, ys = SMOTE(random_state=seed).fit_resample(X, y)
    a_tr, a_te, b_tr, b_te = train_test_split(Xs, ys, test_size=0.2, stratify=ys, random_state=seed)
    p = xgb.XGBClassifier(**params).fit(a_tr, b_tr).predict_proba(a_te)[:, 1]
    rows["A"] = {"protocol": "SMOTE on the whole dataset, then random 80/20 split, threshold 0.5",
                 **evaluate(b_te, p, 0.5), "test_fraud_share": float(b_te.mean())}
    log(f"protocol[{name}] B: random split, SMOTE on train only")
    a_tr, a_te, b_tr, b_te = train_test_split(X, y, test_size=0.2, stratify=y, random_state=seed)
    Xs, ys = SMOTE(random_state=seed).fit_resample(a_tr, b_tr)
    p = xgb.XGBClassifier(**params).fit(Xs, ys).predict_proba(a_te)[:, 1]
    rows["B"] = {"protocol": "Random split first, SMOTE on training data only, threshold 0.5",
                 **evaluate(b_te, p, 0.5), "test_fraud_share": float(b_te.mean())}
    tr, va = masks["train"], masks["val"]
    log(f"protocol[{name}] C: chronological split + SMOTE on train")
    Xs, ys = SMOTE(random_state=seed).fit_resample(X[tr], y[tr])
    m = xgb.XGBClassifier(**params).fit(Xs, ys)
    thr = best_f1_threshold(y[va], m.predict_proba(X[va])[:, 1])
    rows["C"] = {"protocol": "Chronological split, SMOTE on training data only, threshold tuned on validation",
                 **evaluate(y[te], m.predict_proba(X[te])[:, 1], thr), "test_fraud_share": float(y[te].mean())}
    log(f"protocol[{name}] D: chronological split + class weighting")
    m = xgb.XGBClassifier(**params, scale_pos_weight=pos_weight(y[tr])).fit(X[tr], y[tr])
    thr = best_f1_threshold(y[va], m.predict_proba(X[va])[:, 1])
    rows["D"] = {"protocol": "Chronological split, class weighting (no synthetic data), threshold tuned on validation (FraudLens)",
                 **evaluate(y[te], m.predict_proba(X[te])[:, 1], thr), "test_fraud_share": float(y[te].mean())}
    return rows


def stage_protocol() -> None:
    ulb = data.load_ulb()
    Xu, yu = data.ulb_features(ulb)
    out = {"ulb": protocol_experiment(Xu.to_numpy(np.float32), yu, data.ulb_split(len(ulb)), "ulb")}
    save_json("protocol", out)
    d = load_sparkov_data("deployed")
    X = np.vstack([d.X["train"], d.X["val"], d.X["test"]])
    y = np.concatenate([d.y["train"], d.y["val"], d.y["test"]])
    n1, n2 = len(d.y["train"]), len(d.y["val"])
    idx = np.arange(len(y))
    masks = {"train": idx < n1, "val": (idx >= n1) & (idx < n1 + n2), "test": idx >= n1 + n2}
    out["sparkov"] = protocol_experiment(X, y, masks, "sparkov")
    save_json("protocol", out)


# ================================================================= E4 ablation
def _stack_eval(combo, S_val, S_te, yv, yte, engine):
    def z(S):
        cols = []
        for c in combo:
            if c == "iforest":
                cols.append((S["iforest_raw"] - engine._if_mu) / engine._if_sd)
            else:
                cols.append(np.log(np.clip(S[c], 1e-6, 1 - 1e-6) / (1 - np.clip(S[c], 1e-6, 1 - 1e-6))))
        return np.column_stack(cols)
    Zv, Zt = z(S_val), z(S_te)
    cv = StratifiedKFold(5, shuffle=True, random_state=config.SEED)
    oof = cross_val_predict(LogisticRegression(max_iter=1000), Zv, yv, cv=cv, method="predict_proba")[:, 1]
    p = LogisticRegression(max_iter=1000).fit(Zv, yv).predict_proba(Zt)[:, 1]
    return oof, p


def load_engine() -> HybridRiskEngine:
    """The saved engine is tuned for one-at-a-time API scoring; use all cores for batch work."""
    engine = joblib.load(ENGINE_PATH)
    for m in (engine.xgb, engine.rf, engine.iso):
        m.set_params(n_jobs=config.N_JOBS)
    return engine


def stage_ablation() -> None:
    out = {"feature_sets": {}, "components": {}}
    ref = None
    # "deployed" first so the other feature sets can be tested against it
    for fs, label in (("deployed", "+ behavioural features (FraudLens, protected attributes excluded)"),
                      ("raw", "Raw transaction fields only (typical project)"),
                      ("all", "+ age and gender (protected attributes)")):
        log(f"ablation features: {fs}")
        d = load_sparkov_data(fs)
        t0 = time.perf_counter()
        m = fit_gbdt_early_stopping("xgb", d.X["train"], d.y["train"], d.X["val"], d.y["val"])
        pv, pt = m.predict_proba(d.X["val"])[:, 1], m.predict_proba(d.X["test"])[:, 1]
        out["feature_sets"][fs] = report_row(label, d.y["val"], pv, d.y["test"], pt, d.amt["val"], d.amt["test"],
                                             time.perf_counter() - t0, extra={"n_features": len(d.features)})
        if fs == "deployed":
            ref = pt
        else:
            out["feature_sets"][fs]["vs_deployed"] = paired_bootstrap(d.y["test"], pt, ref, n=500)
        save_json("ablation", out)
    out["feature_sets"] = {k: out["feature_sets"][k] for k in ("raw", "deployed", "all")}

    d = load_sparkov_data("deployed")
    engine = load_engine()
    yv, yte = d.y["val"], d.y["test"]
    S_val, S_te = engine.component_scores(d.X["val"]), engine.component_scores(d.X["test"])
    combos = {
        "xgb": ("xgb",), "rf": ("rf",), "iforest": ("iforest",), "xgb+rf": ("xgb", "rf"),
        "xgb+iforest": ("xgb", "iforest"), "rf+iforest": ("rf", "iforest"), "xgb+rf+iforest": ("xgb", "rf", "iforest"),
    }
    preds = {}
    for key, combo in combos.items():
        log(f"ablation components: {key}")
        oof, p = _stack_eval(combo, S_val, S_te, yv, yte, engine)
        preds[key] = p
        out["components"][key] = report_row(key, yv, oof, yte, p, d.amt["val"], d.amt["test"], 0.0)
    avg_v, avg_t = (S_val["xgb"] + S_val["rf"]) / 2, (S_te["xgb"] + S_te["rf"]) / 2
    out["components"]["avg(xgb,rf)"] = report_row("simple average of XGB and RF", yv, avg_v, yte, avg_t,
                                                  d.amt["val"], d.amt["test"], 0.0)
    log("ablation: Isolation-Forest score as an extra XGBoost feature (Carcillo et al. 2021)")
    z = lambda S: ((S["iforest_raw"] - engine._if_mu) / engine._if_sd)[:, None]
    S_tr = engine.component_scores(d.X["train"])
    m = fit_gbdt_early_stopping("xgb", np.hstack([d.X["train"], z(S_tr)]), d.y["train"],
                                np.hstack([d.X["val"], z(S_val)]), yv)
    pv = m.predict_proba(np.hstack([d.X["val"], z(S_val)]))[:, 1]
    pt = m.predict_proba(np.hstack([d.X["test"], z(S_te)]))[:, 1]
    out["components"]["xgb_with_if_feature"] = report_row("XGBoost with IF score as input feature", yv, pv, yte, pt,
                                                          d.amt["val"], d.amt["test"], 0.0)
    for key in out["components"]:
        if key != "xgb":
            p = preds.get(key, pt if key == "xgb_with_if_feature" else avg_t)
            out["components"][key]["vs_xgb"] = paired_bootstrap(yte, p, preds["xgb"], n=500)
    save_json("ablation", out)


# ================================================================== E5 unseen
def stage_unseen() -> None:
    d = load_sparkov_data("deployed")
    full = load_engine()
    online = {s: d.meta[s]["category"].isin(F.ONLINE_CATEGORIES).to_numpy() for s in ("train", "val", "test")}
    out = {}
    for held in ("online", "in_person"):
        log(f"unseen: hold out {held} fraud")
        kind = {s: online[s] if held == "online" else ~online[s] for s in online}
        keep_tr = ~((d.y["train"] == 1) & kind["train"])
        keep_va = ~((d.y["val"] == 1) & kind["val"])
        eng = HybridRiskEngine(d.features, iforest_features=IF_FEATURES).fit(
            d.X["train"][keep_tr], d.y["train"][keep_tr], d.X["val"][keep_va], d.y["val"][keep_va],
            d.amt["val"][keep_va])
        te = (d.y["test"] == 0) | kind["test"]
        Xt, yt = d.X["test"][te], d.y["test"][te]
        Sv = eng.component_scores(d.X["val"][keep_va])
        St = eng.component_scores(Xt)
        yv, av = d.y["val"][keep_va], d.amt["val"][keep_va]
        rows = {}
        for comp in ("xgb", "rf", "iforest"):
            thr = cost_optimal_threshold(yv, Sv[comp], av)
            rows[comp] = {**ranking_metrics(yt, St[comp]), **threshold_metrics(yt, St[comp], thr)}
        ph = eng.predict_proba(Xt, St)
        rows["hybrid"] = {**ranking_metrics(yt, ph), **threshold_metrics(yt, ph, eng.t_alert)}
        masks = policy.evaluate_matrix(Xt, d.features, St["iforest"])
        rows["novelty_alarm"] = threshold_metrics(yt, masks["N1"].astype(float), 0.5)
        final = (ph >= eng.t_alert) | np.logical_or.reduce(list(masks.values()))
        rows["hybrid_with_policy"] = threshold_metrics(yt, final.astype(float), 0.5)
        pf = full.predict_proba(Xt)
        rows["hybrid_trained_on_all_types"] = {**ranking_metrics(yt, pf), **threshold_metrics(yt, pf, full.t_alert)}
        out[held] = {"held_out_frauds_in_test": int(yt.sum()),
                     "frauds_removed_from_training": int((~keep_tr).sum() + (~keep_va).sum()),
                     "results": rows}
        save_json("unseen", out)


# ===================================================================== E6 ULB
def stage_ulb() -> None:
    from .deep import TorchClassifier

    ulb = data.load_ulb()
    Xdf, y = data.ulb_features(ulb)
    X = Xdf.to_numpy(np.float32)
    amt = ulb["Amount"].to_numpy(float)
    m = data.ulb_split(len(ulb))
    Xtr, ytr, Xv, yv, Xte, yte = X[m["train"]], y[m["train"]], X[m["val"]], y[m["val"]], X[m["test"]], y[m["test"]]
    results, preds = {}, {}
    for name in ("lr", "rf", "xgb", "lgbm", "iforest", "mlp", "hybrid"):
        log(f"ulb: {name}")
        t0 = time.perf_counter()
        if name == "iforest":
            model = make_isolation_forest().fit(Xtr[ytr == 0])
            pv, pt = -model.score_samples(Xv), -model.score_samples(Xte)
        elif name == "mlp":
            model = TorchClassifier("mlp").fit(Xtr, ytr, Xv, yv)
            pv, pt = model.predict_proba(Xv)[:, 1], model.predict_proba(Xte)[:, 1]
        elif name == "hybrid":
            model = HybridRiskEngine(list(Xdf.columns)).fit(Xtr, ytr, Xv, yv, amt[m["val"]])
            pv, pt = model.val_oof, model.predict_proba(Xte)
        elif name in ("xgb", "lgbm"):
            model = fit_gbdt_early_stopping(name, Xtr, ytr, Xv, yv)
            pv, pt = model.predict_proba(Xv)[:, 1], model.predict_proba(Xte)[:, 1]
        else:
            model = make_model(name, "weight", ytr).fit(Xtr, ytr)
            pv, pt = model.predict_proba(Xv)[:, 1], model.predict_proba(Xte)[:, 1]
        results[name] = report_row(MODEL_LABELS[name], yv, pv, yte, pt, amt[m["val"]], amt[m["test"]],
                                   time.perf_counter() - t0)
        lo_hi = bootstrap_ci(yte, pt, n=500)
        results[name]["test"]["pr_auc_ci"] = [lo_hi[1], lo_hi[2]]
        preds[f"test_{name}"] = pt.astype(np.float32)
        log(f"  PR-AUC={results[name]['test']['pr_auc']:.4f} F1={results[name]['test']['f1']:.4f}")
    results["_dataset"] = {"rows": len(ulb), "frauds": int(y.sum()), "fraud_rate": float(y.mean()),
                           "splits": {s: {"rows": int(v.sum()), "frauds": int(y[v].sum())} for s, v in m.items()}}
    results["_pairwise_vs_hybrid"] = {n: paired_bootstrap(yte, preds["test_hybrid"], preds[f"test_{n}"], n=500)
                                      for n in ("xgb", "rf", "lgbm", "lr", "mlp")}
    save_json("benchmark_ulb", results)
    np.savez_compressed(config.RESULTS / "preds_ulb.npz", y_test=yte, **preds)


# ================================================================ E7 analysis
def stage_analysis() -> None:
    P = dict(np.load(PREDS_PATH))
    yv, yte, av, ate = P["y_val"], P["y_test"], P["amt_val"], P["amt_test"]
    engine = joblib.load(ENGINE_PATH)
    meta = pd.read_parquet(META_PATH)
    mt = meta[meta["split"] == "test"].reset_index(drop=True)
    ph, pv = P["test_hybrid"], P["val_hybrid"]
    out = {}

    log("analysis: bootstrap confidence intervals and paired tests")
    names = [k[5:] for k in P if k.startswith("test_") and k[5:] not in ("rules", "iforest")]
    out["pr_auc_ci"] = {n: dict(zip(("value", "low", "high"), bootstrap_ci(yte, P[f"test_{n}"], n=500))) for n in names}
    out["hybrid_vs"] = {n: paired_bootstrap(yte, ph, P[f"test_{n}"], n=500) for n in names if n != "hybrid"}

    log("analysis: cost sensitivity")
    days = (mt["ts"].max() - mt["ts"].min()).total_seconds() / 86400
    rows = []
    for c in config.ALERT_COST_SENSITIVITY:
        thr = cost_optimal_threshold(yv, pv, av, c)
        r = threshold_metrics(yte, ph, thr, ate, c)
        rows.append({"alert_cost": c, **r, "alerts_per_day": (r["tp"] + r["fp"]) / days})
    out["cost_sensitivity"] = rows

    log("analysis: risk tiers")
    tiers = np.where(ph >= engine.t_block, "HIGH", np.where(ph >= engine.t_alert, "MEDIUM", "LOW"))
    out["tiers"] = {}
    for t in ("LOW", "MEDIUM", "HIGH"):
        mask = tiers == t
        out["tiers"][t] = {"transactions": int(mask.sum()), "share": float(mask.mean()),
                           "frauds": int(yte[mask].sum()),
                           "fraud_rate": float(yte[mask].mean()) if mask.any() else 0.0,
                           "fraud_amount": float(ate[mask & (yte == 1)].sum()),
                           "per_day": float(mask.sum() / days)}
    out["tiers_thresholds"] = {"alert": engine.t_alert, "block": engine.t_block,
                               "risk_band_medium": config.RISK_BAND_MEDIUM, "risk_band_high": config.RISK_BAND_HIGH}
    out["test_days"] = days

    log("analysis: monthly stability and drift")
    month = mt["ts"].dt.to_period("M").astype(str).to_numpy()
    out["monthly"] = {}
    for mo in sorted(set(month)):
        k = month == mo
        out["monthly"][mo] = {"transactions": int(k.sum()), "frauds": int(yte[k].sum()),
                              **ranking_metrics(yte[k], ph[k]), **threshold_metrics(yte[k], ph[k], engine.t_alert)}
    edges = np.quantile(pv, np.linspace(0, 1, 11))
    edges[0], edges[-1] = -np.inf, np.inf
    edges = np.unique(edges)
    e = np.histogram(pv, edges)[0] / len(pv) + 1e-6
    a = np.histogram(ph, edges)[0] / len(ph) + 1e-6
    out["psi_val_to_test"] = float(np.sum((a - e) * np.log(a / e)))
    save_json("analysis", out)


# ================================================================= explain
def stage_explain() -> None:
    from .explain import FEATURE_LABELS, explain_row, shap_values

    d = load_sparkov_data("deployed")
    engine = load_engine()
    rng = np.random.default_rng(config.SEED)
    yte = d.y["test"]
    idx = np.r_[np.where(yte == 1)[0], rng.choice(np.where(yte == 0)[0], 6000, replace=False)]
    Xs = d.X["test"][idx]
    log("explain: global TreeSHAP")
    sv, _ = shap_values(engine.xgb, Xs)   # exact TreeSHAP, same code path as the live API
    imp = np.abs(sv).mean(axis=0)
    order = np.argsort(-imp)
    np.savez_compressed(config.RESULTS / "shap_sample.npz", shap=sv.astype(np.float32), X=Xs, y=yte[idx],
                        features=np.array(d.features))
    out = {"global_importance": [{"feature": d.features[i], "label": FEATURE_LABELS.get(d.features[i], d.features[i]),
                                  "mean_abs_shap": float(imp[i])} for i in order]}

    log("explain: case studies")
    ph = np.load(PREDS_PATH)["test_hybrid"]
    tiers = np.where(ph >= engine.t_block, "HIGH", np.where(ph >= engine.t_alert, "MEDIUM", "LOW"))
    mt = d.meta["test"]
    comp = engine.component_scores(d.X["test"])
    cases, seen_groups = [], set()

    def case(i, kind):
        e = explain_row(engine.xgb, d.features, d.X["test"][i], mt.loc[i, "category"])
        return {"kind": kind, "index": int(i), "ts": str(mt.loc[i, "ts"]), "amount": float(mt.loc[i, "amt"]),
                "category": mt.loc[i, "category"], "merchant": mt.loc[i, "merchant"], "is_fraud": int(yte[i]),
                "probability": float(ph[i]), "risk_score": float(engine.risk_score(ph[i])), "tier": tiers[i],
                "components": {"xgb": float(comp["xgb"][i]), "rf": float(comp["rf"][i]),
                               "anomaly_percentile": float(comp["iforest"][i])},
                "reasons": e["reasons"], "mitigating": e["mitigating"], "top_groups": e["groups"][:4],
                "features": {k: float(v) for k, v in zip(d.features, d.X["test"][i]) if not k.startswith("cat_")}}

    caught = np.where((yte == 1) & (tiers == "HIGH"))[0]
    for i in rng.permutation(caught):
        e = explain_row(engine.xgb, d.features, d.X["test"][i], mt.loc[i, "category"])
        top = e["groups"][0]["group"]
        if top not in seen_groups:
            seen_groups.add(top)
            cases.append(case(i, "fraud caught (HIGH risk)"))
        if len(cases) >= 4:
            break
    step = np.where((yte == 1) & (tiers == "MEDIUM"))[0]
    if len(step):
        cases.append(case(int(rng.choice(step)), "fraud sent to step-up verification (MEDIUM)"))
    fp = np.where((yte == 0) & (tiers == "HIGH"))[0]
    if len(fp):
        cases.append(case(int(fp[np.argmax(ph[fp])]), "false alarm (genuine blocked)"))
    missed = np.where((yte == 1) & (tiers == "LOW"))[0]
    if len(missed):
        biggest = missed[np.argmax(d.amt["test"][missed])]
        cases.append(case(int(biggest), "missed fraud (approved)"))
    genuine = np.where((yte == 0) & (tiers == "LOW"))[0]
    cases.append(case(int(rng.choice(genuine)), "normal transaction (approved)"))
    out["cases"] = cases
    save_json("explain", out)


# ============================================================== artifacts
def stage_artifacts() -> None:
    meta = pd.read_parquet(META_PATH)
    stream = meta[meta["split"] == "test"].drop(columns=["split"]).reset_index(drop=True)
    stream.to_parquet(config.ARTIFACTS / "stream.parquet")
    bench = load_json("benchmark_sparkov")
    engine = joblib.load(ENGINE_PATH)
    ds = load_json("dataset_sparkov")
    card = {
        "model_version": config.MODEL_VERSION,
        "trained_at": time.strftime("%Y-%m-%d"),
        "training_data": ds["splits"],
        "features": engine.feature_names,
        "iforest_features": engine.iforest_features,
        "thresholds": {"alert": engine.t_alert, "block": engine.t_block},
        "alert_cost_usd": config.ALERT_COST,
        "block_min_precision": config.BLOCK_MIN_PRECISION,
        "meta_weights": engine.meta_weights(),
        "test_metrics": bench["hybrid"]["test"],
        "test_cost_metrics": bench["hybrid"]["test_cost_threshold"],
        "latency": bench["hybrid"].get("latency"),
    }
    (config.ARTIFACTS / "model_card.json").write_text(json.dumps(card, indent=2, default=float))
    log("wrote artifacts/stream.parquet and artifacts/model_card.json")


def stage_latency() -> None:
    """Latency on an idle machine: one thread, one transaction per call.

    Kept separate from training so every model is timed under the same
    conditions (timing right after training is distorted by whatever else runs).
    Also times the full API path: feature store + three models + safety layer
    + SHAP explanation + decision-log write.
    """
    import os
    import tempfile
    from datetime import datetime, timezone
    from types import SimpleNamespace

    d = load_sparkov_data("deployed")
    Xte = d.X["test"]
    bench = load_json("benchmark_sparkov")
    cols = [d.features.index(f) for f in IF_FEATURES]
    for name in list(bench):
        path = ENGINE_PATH if name == "hybrid" else MODELS_DIR / f"{name}.joblib"
        if name == "rules":
            continue
        if not path.exists():
            bench[name].pop("latency", None)
            bench[name]["latency_note"] = "not re-measured on an idle machine"
            continue
        model = joblib.load(path)
        single_thread(model)
        fn = (lambda x, m=model: m.score_samples(x[:, cols])) if name == "iforest" else model.predict_proba
        bench[name]["latency"] = latency(fn, Xte)
        log(f"latency {name}: p50 {bench[name]['latency']['p50_ms']:.2f} ms")
    save_json("benchmark_sparkov", bench)

    os.environ["FRAUDLENS_DB_URL"] = f"sqlite:///{(Path(tempfile.gettempdir()) / 'fraudlens_lat.db').as_posix()}"
    from .api.service import FraudService, card_token

    svc = FraudService()
    times = []
    for r in svc.stream.iloc[:300].itertuples():
        req = SimpleNamespace(card_token=card_token(r.cc_num), amount=float(r.amt), category=r.category,
                              timestamp=datetime.fromtimestamp(int(r.unix), tz=timezone.utc).replace(tzinfo=None),
                              merchant=r.merchant, known_merchant=False, distance_km=None,
                              merch_lat=float(r.merch_lat), merch_long=float(r.merch_long), commit=False)
        t0 = time.perf_counter()
        svc.score(req)
        times.append(time.perf_counter() - t0)
    t0 = time.perf_counter()
    n = len(svc.stream_next(1000))
    stream_s = time.perf_counter() - t0
    out = {
        "note": "single thread per model, one transaction per call, idle laptop CPU",
        "models": {k: v.get("latency") for k, v in bench.items() if v.get("latency")},
        "api_single_ms": {"p50": float(np.median(times) * 1e3), "p95": float(np.quantile(times, 0.95) * 1e3)},
        "api_stream": {"transactions": n, "seconds": stream_s, "ms_per_txn": stream_s / max(n, 1) * 1e3,
                       "per_second": n / stream_s},
    }
    save_json("latency", out)
    card_path = config.ARTIFACTS / "model_card.json"
    if card_path.exists():
        card = json.loads(card_path.read_text())
        card["latency"] = bench["hybrid"]["latency"]
        card["api_latency_ms"] = out["api_single_ms"]
        card_path.write_text(json.dumps(card, indent=2, default=float))
    log(f"API single score p50 {out['api_single_ms']['p50']:.1f} ms; stream {out['api_stream']['per_second']:.0f} txn/s")


def stage_policy() -> None:
    """Cost and benefit of the policy rules + novelty alarm on real validation and test data."""
    d = load_sparkov_data("deployed")
    engine = load_engine()
    out = {"rules": policy.RULE_INFO, "novelty_percentile": policy.NOVELTY_PERCENTILE}
    for split in ("val", "test"):
        X, y, amt = d.X[split], d.y[split], d.amt[split]
        S = engine.component_scores(X)
        ml = engine.predict_proba(X, S) >= engine.t_alert
        masks = policy.evaluate_matrix(X, d.features, S["iforest"])
        days = (d.meta[split]["ts"].max() - d.meta[split]["ts"].min()).total_seconds() / 86400
        rules = {}
        for rid, m in masks.items():
            extra = m & ~ml
            rules[rid] = {"fires": int(m.sum()), "fires_on_genuine": int((m & (y == 0)).sum()),
                          "fraud_rate": float(y[m].mean()) if m.any() else 0.0,
                          "extra_alerts": int(extra.sum()), "extra_frauds": int((extra & (y == 1)).sum()),
                          "extra_alerts_per_day": float(extra.sum() / days)}
        final = ml | np.logical_or.reduce(list(masks.values()))
        out[split] = {"days": days, "rules": rules,
                      "ml_only": threshold_metrics(y, ml.astype(float), 0.5, amt),
                      "ml_plus_policy": threshold_metrics(y, final.astype(float), 0.5, amt),
                      "extra_alerts_per_day": float((final & ~ml).sum() / days)}
        log(f"policy[{split}]: ML alerts {int(ml.sum())}, +policy {int((final & ~ml).sum())} "
            f"({out[split]['extra_alerts_per_day']:.2f}/day), extra frauds {int((final & ~ml & (y == 1)).sum())}")
    save_json("policy", out)


def stage_scenarios() -> None:
    """Run every scam scenario through the real API service (sandboxed) for the report."""
    import os
    import tempfile

    os.environ["FRAUDLENS_DB_URL"] = f"sqlite:///{(Path(tempfile.gettempdir()) / 'fraudlens_scen.db').as_posix()}"
    from .api.service import FraudService

    svc = FraudService()
    out = {}
    for sc in svc.scenarios():
        res = svc.run_scenario(sc["id"], None)
        out[sc["id"]] = {
            "title": sc["title"], "scam": sc["scam"], "signals": sc["signals"], "verdict": res["verdict"],
            "card": {k: res["card"].get(k) for k in ("last4", "home_city", "state", "n_txns", "mean_amt", "txns_per_day",
                                                     "night_share", "top_categories")},
            "steps": [{k: s[k] for k in ("step", "minutes_from_start", "txn_time", "amount", "category_label",
                                         "probability", "risk_score", "risk_level", "decision", "ml_risk_score",
                                         "ml_risk_level", "policy", "reasons", "mitigating", "components",
                                         "latency_ms")} for s in res["steps"]],
        }
        log(f"  {sc['id']}: verdict {res['verdict']} "
            f"(max risk {max(s['risk_score'] for s in res['steps']):.0f})")
    save_json("scenarios", out)


STAGES = {
    "features": stage_features, "benchmark": stage_benchmark, "imbalance": stage_imbalance,
    "protocol": stage_protocol, "ablation": stage_ablation, "unseen": stage_unseen, "ulb": stage_ulb,
    "analysis": stage_analysis, "explain": stage_explain, "artifacts": stage_artifacts,
    "latency": stage_latency, "policy": stage_policy, "scenarios": stage_scenarios,
}


def main(argv: list[str]) -> None:
    stages = list(STAGES) if argv == ["all"] else argv
    for s in stages:
        if ":" in s:  # e.g. benchmark:xgb,hybrid re-runs only those models
            name, arg = s.split(":", 1)
            log(f"=== stage {name} ({arg}) ===")
            STAGES[name](arg.split(","))
        else:
            log(f"=== stage {s} ===")
            STAGES[s]()


if __name__ == "__main__":
    main(sys.argv[1:] or ["all"])
