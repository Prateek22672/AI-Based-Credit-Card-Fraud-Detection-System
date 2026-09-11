import { useEffect, useState } from "react";
import { Database, Server } from "lucide-react";
import { fetchResult } from "../../lib/api.js";
import { isNum, num, pct } from "../../lib/format.js";
import { NotGenerated } from "../../components/ui/EmptyState.jsx";
import { PageLoader } from "../../components/ui/Spinner.jsx";

export function useResult(name) {
  const [state, setState] = useState({ loading: true, data: null, source: null, error: null });
  useEffect(() => {
    let alive = true;
    setState((s) => ({ ...s, loading: true }));
    fetchResult(name).then((r) => alive && setState({ loading: false, ...r }));
    return () => {
      alive = false;
    };
  }, [name]);
  return state;
}

// Wraps a tab: loading → not generated → render(data).
export function ResultSection({ name, hint, children }) {
  const r = useResult(name);
  if (r.loading) return <PageLoader label={`Loading ${name}`} />;
  if (!r.data) return <NotGenerated name={name} hint={hint} />;
  return (
    <div className="space-y-5">
      {children(r.data)}
      <SourceNote name={name} source={r.source} />
    </div>
  );
}

export function SourceNote({ name, source }) {
  return (
    <p className="flex items-center gap-1.5 text-[11px] text-muted">
      {source === "api" ? <Server size={11} /> : <Database size={11} />}
      Source: <span className="font-mono">reports/results/{name}.json</span> via {source === "api" ? "the API" : "the static copy (npm run sync-data)"}.
    </p>
  );
}

// ------------------------------------------------------------- cell helpers
export const P = (v, d = 3) => (isNum(v) ? num(v, d) : "—");
export const Pc = (v, d = 1) => (isNum(v) ? pct(v, d) : "—");

export function Delta({ diff, ci_low, ci_high, p_value }) {
  if (!isNum(diff)) return <span className="text-muted">—</span>;
  const sig = isNum(p_value) && p_value < 0.05;
  return (
    <span className={`tabular-nums ${diff > 0 ? "text-green-700" : diff < 0 ? "text-red-700" : ""}`} title={`95% CI [${P(ci_low)}, ${P(ci_high)}]${isNum(p_value) ? ` · p = ${p_value.toFixed(3)}` : ""}`}>
      {diff > 0 ? "+" : ""}{num(diff, 3)}
      {isNum(p_value) && <span className={`ml-1 text-[10px] ${sig ? "text-green-700" : "text-muted"}`}>{sig ? "sig." : "n.s."}</span>}
    </span>
  );
}

// Order for model rows so the tables read consistently.
export const MODEL_ORDER = ["hybrid", "xgb", "rf", "lgbm", "dt", "lr", "mlp", "cnn", "iforest", "rules"];
export const sortModels = (keys) =>
  keys.slice().sort((a, b) => {
    const ia = MODEL_ORDER.indexOf(a), ib = MODEL_ORDER.indexOf(b);
    return (ia === -1 ? 99 : ia) - (ib === -1 ? 99 : ib);
  });
export const SHORT = { hybrid: "Hybrid", xgb: "XGBoost", rf: "Random Forest", lgbm: "LightGBM", dt: "Decision Tree", lr: "Logistic Reg.", mlp: "Deep MLP", cnn: "1D-CNN", iforest: "Isolation Forest", rules: "Rules" };
