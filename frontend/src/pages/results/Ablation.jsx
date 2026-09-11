import { Bar, BarChart, CartesianGrid, Cell, LabelList, Tooltip, XAxis, YAxis } from "recharts";
import Card from "../../components/ui/Card.jsx";
import Callout from "../../components/ui/Callout.jsx";
import { AXIS, ChartBox, ChartTooltip, GRID } from "../../components/charts/ChartBits.jsx";
import { secs } from "../../lib/format.js";
import { CHART } from "../../lib/risk.js";
import { Delta, P, Pc, ResultSection } from "./shared.jsx";

const FS_ORDER = ["raw", "deployed", "all"];
const COMP_ORDER = ["xgb", "rf", "iforest", "xgb+rf", "xgb+iforest", "rf+iforest", "xgb+rf+iforest", "avg(xgb,rf)", "xgb_with_if_feature"];
const COMP_LABEL = {
  xgb: "XGBoost only", rf: "Random Forest only", iforest: "Isolation Forest only", "xgb+rf": "XGB + RF", "xgb+iforest": "XGB + IF", "rf+iforest": "RF + IF",
  "xgb+rf+iforest": "XGB + RF + IF (FraudLens)", "avg(xgb,rf)": "Simple average of XGB and RF", xgb_with_if_feature: "XGB with IF score as a feature",
};

function Block({ title, subtitle, rows, order, labelOf, refKey, vsKey, highlight, extraCol }) {
  const keys = order.filter((k) => rows[k]).concat(Object.keys(rows).filter((k) => !order.includes(k)));
  const chart = keys.map((k) => ({ name: labelOf(k), prAuc: rows[k].test?.pr_auc, hi: k === highlight }));
  return (
    <Card title={title} subtitle={subtitle} noPad>
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-5">
        <div className="table-wrap rounded-none border-x-0 border-b-0 lg:col-span-3">
          <table className="table">
            <thead><tr><th>Variant</th>{extraCol && <th className="num">{extraCol.label}</th>}<th className="num">PR-AUC</th><th className="num">Precision</th><th className="num">Recall</th><th className="num">F1</th><th className="num">$ caught</th><th className="num">Δ PR-AUC vs {refKey}</th><th className="num">Fit</th></tr></thead>
            <tbody>
              {keys.map((k) => {
                const r = rows[k];
                return (
                  <tr key={k} className={k === highlight ? "row-highlight" : ""}>
                    <td className="whitespace-normal">{r.label && r.label !== k ? r.label : labelOf(k)}</td>
                    {extraCol && <td className="num">{extraCol.get(r) ?? "—"}</td>}
                    <td className="num font-semibold">{P(r.test?.pr_auc)}</td>
                    <td className="num">{Pc(r.test?.precision)}</td>
                    <td className="num">{Pc(r.test?.recall)}</td>
                    <td className="num">{P(r.test?.f1)}</td>
                    <td className="num">{Pc(r.test?.amount_recall)}</td>
                    <td className="num">{r[vsKey] ? <Delta {...r[vsKey]} /> : <span className="text-muted">ref.</span>}</td>
                    <td className="num text-muted">{r.fit_seconds ? secs(r.fit_seconds) : "—"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <div className="px-5 pb-5 lg:col-span-2 lg:pt-2">
          <ChartBox height={Math.max(160, keys.length * 30)}>
            <BarChart data={chart} layout="vertical" margin={{ left: 4, right: 44, top: 4, bottom: 4 }} barCategoryGap={6}>
              <CartesianGrid {...GRID} horizontal={false} vertical />
              <XAxis type="number" domain={[0, 1]} {...AXIS} />
              <YAxis type="category" dataKey="name" width={150} {...AXIS} tick={{ fontSize: 10.5, fill: "#64748b" }} />
              <Tooltip content={<ChartTooltip formatter={(v) => (Number.isFinite(v) ? v.toFixed(3) : "—")} />} cursor={{ fill: "#f1f5f9" }} />
              <Bar dataKey="prAuc" name="PR-AUC" radius={[0, 4, 4, 0]} barSize={14}>
                {chart.map((d) => <Cell key={d.name} fill={d.hi ? CHART.primary : CHART.teal} />)}
                <LabelList dataKey="prAuc" position="right" formatter={(v) => (Number.isFinite(v) ? v.toFixed(3) : "")} style={{ fontSize: 10.5, fill: "#334155", fontWeight: 600 }} />
              </Bar>
            </BarChart>
          </ChartBox>
        </div>
      </div>
    </Card>
  );
}

export default function Ablation() {
  return (
    <ResultSection name="ablation" hint="stage: ablation">
      {(data) => (
        <>
          <Callout tone="info" title="Which parts matter?">
            Two ablations: (1) the feature set given to the same XGBoost — raw transaction fields only, plus behavioural card-history features, plus the protected attributes we deliberately
            exclude from deployment; (2) which detectors the stacking meta-learner combines. Δ columns are paired-bootstrap differences on the same test transactions.
          </Callout>
          {data.feature_sets && (
            <Block
              title="Feature sets (XGBoost)"
              subtitle="Behavioural features are the biggest single win; age and gender add little and are excluded for fairness"
              rows={data.feature_sets}
              order={FS_ORDER}
              labelOf={(k) => ({ raw: "Raw fields", deployed: "+ behavioural (deployed)", all: "+ age & gender" }[k] || k)}
              refKey="deployed"
              vsKey="vs_deployed"
              highlight="deployed"
              extraCol={{ label: "# features", get: (r) => r.n_features }}
            />
          )}
          {data.components && (
            <Block
              title="Hybrid components (stacked)"
              subtitle="Each combination is stacked with the same logistic-regression meta-learner on validation data"
              rows={data.components}
              order={COMP_ORDER}
              labelOf={(k) => COMP_LABEL[k] || k}
              refKey="XGB"
              vsKey="vs_xgb"
              highlight="xgb+rf+iforest"
            />
          )}
        </>
      )}
    </ResultSection>
  );
}
