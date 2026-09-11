"""Causal behavioural feature engineering shared by training and the live API.

The same ``FeatureStore`` code produces the training matrix (by replaying the
historical transactions in time order) and the features of a live transaction
in the API. There is only one implementation, so training/serving skew is
impossible by construction, and every feature only uses information that is
available at authorisation time (the card's *past* transactions).

Feature ideas follow transaction-aggregation research: Whitrow et al. (2009),
Bahnsen et al. (2016) and the ULB reproducible-ML handbook (Le Borgne et al.,
2022): velocity counts over time windows, spend relative to the card's own
history, novelty of category/merchant, and geography.
"""
from __future__ import annotations

import copy
import math
import time
from collections import deque
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

HOUR = 3600
DAY = 86400
WEEK = 7 * DAY

CATEGORIES = [
    "entertainment", "food_dining", "gas_transport", "grocery_net", "grocery_pos",
    "health_fitness", "home", "kids_pets", "misc_net", "misc_pos", "personal_care",
    "shopping_net", "shopping_pos", "travel",
]
ONLINE_CATEGORIES = {"grocery_net", "misc_net", "shopping_net"}
CAT_INDEX = {c: i for i, c in enumerate(CATEGORIES)}

# Numeric behavioural + transaction features, in matrix column order.
NUMERIC_FEATURES = [
    "amt", "log_amt", "hour", "is_night", "day_of_week", "is_weekend", "is_online",
    "age", "gender_m", "log_city_pop", "dist_home_km",
    "card_history_len", "log_secs_since_last", "cnt_1h", "cnt_24h", "cnt_7d",
    "sum_24h", "cnt_24h_vs_usual", "amt_to_card_mean", "amt_zscore", "amt_to_cat_mean",
    "cat_share", "is_new_category", "is_new_merchant", "night_share", "dist_prev_km",
    "speed_kmh",
]
CATEGORY_FEATURES = [f"cat_{c}" for c in CATEGORIES]
ALL_FEATURES = NUMERIC_FEATURES + CATEGORY_FEATURES

# Protected / demographic attributes. They are excluded from the deployed model
# (fraud decisions should not depend on gender or age) and the ablation study
# measures what that costs in accuracy.
PROTECTED_FEATURES = ["age", "gender_m"]
DEPLOYED_FEATURES = [f for f in ALL_FEATURES if f not in PROTECTED_FEATURES]

# "Raw" features = what most basic projects feed a classifier: the columns of
# the transaction itself, with no knowledge of the card's history.
RAW_FEATURES = [
    "amt", "log_amt", "hour", "is_night", "day_of_week", "is_weekend", "is_online",
    "log_city_pop", "dist_home_km",
] + CATEGORY_FEATURES

NO_HISTORY_SECS = 30 * DAY  # value used for "time since last" on a card's first transaction


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = p2 - p1
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * 6371.0 * math.asin(min(1.0, math.sqrt(a)))


@dataclass
class CardProfile:
    """Static customer data a bank already holds for each card."""
    cc_num: str
    lat: float
    long: float
    city_pop: float
    dob_unix: int
    gender_m: int
    city: str = ""
    state: str = ""


@dataclass
class CardState:
    """Rolling history of one card. Only past transactions are stored."""
    recent: deque = field(default_factory=deque)   # (ts, amt, is_online) within the last 7 days
    n: int = 0
    mean: float = 0.0
    m2: float = 0.0                                  # Welford running variance accumulator
    first_ts: int | None = None
    last_ts: int | None = None
    last_lat: float | None = None
    last_lon: float | None = None
    night_n: int = 0
    cat_n: dict = field(default_factory=dict)
    cat_sum: dict = field(default_factory=dict)
    merchants: set = field(default_factory=set)


@dataclass
class Txn:
    cc_num: str
    unix: int
    amt: float
    category: str
    merchant: str
    merch_lat: float
    merch_long: float


def _is_night(hour: int) -> int:
    return int(hour >= 22 or hour < 4)


class FeatureStore:
    """Per-card state + feature computation.

    ``features(txn)`` is a pure read (safe for what-if scoring);
    ``update(txn)`` commits the transaction into the card's history.
    """

    def __init__(self, profiles: dict[str, CardProfile]):
        self.profiles = profiles
        self.states: dict[str, CardState] = {}

    # ------------------------------------------------------------------ core
    def features(self, t: Txn) -> np.ndarray:
        prof = self.profiles[t.cc_num]
        st = self.states.get(t.cc_num) or CardState()
        ts = t.unix
        tm = time.gmtime(ts)
        hour, dow = tm.tm_hour, tm.tm_wday

        cnt_1h = cnt_24h = cnt_7d = 0
        sum_24h = 0.0
        for rts, ramt, _ in st.recent:
            age = ts - rts
            if age < 0 or age > WEEK:
                continue
            cnt_7d += 1
            if age <= DAY:
                cnt_24h += 1
                sum_24h += ramt
                if age <= HOUR:
                    cnt_1h += 1

        n = st.n
        if n > 0:
            mean = st.mean
            std = math.sqrt(st.m2 / (n - 1)) if n > 1 else 0.0
            secs_since = max(0, ts - st.last_ts)
            active_days = max(1.0, (ts - st.first_ts) / DAY)
            usual_daily = n / active_days
            cat_n = st.cat_n.get(t.category, 0)
            cat_mean = st.cat_sum[t.category] / cat_n if cat_n else mean
            amt_to_mean = t.amt / (mean + 1.0)
            zscore = (t.amt - mean) / (std + 1.0)
            cat_share = cat_n / n
            new_cat = int(cat_n == 0)
            new_merchant = int(t.merchant not in st.merchants)
            night_share = st.night_n / n
            dist_prev = haversine_km(st.last_lat, st.last_lon, t.merch_lat, t.merch_long)
            hours = max(secs_since / HOUR, 1 / 60)  # at least one minute
            speed = min(dist_prev / hours, 2000.0)
        else:
            secs_since = NO_HISTORY_SECS
            usual_daily = 1.0
            cat_mean = t.amt
            amt_to_mean, zscore, cat_share = 1.0, 0.0, 0.0
            new_cat, new_merchant, night_share = 1, 1, 0.0
            dist_prev, speed = 0.0, 0.0

        age_years = (ts - prof.dob_unix) / (365.25 * DAY)
        row = [
            t.amt, math.log1p(t.amt), hour, _is_night(hour), dow, int(dow >= 5),
            int(t.category in ONLINE_CATEGORIES),
            age_years, prof.gender_m, math.log1p(prof.city_pop),
            haversine_km(prof.lat, prof.long, t.merch_lat, t.merch_long),
            math.log1p(n), math.log1p(secs_since), cnt_1h, cnt_24h, cnt_7d,
            sum_24h, cnt_24h / max(usual_daily, 0.1), amt_to_mean, zscore,
            t.amt / (cat_mean + 1.0), cat_share, new_cat, new_merchant, night_share,
            dist_prev, speed,
        ]
        onehot = [0.0] * len(CATEGORIES)
        if t.category in CAT_INDEX:
            onehot[CAT_INDEX[t.category]] = 1.0
        return np.asarray(row + onehot, dtype=np.float64)

    def update(self, t: Txn) -> None:
        st = self.states.get(t.cc_num)
        if st is None:
            st = self.states[t.cc_num] = CardState()
        ts = t.unix
        while st.recent and ts - st.recent[0][0] > WEEK:
            st.recent.popleft()
        st.recent.append((ts, t.amt, t.category in ONLINE_CATEGORIES))
        st.n += 1
        delta = t.amt - st.mean
        st.mean += delta / st.n
        st.m2 += delta * (t.amt - st.mean)
        if st.first_ts is None:
            st.first_ts = ts
        st.last_ts = ts
        st.last_lat, st.last_lon = t.merch_lat, t.merch_long
        st.night_n += _is_night(time.gmtime(ts).tm_hour)
        st.cat_n[t.category] = st.cat_n.get(t.category, 0) + 1
        st.cat_sum[t.category] = st.cat_sum.get(t.category, 0.0) + t.amt
        st.merchants.add(t.merchant)

    def process(self, t: Txn) -> np.ndarray:
        """Features of ``t`` given the past, then commit ``t`` into history."""
        x = self.features(t)
        self.update(t)
        return x

    def sandbox(self, cc_nums: list[str] | None = None) -> "FeatureStore":
        """Independent copy for what-if scenarios that must not touch live state.

        Copying only the cards involved keeps this cheap enough to do per request.
        """
        fs = FeatureStore(self.profiles)
        keys = self.states.keys() if cc_nums is None else [c for c in cc_nums if c in self.states]
        fs.states = {k: copy.deepcopy(self.states[k]) for k in keys}
        return fs

    def card_summary(self, cc_num: str) -> dict:
        st = self.states.get(cc_num)
        if st is None or st.n == 0:
            return {"n_txns": 0}
        std = math.sqrt(st.m2 / (st.n - 1)) if st.n > 1 else 0.0
        top = sorted(st.cat_n.items(), key=lambda kv: -kv[1])[:3]
        days = max(1.0, (st.last_ts - st.first_ts) / DAY)
        return {
            "n_txns": st.n, "mean_amt": round(st.mean, 2), "std_amt": round(std, 2),
            "txns_per_day": round(st.n / days, 2), "night_share": round(st.night_n / st.n, 3),
            "top_categories": [c for c, _ in top], "last_ts": st.last_ts,
            "n_merchants": len(st.merchants),
        }


# ---------------------------------------------------------------- offline API
def build_profiles(df: pd.DataFrame) -> dict[str, CardProfile]:
    first = df.drop_duplicates("cc_num")
    dob_unix = (first["dob"] - pd.Timestamp("1970-01-01")) // pd.Timedelta(seconds=1)
    return {
        cc: CardProfile(cc, float(la), float(lo), float(pop), int(d), int(g == "M"), city, state)
        for cc, la, lo, pop, d, g, city, state in zip(
            first["cc_num"], first["lat"], first["long"], first["city_pop"], dob_unix,
            first["gender"], first["city"], first["state"],
        )
    }


def iter_txns(df: pd.DataFrame):
    for cc, u, a, c, m, la, lo in zip(
        df["cc_num"], df["unix"], df["amt"], df["category"], df["merchant"],
        df["merch_lat"], df["merch_long"],
    ):
        yield Txn(cc, int(u), float(a), c, m, float(la), float(lo))


def build_feature_matrix(df: pd.DataFrame, store: FeatureStore | None = None) -> tuple[pd.DataFrame, FeatureStore]:
    """Replay ``df`` (sorted by time) through a FeatureStore.

    Returns the feature matrix (one row per transaction, computed strictly
    from earlier transactions) and the store holding the final card state.
    """
    if store is None:
        store = FeatureStore(build_profiles(df))
    out = np.empty((len(df), len(ALL_FEATURES)), dtype=np.float64)
    for i, t in enumerate(iter_txns(df)):
        out[i] = store.process(t)
    return pd.DataFrame(out, columns=ALL_FEATURES, index=df.index), store
