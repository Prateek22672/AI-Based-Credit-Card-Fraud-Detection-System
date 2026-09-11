"""Feature engineering must be causal (no future leakage) and identical online/offline."""
import numpy as np
import pandas as pd
import pytest

from fraudlens import config
from fraudlens.features import (ALL_FEATURES, CardProfile, FeatureStore, Txn, build_feature_matrix,
                                haversine_km)

T0 = 1_577_836_800  # 2020-01-01 00:00:00 UTC


def store():
    return FeatureStore({"c1": CardProfile("c1", 40.0, -75.0, 50_000, T0 - 40 * 365 * 86400, 1)})


def col(x, name):
    return x[ALL_FEATURES.index(name)]


def test_first_transaction_has_neutral_history():
    x = store().process(Txn("c1", T0, 50.0, "grocery_pos", "m1", 40.0, -75.0))
    assert col(x, "card_history_len") == 0
    assert col(x, "cnt_1h") == 0 and col(x, "is_new_category") == 1 and col(x, "amt_to_card_mean") == 1.0


def test_velocity_windows_count_only_the_past():
    fs = store()
    for k in range(4):                                 # 4 txns, 10 minutes apart
        fs.process(Txn("c1", T0 + 600 * k, 20.0, "misc_net", f"m{k}", 40.0, -75.0))
    x = fs.features(Txn("c1", T0 + 600 * 4, 900.0, "shopping_net", "m9", 40.0, -75.0))
    assert col(x, "cnt_1h") == 4
    assert col(x, "cnt_24h") == 4
    assert col(x, "sum_24h") == pytest.approx(80.0)
    assert col(x, "amt_to_card_mean") == pytest.approx(900 / 21)
    assert col(x, "is_new_category") == 1


def history(amounts):
    n = len(amounts)
    return pd.DataFrame({"cc_num": ["c1"] * n, "unix": [T0 + 3600 * k for k in range(n)], "amt": amounts,
                         "category": ["grocery_pos"] * n, "merchant": ["m1"] * n,
                         "merch_lat": [40.0] * n, "merch_long": [-75.0] * n})


def test_features_do_not_see_future_transactions():
    """Changing the last transaction must not change any earlier row's features."""
    a = history([30.0, 31.0, 32.0, 33.0, 34.0, 35.0])
    b = a.copy()
    b.loc[5, ["amt", "category"]] = [9999.0, "travel"]
    Xa, _ = build_feature_matrix(a, store())
    Xb, _ = build_feature_matrix(b, store())
    pd.testing.assert_frame_equal(Xa.iloc[:5], Xb.iloc[:5])
    assert not Xa.iloc[5].equals(Xb.iloc[5])


def test_features_is_a_pure_read_and_sandbox_is_isolated():
    fs = store()
    fs.process(Txn("c1", T0, 10.0, "home", "m1", 40.0, -75.0))
    t = Txn("c1", T0 + 60, 99.0, "home", "m1", 40.0, -75.0)
    assert np.array_equal(fs.features(t), fs.features(t))
    sb = fs.sandbox(["c1"])
    sb.update(t)
    assert fs.states["c1"].n == 1 and sb.states["c1"].n == 2


def test_haversine():
    assert haversine_km(0, 0, 0, 1) == pytest.approx(111.19, rel=1e-3)


@pytest.mark.skipif(not (config.ARTIFACTS / "stream.parquet").exists(), reason="run the pipeline first")
def test_online_features_match_training_features():
    """Training/serving parity: replaying the test stream through the API's
    feature-store snapshot reproduces the offline training matrix exactly."""
    import pickle

    from fraudlens.pipeline import FEATS_PATH, META_PATH

    fs = pickle.loads((config.ARTIFACTS / "feature_store.pkl").read_bytes())
    stream = pd.read_parquet(config.ARTIFACTS / "stream.parquet").head(3000)
    meta = pd.read_parquet(META_PATH)
    offline = pd.read_parquet(FEATS_PATH).loc[meta.index[meta["split"] == "test"][:3000]].to_numpy()
    online = np.vstack([fs.process(Txn(r.cc_num, int(r.unix), float(r.amt), r.category, r.merchant,
                                       float(r.merch_lat), float(r.merch_long))) for r in stream.itertuples()])
    np.testing.assert_allclose(online.astype(np.float32), offline, rtol=1e-6, atol=1e-5)
