"""The safety layer can only raise a decision, and its rules fire on the patterns they document."""
import numpy as np

from fraudlens import policy
from fraudlens.features import ALL_FEATURES


def feats(**over):
    base = {f: 0.0 for f in ALL_FEATURES}
    base.update(amt=40.0, amt_to_card_mean=1.0, dist_prev_km=3.0, speed_kmh=10.0)
    base.update(over)
    return base


def test_no_hit_on_ordinary_transaction():
    assert policy.evaluate(feats(), 0.5) == []
    assert policy.combine("LOW", []) == ("LOW", "APPROVE")


def test_rules_fire_on_their_patterns():
    ids = lambda f, a=0.0: {h["id"] for h in policy.evaluate(f, a)}
    assert ids(feats(cnt_1h=4, amt=900.0, amt_to_card_mean=15.0)) == {"P1"}
    assert ids(feats(dist_prev_km=1100.0, speed_kmh=2000.0)) == {"P2"}
    assert ids(feats(cnt_1h=3, amt=1.5, is_online=1)) == {"P3"}
    assert ids(feats(), 0.9999) == {"N1"}


def test_combine_only_raises():
    hits = policy.evaluate(feats(cnt_1h=3, amt=2.0, is_online=1), 0.0)
    assert policy.combine("LOW", hits) == ("MEDIUM", "STEP_UP")
    assert policy.combine("HIGH", hits) == ("HIGH", "BLOCK")      # never lowered
    assert policy.combine("MEDIUM", []) == ("MEDIUM", "STEP_UP")


def test_matrix_matches_scalar_rules():
    rows = [feats(cnt_1h=4, amt=900.0, amt_to_card_mean=15.0), feats(dist_prev_km=1100.0, speed_kmh=2000.0),
            feats(cnt_1h=3, amt=1.5, is_online=1), feats()]
    X = np.array([[r[f] for f in ALL_FEATURES] for r in rows])
    masks = policy.evaluate_matrix(X, ALL_FEATURES, np.array([0.0, 0.0, 0.0, 0.9999]))
    for i, r in enumerate(rows):
        scalar = {h["id"] for h in policy.evaluate(r, [0.0, 0.0, 0.0, 0.9999][i])}
        assert {k for k, m in masks.items() if m[i]} == scalar
