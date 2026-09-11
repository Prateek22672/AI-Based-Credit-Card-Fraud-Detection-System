"""Write reports/RESULTS.md: the key result tables in Markdown (for GitHub)."""
from __future__ import annotations

from fraudlens import config

from .results import Results


def table(cols, rows):
    out = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def f(x, nd=3):
    return "n/a" if x is None else f"{x:.{nd}f}"


def build(R: Results) -> str:
    bm = R.get("benchmark_sparkov") or {}
    an = R.get("analysis") or {}
    ci = an.get("pr_auc_ci", {})
    parts = ["# FraudLens results\n", "Generated from `reports/results/*.json` by `python -m reporting.build`.\n"]
    rows = []
    for m in ("hybrid", "xgb", "lgbm", "rf", "mlp", "cnn", "dt", "lr", "iforest", "rules"):
        if m in bm:
            t = bm[m]["test"]
            c = ci.get(m)
            rows.append([("**" + bm[m]["label"] + "**") if m == "hybrid" else bm[m]["label"],
                         f(t["pr_auc"]) + (f" [{c['low']:.3f}, {c['high']:.3f}]" if c else ""), f(t["roc_auc"]),
                         f(t["precision"]), f(t["recall"]), f(t["f1"]), f(t["mcc"]),
                         f(bm[m].get("latency", {}).get("p50_ms"), 2) if bm[m].get("latency") else "-"])
    parts += ["## E1 Model benchmark (Sparkov, unseen test period Apr-Jun 2020)\n",
              table(["Model", "PR-AUC [95% CI]", "ROC-AUC", "Precision", "Recall", "F1", "MCC", "Latency p50 ms"], rows), ""]
    imb = R.get("imbalance_sparkov") or {}
    if imb:
        parts += ["## E2 Imbalance handling\n", table(
            ["Model", "Strategy", "PR-AUC", "F1 @0.5", "F1 tuned", "Brier"],
            [[v["model"], v["strategy"], f(v["pr_auc"]), f(v["at_0.5"]["f1"]), f(v["at_tuned"]["f1"]), f(v["brier"], 5)]
             for v in imb.values()]), ""]
    prot = R.get("protocol") or {}
    for ds in ("ulb", "sparkov"):
        if ds in prot:
            parts += [f"## E3 Evaluation protocol ({ds.upper()})\n", table(
                ["Protocol", "Accuracy", "Precision", "Recall", "F1"],
                [[prot[ds][k]["protocol"], f(prot[ds][k]["accuracy"], 4), f(prot[ds][k]["precision"]),
                  f(prot[ds][k]["recall"]), f(prot[ds][k]["f1"])] for k in ("dummy", "A", "B", "C", "D")]), ""]
    abl = R.get("ablation") or {}
    if abl.get("feature_sets"):
        parts += ["## E4 Ablation\n", table(["Feature set", "PR-AUC", "Recall", "Precision"],
                                           [[v["label"], f(v["test"]["pr_auc"]), f(v["test"]["recall"]), f(v["test"]["precision"])]
                                            for v in abl["feature_sets"].values()]), ""]
        if abl.get("components"):
            parts += [table(["Stacked combination", "PR-AUC", "Recall", "Precision"],
                            [[k, f(v["test"]["pr_auc"], 4), f(v["test"]["recall"]), f(v["test"]["precision"])]
                             for k, v in abl["components"].items()]), ""]
    un = R.get("unseen") or {}
    if un:
        parts += ["## E5 Unseen fraud type (recall on the held-out type)\n", table(
            ["Held-out type", "Frauds", "XGBoost", "RF", "Isolation Forest", "Hybrid", "Hybrid (saw it)"],
            [[h, v["held_out_frauds_in_test"]] + [f(v["results"][k]["recall"]) for k in
                                                  ("xgb", "rf", "iforest", "hybrid", "hybrid_trained_on_all_types")]
             for h, v in un.items()]), ""]
    ulb = R.get("benchmark_ulb") or {}
    if ulb:
        parts += ["## E6 ULB European dataset\n", table(
            ["Model", "PR-AUC", "Precision", "Recall", "F1"],
            [[ulb[m]["label"], f(ulb[m]["test"]["pr_auc"]), f(ulb[m]["test"]["precision"]), f(ulb[m]["test"]["recall"]),
              f(ulb[m]["test"]["f1"])] for m in ("hybrid", "xgb", "lgbm", "rf", "mlp", "lr", "iforest") if m in ulb]), ""]
    if an.get("cost_sensitivity"):
        parts += ["## E7 Business impact (hybrid, cost-optimal thresholds)\n", table(
            ["Alert cost", "Recall", "Precision", "Alerts/day", "Loss avoided"],
            [[f"${r['alert_cost']:g}", f(r["recall"]), f(r["precision"]), f(r["alerts_per_day"], 1),
              f"{r['savings_pct'] * 100:.1f}%"] for r in an["cost_sensitivity"]]), ""]
    pol = R.get("policy") or {}
    if pol.get("test"):
        t = pol["test"]
        parts += ["## Safety layer (test period)\n", table(
            ["Rule", "Fires", "On genuine", "Fraud rate", "Extra alerts beyond ML", "Extra frauds", "Extra / day"],
            [[rid, v["fires"], v["fires_on_genuine"], f"{v['fraud_rate'] * 100:.0f}%" if v["fires"] else "-",
              v["extra_alerts"], v["extra_frauds"], f(v["extra_alerts_per_day"], 2)] for rid, v in t["rules"].items()]),
            "", f"ML only: recall {f(t['ml_only']['recall'])}, precision {f(t['ml_only']['precision'])}; "
                f"ML + safety layer: recall {f(t['ml_plus_policy']['recall'])}, precision {f(t['ml_plus_policy']['precision'])}; "
                f"{t['extra_alerts_per_day']:.2f} extra step-ups per day.", ""]
    lat = R.get("latency") or {}
    if lat.get("models"):
        parts += ["## Latency (idle machine, one thread, one transaction per call)\n", table(
            ["Model", "p50 ms", "p95 ms"],
            [[k, f(v["p50_ms"], 2), f(v["p95_ms"], 2)] for k, v in lat["models"].items()]), "",
            f"Full API path (features + models + safety layer + SHAP + DB write): p50 {lat['api_single_ms']['p50']:.1f} ms, "
            f"p95 {lat['api_single_ms']['p95']:.1f} ms; stream throughput {lat['api_stream']['per_second']:.0f} txn/s.", ""]
    return "\n".join(parts)


def readme_table(R: Results) -> str:
    bm = R.get("benchmark_sparkov") or {}
    an = R.get("analysis") or {}
    pol = R.get("policy") or {}
    lat = R.get("latency") or {}
    rows = []
    for m in ("hybrid", "xgb", "lgbm", "rf", "mlp", "cnn", "dt", "lr", "iforest", "rules"):
        if m in bm:
            t = bm[m]["test"]
            rows.append([("**" + bm[m]["label"] + "**") if m == "hybrid" else bm[m]["label"], f(t["pr_auc"]),
                         f"{t['recall'] * 100:.1f}%", f"{t['precision'] * 100:.1f}%", f(t["f1"]), f(t["mcc"])])
    out = [table(["Model", "PR-AUC", "Recall", "Precision", "F1", "MCC"], rows), ""]
    h = bm.get("hybrid", {})
    api = lat.get("api_single_ms", {})
    tp = pol.get("test", {})
    bullets = []
    if h.get("test_cost_threshold"):
        c = h["test_cost_threshold"]
        bullets.append(f"Fraud value stopped at the cost-optimal threshold: **{c['amount_recall'] * 100:.1f}%**, "
                       f"avoiding **{c['savings_pct'] * 100:.1f}%** of fraud losses after paying $5 per alert.")
    if api:
        bullets.append(f"End-to-end latency (feature store + 3 models + safety layer + SHAP + audit write, one thread): "
                       f"**{api['p50']:.1f} ms** median, {api['p95']:.1f} ms p95.")
    if tp:
        bullets.append(f"Safety layer (policy rules + novelty alarm): **{tp['extra_alerts_per_day']:.2f} extra step-ups per day** "
                       "on the test period; catches card testing and cloned-card travel, which never occur in the training data.")
    pu = (R.get("protocol") or {}).get("ulb", {})
    if pu:
        bullets.append(f"Evaluation shortcut demo (ULB): SMOTE before a random split reports F1 {f(pu['A']['f1'])}; the same "
                       f"XGBoost evaluated honestly on future data gives F1 {f(pu['D']['f1'])}.")
    return "\n".join(out + [f"* {b}" for b in bullets])


def patch_readme(R: Results) -> None:
    path = config.ROOT / "README.md"
    s = path.read_text(encoding="utf-8")
    a, b = "<!-- results:start -->", "<!-- results:end -->"
    if a in s and b in s:
        s = s[:s.index(a) + len(a)] + "\n" + readme_table(R) + "\n" + s[s.index(b):]
        path.write_text(s, encoding="utf-8")


def write(R: Results | None = None):
    R = R or Results()
    path = config.REPORTS / "RESULTS.md"
    path.write_text(build(R), encoding="utf-8")
    patch_readme(R)
    return path
