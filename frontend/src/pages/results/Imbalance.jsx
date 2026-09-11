import { Bar, BarChart, CartesianGrid, Legend, Tooltip, XAxis, YAxis } from "recharts";
import Card from "../../components/ui/Card.jsx";
import Callout from "../../components/ui/Callout.jsx";
import { AXIS, ChartBox, ChartTooltip, GRID } from "../../components/charts/ChartBits.jsx";
import { isNum, secs } from "../../lib/format.js";
import { SERIES } from "../../lib/risk.js";
import { P, Pc, ResultSection } from "./shared.jsx";

const STRAT_ORDER = ["none", "weight", "rus", "smote"];
const MODEL_ORDER = ["lr", "rf", "xgb"];

export default function Imbalance() {
  return (
    <ResultSection name="imbalance_sparkov" hint="stage: imbalance">
      {(data) => {
        const entries = Object.entries(data).map(([key, v]) => {
          const [m, s] = key.split("/");
          return { key, m, s, ...v };
        });
        entries.sort((a, b) => MODEL_ORDER.indexOf(a.m) - MODEL_ORDER.indexOf(b.m) || STRAT_ORDER.indexOf(a.s) - STRAT_ORDER.indexOf(b.s));
        const strategies = [...new Set(entries.map((e) => e.s))].sort((a, b) => STRAT_ORDER.indexOf(a) - STRAT_ORDER.indexOf(b));
        const stratLabel = Object.fromEntries(entries.map((e) => [e.s, e.strategy]));
        const models = [...new Set(entries.map((e) => e.m))];
        const chart = models.map((m) => {
          const row = { name: entries.find((e) => e.m === m)?.model || m };
          for (const s of strategies) row[s] = entries.find((e) => e.m === m && e.s === s)?.pr_auc ?? null;
          return row;
        });
        const best = entries.reduce((a, b) => (b.pr_auc > (a?.pr_auc ?? -1) ? b : a), null);
        return (
          <>
            <Callout tone="info" title="Does re-balancing the training data help?">
              Each model is trained four ways on the same chronological split. Resampling happens inside the training pipeline only, never on validation or test data.
              {best && ` Best PR-AUC: ${best.model} with ${best.strategy.toLowerCase()} (${P(best.pr_auc)}).`} Compare the Brier score and mean predicted probability: 1:1 resampling makes probabilities over-confident (mean prediction far above the real fraud rate), which matters when thresholds are set in money terms.
            </Callout>
            <Card title="Model × strategy" subtitle="Test-quarter metrics · F1 at a fixed 0.5 cut-off vs a threshold tuned on validation" noPad>
              <div className="table-wrap rounded-t-none border-x-0 border-b-0">
                <table className="table">
                  <thead><tr><th>Model</th><th>Strategy</th><th className="num">PR-AUC</th><th className="num">ROC-AUC</th><th className="num">F1 @ 0.5</th><th className="num">F1 tuned</th><th className="num">Precision tuned</th><th className="num">Recall tuned</th><th className="num">Brier</th><th className="num">Mean pred. prob</th><th className="num">Actual rate</th><th className="num">Fit</th></tr></thead>
                  <tbody>
                    {entries.map((e) => (
                      <tr key={e.key} className={best?.key === e.key ? "row-highlight" : ""}>
                        <td>{e.model}</td>
                        <td className="text-ink-2">{e.strategy}</td>
                        <td className="num font-semibold">{P(e.pr_auc)}</td>
                        <td className="num">{P(e.roc_auc, 4)}</td>
                        <td className="num">{P(e["at_0.5"]?.f1)}</td>
                        <td className="num">{P(e.at_tuned?.f1)}</td>
                        <td className="num">{Pc(e.at_tuned?.precision)}</td>
                        <td className="num">{Pc(e.at_tuned?.recall)}</td>
                        <td className="num">{isNum(e.brier) ? e.brier.toFixed(5) : "—"}</td>
                        <td className="num">{Pc(e.mean_predicted_prob, 2)}</td>
                        <td className="num text-muted">{Pc(e.actual_fraud_rate, 2)}</td>
                        <td className="num text-muted">{secs(e.fit_seconds)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
            <Card title="PR-AUC by strategy" subtitle="Grouped by model">
              <ChartBox height={260}>
                <BarChart data={chart} margin={{ left: -8, right: 8, top: 8, bottom: 0 }} barCategoryGap={18} barGap={3}>
                  <CartesianGrid {...GRID} />
                  <XAxis dataKey="name" {...AXIS} />
                  <YAxis domain={[0, 1]} {...AXIS} />
                  <Tooltip content={<ChartTooltip formatter={(v) => (isNum(v) ? v.toFixed(3) : "—")} />} cursor={{ fill: "#f1f5f9" }} />
                  <Legend iconType="square" iconSize={10} />
                  {strategies.map((s, i) => <Bar key={s} dataKey={s} name={stratLabel[s] || s} fill={SERIES[i % SERIES.length]} radius={[3, 3, 0, 0]} />)}
                </BarChart>
              </ChartBox>
            </Card>
          </>
        );
      }}
    </ResultSection>
  );
}
