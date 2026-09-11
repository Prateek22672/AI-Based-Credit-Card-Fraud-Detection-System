"""A legacy rule engine, the "existing system" baseline.

Many banks started with hand-written if-then rules. These are typical ones:
high value, night-time online purchase, bursts of transactions and spending
far above the card's normal. Rules give a yes/no flag, so the score is the
number of rules fired, which still allows a PR curve to be drawn.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

RULES = {
    "R1 high value (> $500)": lambda f: f["amt"] > 500,
    "R2 night-time online purchase > $100": lambda f: (f["is_night"] == 1) & (f["is_online"] == 1) & (f["amt"] > 100),
    "R3 velocity: 3+ transactions in 1 hour": lambda f: f["cnt_1h"] >= 3,
    "R4 amount > 5x card average": lambda f: f["amt_to_card_mean"] > 5,
}


def rule_scores(features: pd.DataFrame) -> np.ndarray:
    fired = np.column_stack([rule(features).to_numpy() for rule in RULES.values()])
    return fired.sum(axis=1).astype(float) / len(RULES)
