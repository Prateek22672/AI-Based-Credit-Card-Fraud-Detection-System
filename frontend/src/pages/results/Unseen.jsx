import { Bar, BarChart, CartesianGrid, Legend, Tooltip, XAxis, YAxis } from "recharts";
import Card from "../../components/ui/Card.jsx";
import Callout from "../../components/ui/Callout.jsx";
import { AXIS, ChartBox, ChartTooltip, GRID } from "../../components/charts/ChartBits.jsx";
import { int, isNum } from "../../lib/format.js";
import { CHART } from "../../lib/risk.js";
import { P, Pc, ResultSection } from "./shared.jsx";

const ORDER = ["xgb", "rf", "iforest", "novelty_alarm", "hybrid", "hybrid_with_policy", "hybrid_trained_on_all_types"];
const LABEL = {
  xgb: "XGBoost (never saw this fraud type)", rf: "Random Forest (never saw this fraud type)", iforest: "Isolation Forest (unsupervised)",
  novelty_alarm: "Novelty alarm alone (N1: anomaly ≥ 99.95th pct)",
  hybrid: "Hybrid, stacking only (never saw this fraud type)",
  hybrid_with_policy: "Hybrid + safety layer (novelty alarm + policy rules)",
  hybrid_trained_on_all_types: "Hybrid trained on all fraud types (reference)",
};
const HELD = { online: "Online (card-not-present) fraud held out", in_person: "In-person fraud held out" };

export default function Unseen() {
  return (
    <ResultSection name="unseen" hint="stage: unseen">
      {(data) => (
        <>
          <Callout tone="info" title="Can the system catch a kind of fraud it was never trained on?">
            All frauds of one channel (online or in-person) are removed from the training and validation data, the engine is retrained, and it is then tested only on that
            withheld fraud type. Supervised models can only recognise what they have seen; the unsupervised Isolation Forest scores &quot;unlike normal&quot;. Compare the
            stacking-only hybrid with the hybrid plus safety layer to see what the novelty route adds. Rows without a PR-AUC are yes/no decision rules.
          </Callout>
          {Object.keys(HELD).filter((k) => data[k]).map((k) => {
            const block = data[k];
            const rows = block.results || {};
            const keys = ORDER.filter((x) => rows[x]).concat(Object.keys(rows).filter((x) => !ORDER.includes(x)));
            const chart = keys.map((x) => ({ name: (LABEL[x] || x).split(" (")[0], prAuc: rows[x].pr_auc, recall: rows[x].recall, precision: rows[x].precision }));
            return (
              <Card key={k} title={HELD[k]} subtitle={`${int(block.frauds_removed_from_training)} frauds removed from training/validation · ${int(block.held_out_frauds_in_test)} of this type in the test quarter`} noPad>
                <div className="grid grid-cols-1 gap-4 xl:grid-cols-5">
                  <div className="table-wrap rounded-none border-x-0 border-b-0 xl:col-span-3">
                    <table className="table">
                      <thead><tr><th>Detector</th><th className="num">PR-AUC</th><th className="num">ROC-AUC</th><th className="num">Precision</th><th className="num">Recall</th><th className="num">F1</th><th className="num">Caught</th></tr></thead>
                      <tbody>
                        {keys.map((x) => (
                          <tr key={x} className={x === "hybrid_with_policy" || (x === "hybrid" && !rows.hybrid_with_policy) ? "row-highlight" : ""}>
                            <td className="whitespace-normal">{LABEL[x] || x}</td>
                            <td className="num font-semibold">{P(rows[x].pr_auc)}</td>
                            <td className="num">{P(rows[x].roc_auc, 4)}</td>
                            <td className="num">{Pc(rows[x].precision)}</td>
                            <td className="num">{Pc(rows[x].recall)}</td>
                            <td className="num">{P(rows[x].f1)}</td>
                            <td className="num text-muted">{isNum(rows[x].tp) ? `${int(rows[x].tp)} / ${int(rows[x].tp + rows[x].fn)}` : "—"}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  <div className="px-5 pb-5 xl:col-span-2 xl:pt-2">
                    <ChartBox height={220}>
                      <BarChart data={chart} margin={{ left: -8, right: 8, top: 8, bottom: 0 }} barCategoryGap={14} barGap={2}>
                        <CartesianGrid {...GRID} />
                        <XAxis dataKey="name" {...AXIS} tick={{ fontSize: 10, fill: "#64748b" }} interval={0} />
                        <YAxis domain={[0, 1]} {...AXIS} />
                        <Tooltip content={<ChartTooltip formatter={(v) => (isNum(v) ? v.toFixed(3) : "—")} />} cursor={{ fill: "#f1f5f9" }} />
                        <Legend iconType="square" iconSize={10} />
                        <Bar dataKey="prAuc" name="PR-AUC" fill={CHART.primary} radius={[3, 3, 0, 0]} />
                        <Bar dataKey="recall" name="Recall" fill={CHART.teal} radius={[3, 3, 0, 0]} />
                      </BarChart>
                    </ChartBox>
                  </div>
                </div>
              </Card>
            );
          })}
        </>
      )}
    </ResultSection>
  );
}
