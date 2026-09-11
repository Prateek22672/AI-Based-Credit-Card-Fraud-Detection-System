"""Dataset loading and leakage-safe, time-based splitting."""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config

# Columns needed from the Sparkov file. Names, street, zip, job and trans_num
# are dropped at load time: they are personal data and are not needed.
SPARKOV_COLUMNS = [
    "trans_date_trans_time", "cc_num", "merchant", "category", "amt", "gender",
    "city", "state", "lat", "long", "city_pop", "dob", "unix_time",
    "merch_lat", "merch_long", "is_fraud",
]


def load_sparkov() -> pd.DataFrame:
    """Load the Sparkov simulated card transactions, sorted by time.

    The mirror's ``unix_time`` field is offset from the textual timestamp
    (it was generated for a different year), so the textual timestamp is
    the single source of truth for time.
    """
    df = pd.read_parquet(config.SPARKOV_PARQUET, columns=SPARKOV_COLUMNS)
    df["ts"] = pd.to_datetime(df["trans_date_trans_time"])
    df["unix"] = (df["ts"] - pd.Timestamp("1970-01-01")) // pd.Timedelta(seconds=1)
    df["dob"] = pd.to_datetime(df["dob"])
    df["merchant"] = df["merchant"].str.replace("fraud_", "", regex=False)
    df["cc_num"] = df["cc_num"].astype("int64").astype(str)
    df = df.drop(columns=["trans_date_trans_time", "unix_time"])
    df = df.sort_values(["unix", "cc_num"], kind="stable").reset_index(drop=True)
    return df


def sparkov_split(df: pd.DataFrame) -> dict[str, np.ndarray]:
    """Boolean masks for train / validation / test with 7-day label-delay gaps."""
    ts = df["ts"]
    return {
        "train": (ts <= pd.Timestamp(config.TRAIN_END)).to_numpy(),
        "val": ((ts >= pd.Timestamp(config.VAL_START)) & (ts <= pd.Timestamp(config.VAL_END))).to_numpy(),
        "test": (ts >= pd.Timestamp(config.TEST_START)).to_numpy(),
    }


def load_ulb() -> pd.DataFrame:
    """ULB / Worldline European card data (Dal Pozzolo et al., 2015)."""
    df = pd.read_csv(config.ULB_CSV)
    return df.sort_values("Time", kind="stable").reset_index(drop=True)


def ulb_features(df: pd.DataFrame) -> tuple[pd.DataFrame, np.ndarray]:
    X = df.drop(columns=["Class"]).copy()
    X["hour"] = (X["Time"] % 86400) // 3600
    X["log_amount"] = np.log1p(X["Amount"])
    X = X.drop(columns=["Time"])
    return X, df["Class"].to_numpy()


def ulb_split(n: int) -> dict[str, np.ndarray]:
    """Chronological 60/20/20 split for the two-day ULB data."""
    a, b, _ = config.ULB_SPLIT
    i1, i2 = int(n * a), int(n * (a + b))
    idx = np.arange(n)
    return {"train": idx < i1, "val": (idx >= i1) & (idx < i2), "test": idx >= i2}
