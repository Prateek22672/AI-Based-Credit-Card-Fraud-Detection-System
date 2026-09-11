import { useSearchParams } from "react-router-dom";
import Tabs from "../components/ui/Tabs.jsx";
import Benchmark from "./results/Benchmark.jsx";
import Imbalance from "./results/Imbalance.jsx";
import Protocol from "./results/Protocol.jsx";
import Ablation from "./results/Ablation.jsx";
import Unseen from "./results/Unseen.jsx";
import Policy from "./results/Policy.jsx";
import Ulb from "./results/Ulb.jsx";
import Business from "./results/Business.jsx";
import Explainability from "./results/Explainability.jsx";
import Figures from "./results/Figures.jsx";
import Dataset from "./results/Dataset.jsx";

const TABS = [
  { value: "benchmark", label: "Benchmark", el: <Benchmark />, blurb: "E1 · Every model on the same chronological Sparkov split" },
  { value: "dataset", label: "Dataset", el: <Dataset />, blurb: "Sparkov dataset facts and the split used everywhere" },
  { value: "imbalance", label: "Imbalance", el: <Imbalance />, blurb: "E2 · No balancing vs class weighting vs undersampling vs SMOTE" },
  { value: "protocol", label: "Evaluation protocol", el: <Protocol />, blurb: "E3 · How common evaluation shortcuts inflate results" },
  { value: "ablation", label: "Ablation", el: <Ablation />, blurb: "E4 · Which features and which detectors matter" },
  { value: "unseen", label: "Unseen fraud", el: <Unseen />, blurb: "E5 · Catching a fraud type the supervised models never saw" },
  { value: "policy", label: "Safety layer", el: <Policy />, blurb: "Cost and effect of the policy rules and the novelty alarm on real traffic" },
  { value: "ulb", label: "ULB benchmark", el: <Ulb />, blurb: "E6 · Same recipe on the European (ULB) dataset" },
  { value: "business", label: "Business impact", el: <Business />, blurb: "E7 · Cost sensitivity, risk tiers, monthly stability, drift" },
  { value: "explain", label: "Explainability", el: <Explainability />, blurb: "Global SHAP importance and case studies" },
  { value: "figures", label: "Figures", el: <Figures />, blurb: "Report figures rendered by the plotting stage" },
];

export default function Results() {
  const [params, setParams] = useSearchParams();
  const tab = TABS.find((t) => t.value === params.get("tab")) || TABS[0];
  return (
    <div className="space-y-4">
      <Tabs tabs={TABS} value={tab.value} onChange={(v) => setParams({ tab: v })} />
      <p className="text-[12.5px] text-muted">{tab.blurb}</p>
      <div key={tab.value}>{tab.el}</div>
    </div>
  );
}
