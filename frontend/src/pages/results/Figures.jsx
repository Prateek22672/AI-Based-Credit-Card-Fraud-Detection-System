import { useState } from "react";
import Figure from "../../components/ui/Figure.jsx";
import Callout from "../../components/ui/Callout.jsx";

export const FIGURES = [
  ["fig_dataset_overview", "Dataset overview: transactions and fraud rate over time, by hour of day and by merchant category."],
  ["fig_amounts", "Transaction amounts for genuine vs fraudulent transactions (log scale)."],
  ["fig_pr_roc_curves", "Precision–recall and ROC curves of every model on the unseen test quarter."],
  ["fig_model_comparison", "Model comparison: PR-AUC with 95% bootstrap confidence intervals, F1 and money saved."],
  ["fig_accuracy_vs_latency", "Accuracy (PR-AUC) against single-transaction scoring latency: the deployment trade-off."],
  ["fig_calibration", "Reliability diagram: predicted probability vs observed fraud rate for the hybrid and its components."],
  ["fig_imbalance", "Class-imbalance strategies: PR-AUC and calibration for no balancing, class weighting, undersampling and SMOTE."],
  ["fig_protocol", "Evaluation-protocol study: how SMOTE-before-split and random splits inflate reported metrics."],
  ["fig_ablation", "Ablation: feature sets and hybrid components."],
  ["fig_unseen", "Unseen fraud type: detectors trained without one fraud channel, tested on it."],
  ["fig_ulb", "Benchmark on the European (ULB) dataset."],
  ["fig_business", "Business impact: cost sensitivity, risk tiers and alerts per day."],
  ["fig_monthly", "Monthly stability of PR-AUC, precision and recall over the test quarter."],
  ["fig_confusion", "Confusion matrix of the deployed hybrid at the alert and block thresholds."],
  ["fig_shap_importance", "Global SHAP feature importance of the XGBoost component."],
  ["fig_shap_beeswarm", "SHAP beeswarm: direction and spread of each feature's effect."],
];

export default function Figures() {
  const [missing, setMissing] = useState(0);
  return (
    <div className="space-y-4">
      <Callout tone="info">
        Figures are rendered by <span className="font-mono">python -m fraudlens.plots</span> into <span className="font-mono">reports/figures/</span> and served at{" "}
        <span className="font-mono">/figures/&lt;name&gt;.png</span> (or from the static copy). Click a figure to open it full size. Missing figures are skipped.
      </Callout>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {FIGURES.map(([name, caption]) => (
          <FigureCell key={name} name={name} caption={caption} onMissing={() => setMissing((m) => m + 1)} />
        ))}
      </div>
      {missing >= FIGURES.length && (
        <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50/60 p-8 text-center text-[13px] text-muted">
          No figures generated yet: run the plotting stage and refresh.
        </div>
      )}
    </div>
  );
}

function FigureCell({ name, caption, onMissing }) {
  return (
    <Figure
      name={name}
      caption={
        <>
          <span className="font-mono text-[11px] text-muted">{name}.png</span>
          <br />
          {caption}
        </>
      }
      onMissing={onMissing}
    />
  );
}
