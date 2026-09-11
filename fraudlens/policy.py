"""Defence in depth: documented policy rules and a novelty alarm on top of the ML risk engine.

Why this layer exists (measured, not assumed):

* The stacking meta-learner is fitted on *labelled* validation fraud. XGBoost
  already explains that fraud, so the meta-learner gives the Isolation Forest
  almost no weight. In other words, stacking alone cannot use the anomaly
  detector for what it is meant for: fraud types that never appeared in the labels.
* Some attacks (card testing, cloned-card impossible travel) do not occur in the
  training data at all, so no supervised model can learn them.
* The RBI Master Direction on Digital Payment Security Controls (2021, paras
  36-37) requires documented, parameterised alerts on velocity and geo-location,
  and allows risk-based step-up authentication (para 34).

Each rule can only *raise* a decision to at least STEP_UP (verification); it
never approves something the model flagged. The cost of every rule (how often
it fires on genuine transactions) is measured on the test period by
``python -m fraudlens.pipeline policy``.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np

NOVELTY_PERCENTILE = 0.9995   # more unusual than 99.95% of genuine training transactions
LEVELS = ("LOW", "MEDIUM", "HIGH")
DECISIONS = {"LOW": "APPROVE", "MEDIUM": "STEP_UP", "HIGH": "BLOCK"}


@dataclass(frozen=True)
class Rule:
    id: str
    title: str
    condition: Callable[[dict, float], bool]
    reason: Callable[[dict, float], str]
    level: str = "MEDIUM"


RULES = [
    Rule("P1", "Burst then jump (account takeover / card testing cash-out)",
         lambda f, a: f["cnt_1h"] >= 3 and f["amt_to_card_mean"] >= 5,
         lambda f, a: (f"Policy P1: {int(f['cnt_1h'])} transactions in the past hour, then a jump to "
                       f"{f['amt_to_card_mean']:.0f}x the card's average amount")),
    Rule("P2", "Impossible travel (cloned card)",
         lambda f, a: f["dist_prev_km"] >= 500 and f["speed_kmh"] >= 800,
         lambda f, a: (f"Policy P2: {f['dist_prev_km']:,.0f} km from the previous transaction; the implied "
                       "speed is faster than a commercial flight")),
    Rule("P3", "Micro-charge burst (card testing)",
         lambda f, a: f["cnt_1h"] >= 3 and f["amt"] < 5 and f["is_online"] == 1,
         lambda f, a: (f"Policy P3: tiny online charge (${f['amt']:.2f}) after {int(f['cnt_1h'])} others in the "
                       "past hour, the classic card-testing pattern")),
    Rule("N1", "Novelty alarm (Isolation Forest)",
         lambda f, a: a >= NOVELTY_PERCENTILE,
         lambda f, a: (f"Novelty alarm: behaviour more unusual than {min(a, 0.9999):.2%} of normal "
                       "transactions; possible new fraud pattern")),
]
RULE_INFO = [{"id": r.id, "title": r.title, "level": r.level} for r in RULES]


def evaluate(features: dict, anomaly_pct: float) -> list[dict]:
    """Rules that fire for one transaction (feature values by name)."""
    return [{"id": r.id, "title": r.title, "level": r.level, "reason": r.reason(features, anomaly_pct)}
            for r in RULES if r.condition(features, anomaly_pct)]


def combine(ml_level: str, hits: list[dict]) -> tuple[str, str]:
    level = max([ml_level] + [h["level"] for h in hits], key=LEVELS.index)
    return level, DECISIONS[level]


def evaluate_matrix(X: np.ndarray, feature_names: list[str], anomaly_pct: np.ndarray) -> dict[str, np.ndarray]:
    """Vectorised version for offline evaluation: rule id -> boolean mask."""
    col = {n: X[:, i] for i, n in enumerate(feature_names)}
    return {
        "P1": (col["cnt_1h"] >= 3) & (col["amt_to_card_mean"] >= 5),
        "P2": (col["dist_prev_km"] >= 500) & (col["speed_kmh"] >= 800),
        "P3": (col["cnt_1h"] >= 3) & (col["amt"] < 5) & (col["is_online"] == 1),
        "N1": anomaly_pct >= NOVELTY_PERCENTILE,
    }
