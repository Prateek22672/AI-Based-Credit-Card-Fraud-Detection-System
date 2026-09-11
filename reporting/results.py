"""Read experiment outputs and format numbers for the reports."""
from __future__ import annotations

import json
from pathlib import Path

from fraudlens import config

NAMES = ["benchmark_sparkov", "benchmark_ulb", "imbalance_sparkov", "protocol", "ablation", "unseen",
         "analysis", "explain", "dataset_sparkov", "policy", "latency", "scenarios", "calibration"]


class Results:
    def __init__(self):
        self.r = {}
        for n in NAMES:
            p = config.RESULTS / f"{n}.json"
            self.r[n] = json.loads(p.read_text()) if p.exists() else {}
        mc = config.ARTIFACTS / "model_card.json"
        self.card = json.loads(mc.read_text()) if mc.exists() else {}
        lit = config.ROOT / "docs" / "sources" / "literature.json"
        self.lit = json.loads(lit.read_text(encoding="utf-8"))

    def get(self, name, *path, default=None):
        cur = self.r.get(name, {})
        for k in path:
            if isinstance(cur, dict) and k in cur:
                cur = cur[k]
            else:
                return default
        return cur

    # formatting helpers ------------------------------------------------------
    @staticmethod
    def f(x, nd=3):
        return "n/a" if x is None else f"{x:.{nd}f}"

    @staticmethod
    def pct(x, nd=1):
        return "n/a" if x is None else f"{x * 100:.{nd}f}%"

    @staticmethod
    def money(x, nd=0):
        return "n/a" if x is None else f"${x:,.{nd}f}"

    @staticmethod
    def n(x):
        return "n/a" if x is None else f"{int(x):,}"

    def bm(self, model, metric, split="test"):
        return self.get("benchmark_sparkov", model, split, metric)

    def figure(self, name) -> Path:
        return config.FIGURES / f"{name}.png"
