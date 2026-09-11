"""Evaluation metrics suited to rare-event detection.

Accuracy is reported only to show why it is misleading (predicting "genuine"
for everything already scores ~99.5%). The primary metric is PR-AUC (average
precision; Saito & Rehmsmeier, 2015), backed by recall, precision, F1, MCC
(Chicco & Jurman, 2020) and a money-based cost (Elkan, 2001).
"""
from __future__ import annotations

import numpy as np
from sklearn.metrics import average_precision_score, roc_auc_score

from . import config


def confusion(y: np.ndarray, alert: np.ndarray) -> tuple[int, int, int, int]:
    y = y.astype(bool)
    alert = alert.astype(bool)
    tp = int(np.sum(y & alert))
    fp = int(np.sum(~y & alert))
    fn = int(np.sum(y & ~alert))
    tn = int(np.sum(~y & ~alert))
    return tp, fp, fn, tn


def mcc(tp: int, fp: int, fn: int, tn: int) -> float:
    denom = np.sqrt(float(tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
    return float((tp * tn - fp * fn) / denom) if denom else 0.0


def threshold_metrics(y: np.ndarray, p: np.ndarray, threshold: float,
                      amt: np.ndarray | None = None, alert_cost: float = config.ALERT_COST) -> dict:
    alert = p >= threshold
    tp, fp, fn, tn = confusion(y, alert)
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    out = {
        "threshold": float(threshold),
        "precision": prec, "recall": rec,
        "f1": 2 * prec * rec / (prec + rec) if prec + rec else 0.0,
        "mcc": mcc(tp, fp, fn, tn),
        "accuracy": (tp + tn) / len(y),
        "fpr": fp / (fp + tn) if fp + tn else 0.0,
        "alert_rate": float(alert.mean()),
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
    }
    if amt is not None:
        out.update(money_metrics(y, alert, amt, alert_cost))
    return out


def money_metrics(y: np.ndarray, alert: np.ndarray, amt: np.ndarray, alert_cost: float) -> dict:
    y = y.astype(bool)
    fraud_total = float(amt[y].sum())
    caught = float(amt[y & alert].sum())
    cost = (fraud_total - caught) + alert_cost * float(alert.sum())
    return {
        "fraud_amount_total": fraud_total,
        "fraud_amount_caught": caught,
        "amount_recall": caught / fraud_total if fraud_total else 0.0,
        "cost": cost,
        "savings": fraud_total - cost,
        "savings_pct": (fraud_total - cost) / fraud_total if fraud_total else 0.0,
    }


def ranking_metrics(y: np.ndarray, p: np.ndarray) -> dict:
    return {"pr_auc": float(average_precision_score(y, p)), "roc_auc": float(roc_auc_score(y, p))}


def evaluate(y: np.ndarray, p: np.ndarray, threshold: float, amt: np.ndarray | None = None,
             alert_cost: float = config.ALERT_COST) -> dict:
    return {**ranking_metrics(y, p), **threshold_metrics(y, p, threshold, amt, alert_cost)}


# ------------------------------------------------------------ threshold choice
def best_f1_threshold(y: np.ndarray, p: np.ndarray) -> float:
    order = np.argsort(-p, kind="stable")
    ys, ps = y[order], p[order]
    tp = np.cumsum(ys)
    k = np.arange(1, len(ys) + 1)
    prec, rec = tp / k, tp / max(1, ys.sum())
    f1 = np.where(prec + rec > 0, 2 * prec * rec / (prec + rec + 1e-12), 0)
    # only consider cut points between distinct scores
    last_of_tie = np.r_[ps[1:] != ps[:-1], True]
    f1 = np.where(last_of_tie, f1, -1)
    return float(ps[int(np.argmax(f1))])


def cost_optimal_threshold(y: np.ndarray, p: np.ndarray, amt: np.ndarray,
                           alert_cost: float = config.ALERT_COST) -> float:
    """Threshold minimising missed-fraud dollars + alert_cost x number of alerts."""
    order = np.argsort(-p, kind="stable")
    ys, ps, am = y[order].astype(bool), p[order], amt[order]
    caught = np.cumsum(np.where(ys, am, 0.0))
    k = np.arange(1, len(ys) + 1)
    cost = (am[ys].sum() - caught) + alert_cost * k
    last_of_tie = np.r_[ps[1:] != ps[:-1], True]
    cost = np.where(last_of_tie, cost, np.inf)
    return float(ps[int(np.argmin(cost))])


def precision_threshold(y: np.ndarray, p: np.ndarray, min_precision: float) -> float:
    """Lowest threshold whose alerts are at least ``min_precision`` precise."""
    order = np.argsort(-p, kind="stable")
    ys, ps = y[order], p[order]
    prec = np.cumsum(ys) / np.arange(1, len(ys) + 1)
    last_of_tie = np.r_[ps[1:] != ps[:-1], True]
    ok = np.where((prec >= min_precision) & last_of_tie)[0]
    return float(ps[ok.max()]) if len(ok) else float(ps[0])


# ---------------------------------------------------------------- statistics
def bootstrap_ci(y: np.ndarray, p: np.ndarray, fn=average_precision_score, n: int = 1000,
                 seed: int = config.SEED, alpha: float = 0.05) -> tuple[float, float, float]:
    rng = np.random.default_rng(seed)
    m = len(y)
    stats = np.empty(n)
    for i in range(n):
        idx = rng.integers(0, m, m)
        stats[i] = fn(y[idx], p[idx])
    lo, hi = np.quantile(stats, [alpha / 2, 1 - alpha / 2])
    return float(fn(y, p)), float(lo), float(hi)


def paired_bootstrap(y: np.ndarray, p_a: np.ndarray, p_b: np.ndarray, fn=average_precision_score,
                     n: int = 1000, seed: int = config.SEED) -> dict:
    """Is model A better than model B on the same test transactions?

    Returns the observed difference, its 95% CI and the one-sided bootstrap
    p-value for "A is not better than B".
    """
    rng = np.random.default_rng(seed)
    m = len(y)
    diffs = np.empty(n)
    for i in range(n):
        idx = rng.integers(0, m, m)
        diffs[i] = fn(y[idx], p_a[idx]) - fn(y[idx], p_b[idx])
    lo, hi = np.quantile(diffs, [0.025, 0.975])
    return {
        "diff": float(fn(y, p_a) - fn(y, p_b)), "ci_low": float(lo), "ci_high": float(hi),
        "p_value": float((np.sum(diffs <= 0) + 1) / (n + 1)),
    }
