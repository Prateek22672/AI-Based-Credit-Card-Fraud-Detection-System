"""Explanations must be faithful: SHAP contributions add up to the model's own output."""
import numpy as np
import pytest

from fraudlens import config

pytestmark = pytest.mark.skipif(not (config.ARTIFACTS / "engine.joblib").exists(), reason="run the pipeline first")


@pytest.fixture(scope="module")
def engine_and_X():
    """The deployed engine and live features of the first 400 test-stream transactions."""
    import pickle

    import joblib
    import pandas as pd

    from fraudlens.features import ALL_FEATURES, Txn

    engine = joblib.load(config.ARTIFACTS / "engine.joblib")
    fs = pickle.loads((config.ARTIFACTS / "feature_store.pkl").read_bytes())
    stream = pd.read_parquet(config.ARTIFACTS / "stream.parquet").head(400)
    X = np.vstack([fs.process(Txn(r.cc_num, int(r.unix), float(r.amt), r.category, r.merchant,
                                  float(r.merch_lat), float(r.merch_long))) for r in stream.itertuples()])
    return engine, X[:, [ALL_FEATURES.index(f) for f in engine.feature_names]]


def test_deployed_model_excludes_protected_attributes(engine_and_X):
    engine = engine_and_X[0]
    assert "age" not in engine.feature_names and "gender_m" not in engine.feature_names


def test_shap_local_accuracy(engine_and_X):
    from fraudlens.explain import shap_values

    engine, X = engine_and_X
    sv, base = shap_values(engine.xgb, X)
    margin = engine.xgb.predict(X, output_margin=True)
    np.testing.assert_allclose(sv.sum(axis=1) + base, margin, rtol=1e-4, atol=1e-3)


def test_risk_score_is_monotone_and_bands_sit_on_thresholds(engine_and_X):
    engine = engine_and_X[0]
    s = engine.risk_score(np.linspace(0, 1, 2001))
    assert np.all(np.diff(s) >= 0) and s[0] == 0 and s[-1] == 100
    assert float(engine.risk_score(engine.t_alert)) == pytest.approx(config.RISK_BAND_MEDIUM)
    if engine.t_block > engine.t_alert:
        assert float(engine.risk_score(engine.t_block)) == pytest.approx(config.RISK_BAND_HIGH)
    assert engine.decide(engine.t_block)[1] == "BLOCK" and engine.decide(0.0)[1] == "APPROVE"
