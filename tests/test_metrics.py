import numpy as np
import pytest

from fraudlens.metrics import (best_f1_threshold, cost_optimal_threshold, precision_threshold,
                               threshold_metrics)

y = np.array([0, 0, 0, 0, 1, 0, 1, 1])
p = np.array([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.8, 0.9])


def test_threshold_metrics_counts():
    m = threshold_metrics(y, p, 0.5)
    assert (m["tp"], m["fp"], m["fn"], m["tn"]) == (3, 1, 0, 4)
    assert m["precision"] == pytest.approx(0.75) and m["recall"] == 1.0


def test_precision_threshold_reaches_target():
    t = precision_threshold(y, p, 1.0)
    assert t == pytest.approx(0.8)
    assert threshold_metrics(y, p, t)["precision"] == 1.0


def test_best_f1_threshold():
    assert best_f1_threshold(y, p) == pytest.approx(0.5)


def test_cost_threshold_trades_alerts_for_money():
    amt = np.array([10, 10, 10, 10, 1000, 10, 50, 50], dtype=float)
    # cheap alerts: catch everything worth catching (include the $1000 fraud at 0.5)
    assert cost_optimal_threshold(y, p, amt, alert_cost=1.0) == pytest.approx(0.5)
    # expensive alerts: only the top-scored fraud pays for itself
    assert cost_optimal_threshold(y, p, amt, alert_cost=45.0) >= 0.5


def test_accuracy_paradox():
    yy = np.r_[np.zeros(995), np.ones(5)]
    m = threshold_metrics(yy, np.zeros(1000), 0.5)
    assert m["accuracy"] == pytest.approx(0.995) and m["recall"] == 0.0
