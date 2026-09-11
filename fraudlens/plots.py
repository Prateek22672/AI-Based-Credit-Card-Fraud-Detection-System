"""All report/dashboard figures, generated from the saved experiment results.

Run:  python -m fraudlens.plots
"""
from __future__ import annotations

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import FuncFormatter, PercentFormatter
from sklearn.calibration import calibration_curve
from sklearn.metrics import precision_recall_curve, roc_curve

from . import config

INK = "#1E293B"
MUTED = "#64748B"
GRID = "#E2E8F0"
COLORS = {
    "hybrid": "#7C3AED", "xgb": "#4F46E5", "rf": "#0D9488", "lgbm": "#0EA5E9", "lr": "#94A3B8",
    "dt": "#F59E0B", "mlp": "#DB2777", "cnn": "#F97316", "iforest": "#64748B", "rules": "#DC2626",
}
SHORT = {
    "hybrid": "FraudLens Hybrid", "xgb": "XGBoost", "rf": "Random Forest", "lgbm": "LightGBM",
    "lr": "Logistic Regression", "dt": "Decision Tree", "mlp": "Deep MLP", "cnn": "1D-CNN",
    "iforest": "Isolation Forest", "rules": "Legacy rules",
}
TIER = {"LOW": "#16A34A", "MEDIUM": "#F59E0B", "HIGH": "#DC2626"}

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 10, "axes.titlesize": 12, "axes.titleweight": "bold",
    "axes.labelcolor": INK, "axes.edgecolor": GRID, "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8, "axes.axisbelow": True,
    "axes.spines.top": False, "axes.spines.right": False, "legend.frameon": False,
    "figure.dpi": 110, "savefig.dpi": 200, "savefig.bbox": "tight",
})


def load(name):
    p = config.RESULTS / f"{name}.json"
    return json.loads(p.read_text()) if p.exists() else None


def save(fig, name):
    path = config.FIGURES / f"{name}.png"
    fig.savefig(path, facecolor="white")
    plt.close(fig)
    print("  wrote", path.relative_to(config.ROOT))


def pct(x, _=None):
    return f"{x:.0%}"


# ------------------------------------------------------------------ data EDA
def fig_dataset():
    ds = load("dataset_sparkov")
    if not ds:
        return
    fig, axes = plt.subplots(1, 3, figsize=(13, 3.6), gridspec_kw={"width_ratios": [1, 1.6, 1.4]})
    ax = axes[0]
    g, f = ds["rows"] - ds["frauds"], ds["frauds"]
    ax.pie([g, f], colors=["#CBD5E1", "#DC2626"], startangle=90, counterclock=False,
           wedgeprops=dict(width=0.35, edgecolor="white"))
    ax.text(0, 0.08, f"{ds['fraud_rate']:.2%}", ha="center", va="center", fontsize=16, fontweight="bold", color="#DC2626")
    ax.text(0, -0.2, "fraud", ha="center", va="center", color=MUTED)
    ax.set_title(f"Class imbalance\n{g:,} genuine vs {f:,} fraud")
    ax = axes[1]
    hours = sorted(ds["fraud_by_hour"], key=int)
    vals = [ds["fraud_by_hour"][h] for h in hours]
    cols = ["#DC2626" if int(h) >= 22 or int(h) < 4 else "#818CF8" for h in hours]
    ax.bar([int(h) for h in hours], vals, color=cols)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.1%}"))
    ax.set_xlabel("Hour of day")
    ax.set_title("Fraud rate by hour (red = 22:00-04:00)")
    ax.set_xticks(range(0, 24, 2))
    ax = axes[2]
    cat = pd.DataFrame(ds["fraud_by_category"]).T.sort_values("mean")
    ax.barh(cat.index.str.replace("_", " "), cat["mean"],
            color=["#DC2626" if v > 0.01 else "#818CF8" for v in cat["mean"]])
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.1%}"))
    ax.set_title("Fraud rate by merchant category")
    ax.tick_params(axis="y", labelsize=8.5)
    fig.tight_layout()
    save(fig, "fig_dataset_overview")

    amt = ds["amount_by_class"]
    fig, ax = plt.subplots(figsize=(6.5, 3.2))
    labels = ["Genuine", "Fraud"]
    means = [amt["0"]["mean"], amt["1"]["mean"]]
    meds = [amt["0"]["50%"], amt["1"]["50%"]]
    x = np.arange(2)
    ax.bar(x - 0.18, means, 0.36, label="Mean", color=["#94A3B8", "#DC2626"])
    ax.bar(x + 0.18, meds, 0.36, label="Median", color=["#CBD5E1", "#FCA5A5"])
    for i in range(2):
        ax.text(i - 0.18, means[i], f"${means[i]:,.0f}", ha="center", va="bottom", fontsize=9)
        ax.text(i + 0.18, meds[i], f"${meds[i]:,.0f}", ha="center", va="bottom", fontsize=9)
    ax.set_xticks(x, labels)
    ax.set_ylabel("Amount (USD)")
    ax.set_title("Fraudulent transactions are much larger")
    ax.legend()
    save(fig, "fig_amounts")


# ------------------------------------------------------------ E1 benchmark
def fig_benchmark():
    b = load("benchmark_sparkov")
    an = load("analysis")
    if not b:
        return
    P = np.load(config.RESULTS / "preds_sparkov.npz")
    y = P["y_test"]
    names = [n for n in ("hybrid", "xgb", "lgbm", "rf", "dt", "cnn", "mlp", "lr", "iforest", "rules") if f"test_{n}" in P]

    fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.6))
    for n in names:
        p = P[f"test_{n}"]
        pr, rc, _ = precision_recall_curve(y, p)
        lw = 2.8 if n == "hybrid" else 1.4
        axes[0].plot(rc, pr, color=COLORS[n], lw=lw, label=f"{SHORT[n]} ({b[n]['test']['pr_auc']:.3f})")
        fpr, tpr, _ = roc_curve(y, p)
        axes[1].plot(fpr, tpr, color=COLORS[n], lw=lw, label=f"{SHORT[n]} ({b[n]['test']['roc_auc']:.3f})")
    axes[0].set(xlabel="Recall (share of frauds caught)", ylabel="Precision (share of alerts that are fraud)",
                title="Precision-Recall curves (test period)", xlim=(0, 1), ylim=(0, 1.02))
    axes[0].legend(fontsize=8, loc="lower left", title="PR-AUC", title_fontsize=8)
    axes[1].set(xlabel="False positive rate", ylabel="True positive rate", title="ROC curves (log x-axis)",
                xscale="log", xlim=(1e-5, 1))
    axes[1].legend(fontsize=8, loc="lower right", title="ROC-AUC", title_fontsize=8)
    fig.tight_layout()
    save(fig, "fig_pr_roc_curves")

    order = sorted(names, key=lambda n: b[n]["test"]["pr_auc"])
    fig, ax = plt.subplots(figsize=(8.5, 4.6))
    vals = [b[n]["test"]["pr_auc"] for n in order]
    err = None
    if an and "pr_auc_ci" in an:
        err = np.array([[v - an["pr_auc_ci"].get(n, {}).get("low", v), an["pr_auc_ci"].get(n, {}).get("high", v) - v]
                        for n, v in zip(order, vals)]).T
    ax.barh([SHORT[n] for n in order], vals, xerr=err, color=[COLORS[n] for n in order], capsize=3,
            error_kw=dict(ecolor=INK, lw=1))
    for i, (n, v) in enumerate(zip(order, vals)):
        ax.text(v + 0.012, i, f"{v:.3f}  |  F1 {b[n]['test']['f1']:.3f}", va="center", fontsize=8.5, color=INK)
    ax.set_xlim(0, 1.18)
    ax.set_xlabel("PR-AUC on unseen test period (95% bootstrap CI)")
    ax.set_title("Model comparison on the same chronological split")
    save(fig, "fig_model_comparison")

    fig, ax = plt.subplots(figsize=(7.5, 4.6))
    for n in names:
        if "latency" not in b[n]:
            continue
        lat = b[n]["latency"]["p50_ms"]
        ax.scatter(lat, b[n]["test"]["pr_auc"], s=220 if n == "hybrid" else 110, color=COLORS[n],
                   edgecolor="white", lw=1.5, zorder=3)
        offset = {"xgb": (-10, -14), "lgbm": (8, 4)}.get(n, (8, -3))
        ax.annotate(SHORT[n], (lat, b[n]["test"]["pr_auc"]), textcoords="offset points", xytext=offset, fontsize=8.5,
                    ha="right" if n == "xgb" else "left")
    ax.set_xscale("log")
    ax.set(xlabel="Latency per single transaction, median (ms, log scale; idle CPU, one thread)", ylabel="PR-AUC",
           title="Accuracy vs single-transaction latency")
    save(fig, "fig_accuracy_vs_latency")

    # calibration: stacked hybrid vs class-weighted XGBoost. 99% of predictions are ~0, so quantile
    # bins collapse; fixed probability bands show the part that matters for decisions.
    edges = np.array([0.01, 0.05, 0.1, 0.2, 0.4, 0.6, 0.8, 0.95, 1.0001])
    bands = {}
    fig, ax = plt.subplots(figsize=(6.2, 4.8))
    ax.plot([0, 1], [0, 1], ls="--", color=MUTED, lw=1, label="Perfect calibration")
    for n in ("hybrid", "xgb"):
        p = P[f"test_{n}"]
        idx = np.digitize(p, edges) - 1
        rows = [(float(p[idx == i].mean()), float(y[idx == i].mean()), int((idx == i).sum()))
                for i in range(len(edges) - 1) if (idx == i).sum() >= 20]
        bands[n] = [{"band": f"{edges[i]:.2f}-{min(edges[i + 1], 1):.2f}", "predicted": r[0], "observed": r[1], "count": r[2]}
                    for i, r in zip([i for i in range(len(edges) - 1) if (idx == i).sum() >= 20], rows)]
        ax.plot([r[0] for r in rows], [r[1] for r in rows], marker="o", color=COLORS[n], lw=2,
                label=f"{SHORT[n]}" + (" (stacked, calibrated)" if n == "hybrid" else " (class-weighted)"))
    ax.set(xlabel="Predicted fraud probability (transactions with p >= 0.01)", ylabel="Observed fraud rate",
           title="Probability calibration", xlim=(0, 1.02), ylim=(0, 1.02))
    ax.legend(fontsize=8.5, loc="upper left")
    save(fig, "fig_calibration")
    (config.RESULTS / "calibration.json").write_text(json.dumps(bands, indent=2))


# ------------------------------------------------------------- E2 imbalance
def fig_imbalance():
    r = load("imbalance_sparkov")
    if not r:
        return
    strategies = ["none", "weight", "rus", "smote"]
    slabel = {"none": "None", "weight": "Class weight", "rus": "Undersample", "smote": "SMOTE"}
    models = ["lr", "rf", "xgb"]
    fig, axes = plt.subplots(1, 3, figsize=(13, 3.9))
    metrics = [("pr_auc", "PR-AUC (threshold-free)"), ("at_0.5", "F1 at default 0.5 threshold"),
               ("at_tuned", "F1 at threshold tuned on validation")]
    width = 0.2
    scols = {"none": "#94A3B8", "weight": "#4F46E5", "rus": "#F59E0B", "smote": "#DB2777"}
    for ax, (key, title) in zip(axes, metrics):
        for j, s in enumerate(strategies):
            vals = []
            for m in models:
                row = r.get(f"{m}/{s}")
                vals.append((row[key] if key == "pr_auc" else row[key]["f1"]) if row else np.nan)
            ax.bar(np.arange(3) + (j - 1.5) * width, vals, width, label=slabel[s], color=scols[s])
        ax.set_xticks(range(3), [SHORT[m] for m in models], fontsize=9)
        ax.set_ylim(0, 1.05)
        ax.set_title(title, fontsize=11)
    axes[0].legend(fontsize=8.5, loc="upper left")
    fig.suptitle("Imbalance handling: what really changes", fontweight="bold", y=1.03)
    fig.tight_layout()
    save(fig, "fig_imbalance")


# -------------------------------------------------------------- E3 protocol
def fig_protocol():
    r = load("protocol")
    if not r:
        return
    ds = [k for k in ("ulb", "sparkov") if k in r]
    fig, axes = plt.subplots(1, len(ds), figsize=(6.4 * len(ds), 4.2), squeeze=False)
    mets = [("accuracy", "Accuracy", "#94A3B8"), ("precision", "Precision", "#4F46E5"),
            ("recall", "Recall", "#0D9488"), ("f1", "F1", "#7C3AED")]
    for ax, d in zip(axes[0], ds):
        prot = ["A", "B", "C", "D"]
        x = np.arange(len(prot))
        for j, (k, lab, c) in enumerate(mets):
            ax.bar(x + (j - 1.5) * 0.2, [r[d][p][k] for p in prot], 0.2, label=lab, color=c)
        ax.set_xticks(x, ["A\nSMOTE before\nrandom split", "B\nrandom split,\nSMOTE train", "C\ntime split,\nSMOTE train",
                          "D (ours)\ntime split,\nclass weight"], fontsize=8.5)
        ax.set_ylim(0, 1.08)
        ax.set_title(f"{'ULB European dataset' if d == 'ulb' else 'Sparkov dataset'}")
        ax.axhline(r[d]["dummy"]["accuracy"], ls=":", color="#DC2626", lw=1.2)
        ax.text(3.45, r[d]["dummy"]["accuracy"] + 0.01, "'always genuine'\naccuracy", fontsize=7.5, color="#DC2626", ha="right")
    handles, labels = axes[0][0].get_legend_handles_labels()
    fig.suptitle("The same XGBoost, four evaluation protocols: shortcuts inflate the numbers", fontweight="bold", y=1.08)
    fig.legend(handles, labels, loc="upper center", ncol=4, fontsize=9, bbox_to_anchor=(0.5, 1.02))
    fig.tight_layout()
    save(fig, "fig_protocol")


# -------------------------------------------------------------- E4 ablation
def fig_ablation():
    r = load("ablation")
    if not r:
        return
    fs = r["feature_sets"]
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.0), gridspec_kw={"width_ratios": [1, 1.35]})
    ax = axes[0]
    keys = [k for k in ("raw", "deployed", "all") if k in fs]
    labels = {"raw": "Raw fields\n(typical project)", "deployed": "+ behavioural\nfeatures (ours)", "all": "+ age & gender\n(protected)"}
    cols = {"raw": "#94A3B8", "deployed": "#7C3AED", "all": "#C4B5FD"}
    x = np.arange(len(keys))
    ax.bar(x - 0.2, [fs[k]["test"]["pr_auc"] for k in keys], 0.4, color=[cols[k] for k in keys], label="PR-AUC")
    ax.bar(x + 0.2, [fs[k]["test"]["recall"] for k in keys], 0.4, color=[cols[k] for k in keys], alpha=0.55,
           hatch="//", label="Recall")
    for i, k in enumerate(keys):
        ax.text(i - 0.2, fs[k]["test"]["pr_auc"] + 0.01, f"{fs[k]['test']['pr_auc']:.3f}", ha="center", fontsize=8.5)
        ax.text(i + 0.2, fs[k]["test"]["recall"] + 0.01, f"{fs[k]['test']['recall']:.3f}", ha="center", fontsize=8.5)
    ax.set_xticks(x, [labels[k] for k in keys], fontsize=9)
    ax.set_ylim(0, 1.1)
    ax.set_title("Feature engineering (XGBoost)")
    ax.legend(fontsize=8.5, loc="upper left")
    ax = axes[1]
    comp = r["components"]
    order = [k for k in ("iforest", "rf", "xgb", "avg(xgb,rf)", "rf+iforest", "xgb+rf", "xgb+iforest",
                         "xgb_with_if_feature", "xgb+rf+iforest") if k in comp]
    nice = {"iforest": "IF only", "rf": "RF only", "xgb": "XGB only", "avg(xgb,rf)": "avg(XGB,RF)",
            "rf+iforest": "RF+IF", "xgb+rf": "XGB+RF", "xgb+iforest": "XGB+IF",
            "xgb_with_if_feature": "XGB w/ IF feature", "xgb+rf+iforest": "XGB+RF+IF (ours)"}
    vals = [comp[k]["test"]["pr_auc"] for k in order]
    ax.barh([nice[k] for k in order], vals, color=["#7C3AED" if k == "xgb+rf+iforest" else "#A5B4FC" for k in order])
    lo = min(v for v in vals if v > 0.5) if any(v > 0.5 for v in vals) else 0
    x0 = max(0, lo - 0.05)
    for i, v in enumerate(vals):
        if v < x0:   # off the zoomed axis: label it at the left edge instead of outside the plot
            ax.text(x0 + 0.002, i, f"{v:.4f} (off scale)", va="center", fontsize=8.5, color=MUTED)
        else:
            ax.text(v + 0.002, i, f"{v:.4f}", va="center", fontsize=8.5)
    ax.set_xlim(x0, 1.0)
    ax.set_title("Hybrid components (stacked, PR-AUC on test)")
    fig.tight_layout()
    save(fig, "fig_ablation")


# ---------------------------------------------------------------- E5 unseen
def fig_unseen():
    r = load("unseen")
    if not r:
        return
    fig, axes = plt.subplots(1, len(r), figsize=(6.8 * len(r), 4.0), squeeze=False)
    nice = {"xgb": "XGBoost", "rf": "Random\nForest", "iforest": "Isolation\nForest", "novelty_alarm": "Novelty\nalarm N1",
            "hybrid": "Hybrid\n(stacking)", "hybrid_with_policy": "Hybrid +\nsafety layer",
            "hybrid_trained_on_all_types": "Hybrid that\nsaw this type"}
    col = {"novelty_alarm": "#14B8A6", "hybrid_with_policy": "#F59E0B", "hybrid_trained_on_all_types": "#CBD5E1"}
    for ax, (held, v) in zip(axes[0], r.items()):
        res = v["results"]
        names = [n for n in nice if n in res]
        rec = [res[n]["recall"] for n in names]
        ax.bar(range(len(names)), rec, color=[col.get(n, COLORS.get(n, "#C4B5FD")) for n in names])
        for i, val in enumerate(rec):
            ax.text(i, val + 0.01, f"{val:.2f}", ha="center", fontsize=9)
        ax.set_xticks(range(len(names)), [nice[n] for n in names], fontsize=8)
        ax.set_ylim(0, 1.1)
        ax.set_ylabel("Recall on the never-seen fraud type")
        ax.set_title(f"Hold out {held.replace('_', '-')} fraud ({v['held_out_frauds_in_test']} test frauds)")
    fig.tight_layout()
    save(fig, "fig_unseen")


# ---------------------------------------------------------------- E6 ULB
def fig_ulb():
    r = load("benchmark_ulb")
    if not r:
        return
    names = [n for n in ("hybrid", "xgb", "lgbm", "rf", "mlp", "lr", "iforest") if n in r]
    order = sorted(names, key=lambda n: r[n]["test"]["pr_auc"])
    fig, ax = plt.subplots(figsize=(8, 3.8))
    vals = [r[n]["test"]["pr_auc"] for n in order]
    err = np.array([[v - r[n]["test"]["pr_auc_ci"][0], r[n]["test"]["pr_auc_ci"][1] - v] for n, v in zip(order, vals)]).T
    ax.barh([SHORT[n] for n in order], vals, xerr=err, capsize=3, color=[COLORS[n] for n in order])
    for i, (n, v) in enumerate(zip(order, vals)):
        ax.text(min(v + 0.03, 1.02), i, f"{v:.3f} | recall {r[n]['test']['recall']:.2f} | prec {r[n]['test']['precision']:.2f}",
                va="center", fontsize=8.5)
    ax.set_xlim(0, 1.45)
    ax.set_xlabel("PR-AUC on the last 20% of the timeline (95% CI)")
    ax.set_title("ULB European dataset benchmark")
    save(fig, "fig_ulb")


# ---------------------------------------------------------- E7 analysis
def fig_business():
    an = load("analysis")
    b = load("benchmark_sparkov")
    if not an or not b:
        return
    P = np.load(config.RESULTS / "preds_sparkov.npz")
    y, amt, p = P["y_test"], P["amt_test"], P["test_hybrid"]
    thr = an["tiers_thresholds"]
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.2))
    ax = axes[0]
    grid = np.unique(np.quantile(p, np.linspace(0.5, 1, 400)))
    fraud_total = amt[y == 1].sum()
    for c, col in zip(config.ALERT_COST_SENSITIVITY, ["#C7D2FE", "#A5B4FC", "#7C3AED", "#4F46E5", "#1E1B4B"]):
        costs = [(fraud_total - amt[(y == 1) & (p >= t)].sum()) + c * (p >= t).sum() for t in grid]
        ax.plot(grid, np.array(costs) / 1e3, color=col, lw=2 if c == config.ALERT_COST else 1.2,
                label=f"alert cost ${c:g}")
    ax.axvline(thr["alert"], color="#F59E0B", ls="--", lw=1.4)
    ax.axvline(thr["block"], color="#DC2626", ls="--", lw=1.4)
    ax.text(thr["alert"], ax.get_ylim()[1] * 0.92, " step-up", color="#B45309", fontsize=8.5)
    ax.text(thr["block"], ax.get_ylim()[1] * 0.82, " block", color="#B91C1C", fontsize=8.5)
    ax.set_xscale("log")
    ax.set_xlim(max(grid.min(), 1e-6), 1)
    ax.set(xlabel="Hybrid fraud probability threshold (log scale)", ylabel="Total cost on test period ($ thousands)",
           title="Money lost vs alert threshold")
    ax.legend(fontsize=8)
    ax = axes[1]
    tiers = an["tiers"]
    names = ["LOW", "MEDIUM", "HIGH"]
    share = [tiers[t]["share"] for t in names]
    frauds = [tiers[t]["frauds"] for t in names]
    bars = ax.bar(names, [tiers[t]["transactions"] for t in names], color=[TIER[t] for t in names])
    ax.set_yscale("log")
    for bar, t, s, f in zip(bars, names, share, frauds):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() * 1.15,
                f"{tiers[t]['transactions']:,} txns ({s:.2%})\n{f} frauds, fraud rate {tiers[t]['fraud_rate']:.1%}",
                ha="center", fontsize=8.5)
    ax.set_ylim(1, max(t["transactions"] for t in tiers.values()) * 12)
    ax.set_title("Risk tiers on the test period: Approve / Step-up / Block")
    ax.set_ylabel("Transactions (log scale)")
    fig.tight_layout()
    save(fig, "fig_business")

    m = an["monthly"]
    months = list(m)
    fig, ax = plt.subplots(figsize=(7, 3.4))
    for k, lab, c in (("pr_auc", "PR-AUC", "#7C3AED"), ("recall", "Recall", "#0D9488"), ("precision", "Precision", "#4F46E5")):
        ax.plot(months, [m[mo][k] for mo in months], marker="o", lw=2, color=c, label=lab)
    ax.set_ylim(0.5, 1.02)
    ax.set_title(f"Stability over the test months (PSI val->test = {an['psi_val_to_test']:.3f})")
    ax.legend(fontsize=8.5, loc="lower left")
    save(fig, "fig_monthly")

    ht = b["hybrid"]["test"]
    cm = np.array([[ht["tn"], ht["fp"]], [ht["fn"], ht["tp"]]])
    fig, ax = plt.subplots(figsize=(4.4, 3.8))
    ax.imshow(np.log10(cm + 1), cmap="Purples")
    for (i, j), v in np.ndenumerate(cm):
        ax.text(j, i, f"{v:,}", ha="center", va="center", fontsize=13, fontweight="bold",
                color="white" if (i, j) in ((0, 0), (1, 1)) else INK)
    ax.set_xticks([0, 1], ["Predicted genuine", "Predicted fraud"])
    ax.set_yticks([0, 1], ["Actual genuine", "Actual fraud"])
    ax.grid(False)
    ax.set_title("Hybrid confusion matrix (test)")
    save(fig, "fig_confusion")


def fig_explain():
    e = load("explain")
    if not e:
        return
    gi = e["global_importance"][:15][::-1]
    fig, ax = plt.subplots(figsize=(7.5, 5))
    ax.barh([g["label"] for g in gi], [g["mean_abs_shap"] for g in gi], color="#7C3AED")
    ax.set_xlabel("Mean |SHAP value| (impact on fraud log-odds)")
    ax.set_title("What drives the decisions (global SHAP importance)")
    ax.tick_params(axis="y", labelsize=9)
    save(fig, "fig_shap_importance")
    path = config.RESULTS / "shap_sample.npz"
    if path.exists():
        import shap
        from .explain import FEATURE_LABELS
        S = np.load(path, allow_pickle=True)
        names = [FEATURE_LABELS.get(f, f) for f in S["features"]]
        plt.figure()
        shap.summary_plot(S["shap"], S["X"], feature_names=names, max_display=15, show=False, plot_size=(8.5, 6))
        fig = plt.gcf()
        fig.axes[0].set_title("SHAP beeswarm: direction and size of each feature's effect", fontweight="bold")
        save(fig, "fig_shap_beeswarm")


def main():
    for fn in (fig_dataset, fig_benchmark, fig_imbalance, fig_protocol, fig_ablation, fig_unseen, fig_ulb,
               fig_business, fig_explain):
        print(fn.__name__)
        try:
            fn()
        except Exception as ex:  # keep going: one missing result should not block the other figures
            print("  skipped:", type(ex).__name__, ex)


if __name__ == "__main__":
    main()
