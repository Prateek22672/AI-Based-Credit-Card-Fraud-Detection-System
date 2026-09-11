"""Central configuration: paths, split dates, cost assumptions and seeds.

Everything that an experiment result depends on lives here so the report can
quote exact settings and anyone can reproduce the numbers.
"""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_RAW = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"
ARTIFACTS = ROOT / "artifacts"          # trained models + feature-store snapshot used by the API
REPORTS = ROOT / "reports"
RESULTS = REPORTS / "results"           # JSON/CSV experiment outputs
FIGURES = REPORTS / "figures"           # PNG charts used by the dashboard and the documents

for _p in (DATA_RAW, DATA_PROCESSED, ARTIFACTS, RESULTS, FIGURES):
    _p.mkdir(parents=True, exist_ok=True)

SPARKOV_PARQUET = DATA_RAW / "sparkov_train.parquet"
ULB_CSV = DATA_RAW / "creditcard_ulb.csv"

SEED = 42
N_JOBS = max(1, (os.cpu_count() or 2))

# --- Time-based split (Sparkov covers 2019-01-01 .. 2020-06-21) -------------
# Train on the past, validate on the next quarter, test on the most recent
# quarter. A 7-day gap between blocks mimics the delay before fraud labels are
# confirmed in a real bank (Le Borgne et al., 2022), so the model is never
# evaluated on transactions from the week right after its training data.
TRAIN_END = "2019-12-31 23:59:59"
VAL_START = "2020-01-08"
VAL_END = "2020-03-31 23:59:59"
TEST_START = "2020-04-08"
GAP_DAYS = 7

# ULB/European dataset has no dates, only seconds over two days: split by
# time order into 60% / 20% / 20%.
ULB_SPLIT = (0.60, 0.20, 0.20)

# --- Business cost model (USD, Sparkov amounts are USD) ---------------------
# Missing a fraud costs the transaction amount (charge-back loss).
# Every alert costs a fixed amount: analyst review / OTP step-up and customer
# friction. Industry manual-review estimates range from a few dollars to tens
# of dollars; $5 is the base case and the report shows a sensitivity table.
ALERT_COST = 5.0
ALERT_COST_SENSITIVITY = (1.0, 2.0, 5.0, 10.0, 25.0)

# Auto-block tier: only block without human review when the model is this
# precise on validation data; everything between the alert threshold and the
# block threshold goes to step-up verification / analyst review.
BLOCK_MIN_PRECISION = 0.90

# Risk-score bands shown to users (0-100). The band edges are mapped onto the
# data-driven probability thresholds, keeping the team's original design of
# Low 0-30 / Medium 31-60 / High 61-100.
RISK_BAND_MEDIUM = 30.0
RISK_BAND_HIGH = 60.0

MODEL_VERSION = "fraudlens-hybrid-1.0"
