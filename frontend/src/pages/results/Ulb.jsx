import { Bar, BarChart, CartesianGrid, Cell, ErrorBar, LabelList, Tooltip, XAxis, YAxis } from "recharts";
import Card from "../../components/ui/Card.jsx";
import Callout from "../../components/ui/Callout.jsx";
import { AXIS, ChartBox, ChartTooltip, GRID } from "../../components/charts/ChartBits.jsx";
import { int, secs } from "../../lib/format.js";
import { CHART } from "../../lib/risk.js";
import { Delta, P, Pc, ResultSection, SHORT, sortModels } from "./shared.jsx";

export default function Ulb() {
  return (
    <ResultSection name="benchmark_ulb" hint="stage: ulb">
      {(data) => {
        const ds = data._dataset;
        const pair = data._pairwise_vs_hybrid || {};
        const keys = sortModels(Object.keys(data).filter((k) => !k.startsWith("_") && data[k]?.test));
        const chart = keys.map((k) => {
          const t = data[k].test;
          const ci = Array.isArray(t.pr_auc_ci) ? t.pr_auc_ci : null;
          return { name: SHORT[k] || data[k].label, prAuc: t.pr_auc, err: ci ? [t.pr_auc - ci[0], ci[1] - t.pr_auc] : undefined, hi: k === "hybrid" };
        });
        return (
          <>
            <Callout tone="info" title="Second dataset: European cardholders (ULB / Kaggle)">
              {ds ? `${int(ds.rows)} transactions over two days, ${int(ds.frauds)} frauds (${Pc(ds.fraud_rate, 3)}), PCA-anonymised features V1–V28 + amount + time, split 60/20/20 in time order.` : "Anonymised PCA features, split in time order."}{" "}
              No card identifiers exist, so the behavioural feature store cannot be used: this tests the modelling recipe alone, on a different distribution.
            </Callout>
            <Card title="ULB benchmark" subtitle="Threshold = best F1 on validation · 95% bootstrap CI on PR-AUC · Δ = hybrid minus model (paired bootstrap)" noPad>
              <div className="table-wrap rounded-t-none border-x-0 border-b-0">
                <table className="table">
                  <thead><tr><th>Model</th><th className="num">PR-AUC</th><th className="num">95% CI</th><th className="num">ROC-AUC</th><th className="num">Precision</th><th className="num">Recall</th><th className="num">F1</th><th className="num">MCC</th><th className="num">Δ vs hybrid</th><th className="num">Fit</th></tr></thead>
                  <tbody>
                    {keys.map((k) => {
                      const t = data[k].test;
                      const ci = Array.isArray(t.pr_auc_ci) ? t.pr_auc_ci : null;
                      return (
                        <tr key={k} className={k === "hybrid" ? "row-highlight" : ""}>
                          <td className="whitespace-normal">{data[k].label}</td>
                          <td className="num font-semibold">{P(t.pr_auc)}</td>
                          <td className="num text-muted">{ci ? `${P(ci[0])}–${P(ci[1])}` : "—"}</td>
                          <td className="num">{P(t.roc_auc, 4)}</td>
                          <td className="num">{Pc(t.precision)}</td>
                          <td className="num">{Pc(t.recall)}</td>
                          <td className="num">{P(t.f1)}</td>
                          <td className="num">{P(t.mcc)}</td>
                          <td className="num">{k === "hybrid" ? <span className="text-muted">ref.</span> : pair[k] ? <Delta {...pair[k]} /> : "—"}</td>
                          <td className="num text-muted">{secs(data[k].fit_seconds)}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </Card>
            <Card title="PR-AUC on ULB" subtitle="Whiskers: 95% bootstrap CI">
              <ChartBox height={Math.max(200, chart.length * 30)}>
                <BarChart data={chart} layout="vertical" margin={{ left: 4, right: 48, top: 4, bottom: 4 }} barCategoryGap={6}>
                  <CartesianGrid {...GRID} horizontal={false} vertical />
                  <XAxis type="number" domain={[0, 1]} {...AXIS} />
                  <YAxis type="category" dataKey="name" width={110} {...AXIS} />
                  <Tooltip content={<ChartTooltip formatter={(v) => v.toFixed(3)} />} cursor={{ fill: "#f1f5f9" }} />
                  <Bar dataKey="prAuc" name="PR-AUC" radius={[0, 4, 4, 0]} barSize={16}>
                    {chart.map((d) => <Cell key={d.name} fill={d.hi ? CHART.primary : CHART.teal} />)}
                    <ErrorBar dataKey="err" width={4} strokeWidth={1.5} stroke="#0f172a" direction="x" />
                    <LabelList dataKey="prAuc" position="right" formatter={(v) => v.toFixed(3)} style={{ fontSize: 11, fill: "#334155", fontWeight: 600 }} />
                  </Bar>
                </BarChart>
              </ChartBox>
            </Card>
          </>
        );
      }}
    </ResultSection>
  );
}
