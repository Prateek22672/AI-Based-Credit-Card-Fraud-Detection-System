"""Explainable AI: SHAP contributions turned into human-readable reason codes.

SHAP values come from XGBoost's built-in TreeSHAP (``pred_contribs=True``),
the exact algorithm of Lundberg et al. (2020), so the live API needs no
heavy extra dependency and explains a transaction in about a millisecond.
Each value is the feature's push on the fraud log-odds: positive means
"more suspicious", negative means "looks genuine".

Related features are grouped (for example all velocity counters), and each
group gets a sentence built from the actual values of this transaction, so
an analyst reads "5 transactions in the last hour" instead of "cnt_1h=5".
"""
from __future__ import annotations

import math

import numpy as np
import xgboost as xgb

from .features import CATEGORIES

CATEGORY_LABELS = {
    "entertainment": "Entertainment", "food_dining": "Food & dining", "gas_transport": "Fuel & transport",
    "grocery_net": "Online grocery", "grocery_pos": "Grocery (in-store)", "health_fitness": "Health & fitness",
    "home": "Home", "kids_pets": "Kids & pets", "misc_net": "Online miscellaneous",
    "misc_pos": "Miscellaneous (in-store)", "personal_care": "Personal care",
    "shopping_net": "Online shopping", "shopping_pos": "Shopping (in-store)", "travel": "Travel",
}

FEATURE_LABELS = {
    "amt": "Amount", "log_amt": "Amount (log)", "hour": "Hour of day", "is_night": "Night-time (22:00-04:00)",
    "day_of_week": "Day of week", "is_weekend": "Weekend", "is_online": "Online / card-not-present",
    "age": "Customer age", "gender_m": "Gender", "log_city_pop": "Home city population",
    "dist_home_km": "Distance from home (km)", "card_history_len": "Card history length",
    "log_secs_since_last": "Time since previous transaction", "cnt_1h": "Transactions in last 1 h",
    "cnt_24h": "Transactions in last 24 h", "cnt_7d": "Transactions in last 7 days",
    "sum_24h": "Amount spent in last 24 h", "cnt_24h_vs_usual": "24 h activity vs usual",
    "amt_to_card_mean": "Amount / card average", "amt_zscore": "Amount z-score vs card",
    "amt_to_cat_mean": "Amount / card's category average", "cat_share": "Card's share of this category",
    "is_new_category": "First use in this category", "is_new_merchant": "First use at this merchant",
    "night_share": "Card's usual night activity", "dist_prev_km": "Distance from previous transaction (km)",
    "speed_kmh": "Travel speed since previous transaction",
} | {f"cat_{c}": f"Category: {CATEGORY_LABELS[c]}" for c in CATEGORIES}

GROUPS = {
    "amount": ["amt", "log_amt"],
    "spend_vs_history": ["amt_to_card_mean", "amt_zscore", "amt_to_cat_mean"],
    "category": [f"cat_{c}" for c in CATEGORIES] + ["is_online"],
    "time_of_day": ["hour", "is_night", "day_of_week", "is_weekend"],
    "burst_1h": ["cnt_1h"],
    "burst_24h": ["cnt_24h", "sum_24h", "cnt_24h_vs_usual"],
    "week_activity": ["cnt_7d"],
    "gap": ["log_secs_since_last"],
    "novelty": ["is_new_category", "cat_share", "is_new_merchant"],
    "geography": ["dist_home_km", "dist_prev_km", "speed_kmh"],
    "profile": ["log_city_pop", "card_history_len", "night_share", "age", "gender_m"],
}
GROUP_LABELS = {
    "amount": "Transaction amount", "spend_vs_history": "Spend vs card's history",
    "category": "Merchant category / channel", "time_of_day": "Time of day",
    "burst_1h": "Burst of activity (1 h)", "burst_24h": "Activity in last 24 h",
    "week_activity": "Activity in last 7 days", "gap": "Timing vs previous transaction",
    "novelty": "New behaviour for this card", "geography": "Location", "profile": "Card profile",
}
MIN_REASON_SHAP = 0.15  # log-odds; smaller pushes are not worth showing as a reason


def shap_values(booster_model: xgb.XGBClassifier, X: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """TreeSHAP contributions (n, d) and base values (n,).

    Uses exactly the trees the model predicts with: after early stopping that is
    up to ``best_iteration``, not every tree that was grown.
    """
    best = getattr(booster_model, "best_iteration", None)
    kw = {"iteration_range": (0, best + 1)} if best is not None else {}
    contrib = booster_model.get_booster().predict(xgb.DMatrix(np.atleast_2d(X)), pred_contribs=True, **kw)
    return contrib[:, :-1], contrib[:, -1]


def _fmt_duration(secs: float) -> str:
    if secs < 90:
        return f"{secs:.0f} seconds"
    if secs < 5400:
        return f"{secs / 60:.0f} minutes"
    if secs < 2 * 86400:
        return f"{secs / 3600:.1f} hours"
    return f"{secs / 86400:.0f} days"


def _risk_text(group: str, f: dict, card: dict, category: str) -> str:
    cat = CATEGORY_LABELS.get(category, category)
    mean = card.get("mean_amt") or (f["amt"] / max(f["amt_to_card_mean"], 1e-6) - 1)
    if group == "amount":
        ratio = f["amt"] / max(mean, 1.0)
        if ratio >= 2:
            return f"Amount ${f['amt']:,.2f} is {ratio:.1f}x this card's average spend (${mean:,.0f})"
        return f"Large transaction amount (${f['amt']:,.2f})"
    if group == "spend_vs_history":
        if f["amt_to_cat_mean"] >= 2 and not f["is_new_category"]:
            return f"{f['amt_to_cat_mean']:.1f}x what this card usually spends on {cat}"
        if f["amt_zscore"] >= 2:
            return f"Spend is {f['amt_zscore']:.1f} standard deviations above this card's normal"
        return "Spending pattern differs from this card's history"
    if group == "category":
        if f["is_online"]:
            return f"Online (card-not-present) purchase in {cat}, where stolen card details are typically used"
        return f"{cat} has a higher fraud rate in historical data"
    if group == "time_of_day":
        hh = int(f["hour"])
        if f["is_night"]:
            usual = f["night_share"]
            extra = f"; only {usual:.0%} of this card's past transactions were at night" if usual < 0.3 else ""
            return f"Made late at night ({hh:02d}:00-{(hh + 1) % 24:02d}:00){extra}"
        return f"Unusual time of day for this card ({hh:02d}:00)"
    if group == "burst_1h":
        n = int(f["cnt_1h"])
        return f"{n} other transaction{'s' if n != 1 else ''} on this card in the past hour" if n else \
            "Rapid-fire timing pattern"
    if group == "burst_24h":
        return (f"{int(f['cnt_24h'])} transactions (${f['sum_24h']:,.0f}) in the past 24 h, "
                f"{f['cnt_24h_vs_usual']:.1f}x this card's usual daily activity")
    if group == "week_activity":
        return f"{int(f['cnt_7d'])} transactions on this card in the past 7 days"
    if group == "gap":
        secs = math.expm1(f["log_secs_since_last"])
        if secs < 3600:
            return f"Only {_fmt_duration(secs)} since the previous transaction"
        if secs > 7 * 86400:
            return f"Card was dormant for {_fmt_duration(secs)} before this transaction"
        return f"{_fmt_duration(secs)} since the previous transaction"
    if group == "novelty":
        if f["is_new_category"]:
            return f"First time this card has been used for {cat}"
        if f["is_new_merchant"]:
            return "First purchase at this merchant"
        return f"Rarely used category for this card ({f['cat_share']:.0%} of past transactions)"
    if group == "geography":
        if f["speed_kmh"] > 500:
            return f"Implausible travel: {f['dist_prev_km']:,.0f} km from the previous transaction location"
        return f"Merchant is {f['dist_home_km']:,.0f} km from the cardholder's home"
    if group == "profile":
        n = int(round(math.expm1(f["card_history_len"])))
        if n < 20:
            return f"New card with little history ({n} past transactions)"
        return "Card/customer profile resembles past fraud victims"
    return GROUP_LABELS[group]


def _safe_text(group: str, f: dict, card: dict, category: str) -> str:
    cat = CATEGORY_LABELS.get(category, category)
    return {
        "amount": f"Amount ${f['amt']:,.2f} is normal for this card",
        "spend_vs_history": "Spend is consistent with this card's history",
        "category": f"{cat} is a low-risk category",
        "time_of_day": f"Normal time of day ({int(f['hour']):02d}:00)",
        "burst_1h": "No burst of activity in the past hour",
        "burst_24h": "Normal activity level in the past 24 h",
        "week_activity": "Normal activity level this week",
        "gap": "Normal gap since the previous transaction",
        "novelty": f"Card regularly uses {cat}",
        "geography": "Merchant is close to the cardholder's usual area",
        "profile": "Established card with a long history",
    }[group]


def explain_row(model: xgb.XGBClassifier, feature_names: list[str], x: np.ndarray, category: str,
                card: dict | None = None, top_features: int = 10,
                contrib: tuple[np.ndarray, float] | None = None) -> dict:
    """Explanation for one transaction. Pass ``contrib`` (its SHAP row and base value,
    e.g. from one batched ``shap_values`` call) to avoid recomputing SHAP per row."""
    card = card or {}
    if contrib is None:
        sv_all, base_all = shap_values(model, x)
        sv, base = sv_all[0], float(base_all[0])
    else:
        sv, base = contrib[0], float(contrib[1])
    f = dict(zip(feature_names, map(float, x)))
    for k in ("age", "gender_m"):
        f.setdefault(k, 0.0)
    order = np.argsort(-np.abs(sv))[:top_features]
    feats = [{"feature": feature_names[i], "label": FEATURE_LABELS.get(feature_names[i], feature_names[i]),
              "value": float(x[i]), "shap": float(sv[i])} for i in order]
    idx = {n: i for i, n in enumerate(feature_names)}
    groups = []
    for g, members in GROUPS.items():
        s = float(sum(sv[idx[m]] for m in members if m in idx))
        groups.append({"group": g, "label": GROUP_LABELS[g], "shap": s})
    groups.sort(key=lambda d: -d["shap"])
    reasons = [_risk_text(g["group"], f, card, category) for g in groups if g["shap"] >= MIN_REASON_SHAP][:4]
    safe = [_safe_text(g["group"], f, card, category) for g in reversed(groups) if g["shap"] <= -MIN_REASON_SHAP][:3]
    return {"base_value": base, "features": feats, "groups": groups, "reasons": reasons, "mitigating": safe}
