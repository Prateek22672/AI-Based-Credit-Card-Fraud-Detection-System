import { Bar, BarChart, CartesianGrid, Legend, Tooltip, XAxis, YAxis } from "recharts";
import Card from "../../components/ui/Card.jsx";
import Callout from "../../components/ui/Callout.jsx";
import { AXIS, ChartBox, ChartTooltip, GRID } from "../../components/charts/ChartBits.jsx";
import { isNum } from "../../lib/format.js";
import { CHART } from "../../lib/risk.js";
import { P, Pc, ResultSection } from "./shared.jsx";

const ORDER = ["dummy", "A", "B", "C", "D"];
const DS_LABEL = { ulb: "ULB / European card dataset", sparkov: "Sparkov (deployed feature set)" };

function DatasetBlock({ name, rows }) {
  const keys = ORDER.filter((k) => rows[k]);
  const chart = keys.map((k) => ({ name: k === "dummy" ? "No model" : `Protocol ${k}`, precision: rows[k].precision, recall: rows[k].recall, f1: rows[k].f1, prAuc: rows[k].pr_auc }));
  return (
    <Card title={DS_LABEL[name] || name} subtitle="Same XGBoost configuration, evaluated under four protocols of increasing rigour" noPad>
      <div className="table-wrap rounded-t-none border-x-0 border-b-0">
        <table className="table">
          <thead><tr><th>Protocol</th><th>Description</th><th className="num">Accuracy</th><th className="num">Precision</th><th className="num">Recall</th><th className="num">F1</th><th className="num">PR-AUC</th><th className="num">Fraud share in test</th></tr></thead>
          <tbody>
            {keys.map((k) => (
              <tr key={k} className={k === "D" ? "row-highlight" : ""}>
                <td className="font-semibold">{k === "dummy" ? "—" : k}</td>
                <td className="whitespace-normal text-[12.5px] text-ink-2">{rows[k].protocol}</td>
                <td className="num">{Pc(rows[k].accuracy, 2)}</td>
                <td className="num">{Pc(rows[k].precision)}</td>
                <td className="num">{Pc(rows[k].recall)}</td>
                <td className="num">{P(rows[k].f1)}</td>
                <td className="num font-semibold">{P(rows[k].pr_auc)}</td>
                <td className="num text-muted">{isNum(rows[k].test_fraud_share) ? Pc(rows[k].test_fraud_share, 2) : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="px-5 pb-5 pt-3">
        <ChartBox height={220}>
          <BarChart data={chart} margin={{ left: -8, right: 8, top: 8, bottom: 0 }} barCategoryGap={18} barGap={3}>
            <CartesianGrid {...GRID} />
            <XAxis dataKey="name" {...AXIS} />
            <YAxis domain={[0, 1]} {...AXIS} />
            <Tooltip content={<ChartTooltip formatter={(v) => (isNum(v) ? v.toFixed(3) : "—")} />} cursor={{ fill: "#f1f5f9" }} />
            <Legend iconType="square" iconSize={10} />
            <Bar dataKey="precision" name="Precision" fill={CHART.primary} radius={[3, 3, 0, 0]} />
            <Bar dataKey="recall" name="Recall" fill={CHART.teal} radius={[3, 3, 0, 0]} />
            <Bar dataKey="f1" name="F1" fill={CHART.amber} radius={[3, 3, 0, 0]} />
            <Bar dataKey="prAuc" name="PR-AUC" fill={CHART.violet} radius={[3, 3, 0, 0]} />
          </BarChart>
        </ChartBox>
      </div>
    </Card>
  );
}

export default function Protocol() {
  return (
    <ResultSection name="protocol" hint="stage: protocol">
      {(data) => (
        <>
          <Callout tone="warn" title="Why many published results are too good to be true">
            <strong>Protocol A — SMOTE before the split with a random split — inflates results:</strong> synthetic fraud points are interpolated between real ones, so
            near-copies of test frauds leak into training and the test set contains ~50% fraud instead of &lt;1%. Protocol B fixes the leak but still lets the model
            see the future (random split). Protocol C splits chronologically; Protocol D (FraudLens) additionally drops synthetic data in favour of class weighting and tunes
            the threshold on a separate validation period — the numbers a bank would actually observe.
          </Callout>
          {["ulb", "sparkov"].filter((k) => data[k]).map((k) => <DatasetBlock key={k} name={k} rows={data[k]} />)}
        </>
      )}
    </ResultSection>
  );
}
