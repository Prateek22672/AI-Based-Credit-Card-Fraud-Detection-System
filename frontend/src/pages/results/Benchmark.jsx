import { Bar, BarChart, CartesianGrid, Cell, ErrorBar, LabelList, Tooltip, XAxis, YAxis } from "recharts";
import Card from "../../components/ui/Card.jsx";
import Callout from "../../components/ui/Callout.jsx";
import { AXIS, ChartBox, ChartTooltip, GRID } from "../../components/charts/ChartBits.jsx";
import { int, isNum, money, ms, secs } from "../../lib/format.js";
import { CHART } from "../../lib/risk.js";
import { Delta, P, Pc, ResultSection, SHORT, sortModels, useResult } from "./shared.jsx";

export default function Benchmark() {
  const analysis = useResult("analysis");
  const ci = analysis.data?.pr_auc_ci || {};
  const vs = analysis.data?.hybrid_vs || {};

  return (
    <ResultSection name="benchmark_sparkov" hint="stage: benchmark">
      {(data) => {
        const keys = sortModels(Object.keys(data).filter((k) => !k.startsWith("_") && data[k]?.test));
        const rows = keys.map((k) => ({ key: k, ...data[k] }));
        const chart = rows.map((r) => ({
          name: SHORT[r.key] || r.label,
          prAuc: r.test.pr_auc,
          err: ci[r.key] ? [r.test.pr_auc - ci[r.key].low, ci[r.key].high - r.test.pr_auc] : undefined,
          color: r.key === "hybrid" ? CHART.primary : r.key === "rules" ? CHART.slate : CHART.teal,
        }));
        const hybrid = data.hybrid;
        return (
          <>
            {hybrid ? (
              <Callout tone="tip" title={`FraudLens hybrid: PR-AUC ${P(hybrid.test.pr_auc)} · recall ${Pc(hybrid.test.recall)} at ${Pc(hybrid.test.precision)} precision · ${Pc(hybrid.test.savings_pct, 0)} of fraud losses avoided`}>
                Thresholds learned on validation data: alert at p ≥ {P(hybrid.thresholds?.alert, 4)}, block at p ≥ {P(hybrid.thresholds?.block, 4)}.
                {hybrid.meta_weights && ` Meta-learner weights: XGB ${P(hybrid.meta_weights.xgb, 2)}, RF ${P(hybrid.meta_weights.rf, 2)}, IF ${P(hybrid.meta_weights.iforest, 2)}.`}
                {isNum(hybrid.model_size_mb) && ` Engine size ${hybrid.model_size_mb.toFixed(1)} MB.`}
              </Callout>
            ) : (
              <Callout tone="warn">The hybrid row has not been written yet; the table shows the models finished so far.</Callout>
            )}

            <Card title="All models on the unseen test quarter" subtitle="Same chronological split · threshold = best F1 on validation · 95% bootstrap CI on PR-AUC when available" noPad>
              <div className="table-wrap rounded-t-none border-x-0 border-b-0">
                <table className="table">
                  <thead>
                    <tr>
                      <th>Model</th><th className="num">PR-AUC</th><th className="num">95% CI</th><th className="num">ROC-AUC</th><th className="num">Precision</th><th className="num">Recall</th><th className="num">F1</th><th className="num">MCC</th><th className="num">$ caught</th><th className="num">Δ vs hybrid</th><th className="num">Fit</th><th className="num">Latency p50</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((r) => (
                      <tr key={r.key} className={r.key === "hybrid" ? "row-highlight" : ""}>
                        <td className="whitespace-normal">{r.label}</td>
                        <td className="num font-semibold">{P(r.test.pr_auc)}</td>
                        <td className="num text-muted">{ci[r.key] ? `${P(ci[r.key].low)}–${P(ci[r.key].high)}` : "—"}</td>
                        <td className="num">{P(r.test.roc_auc, 4)}</td>
                        <td className="num">{Pc(r.test.precision)}</td>
                        <td className="num">{Pc(r.test.recall)}</td>
                        <td className="num">{P(r.test.f1)}</td>
                        <td className="num">{P(r.test.mcc)}</td>
                        <td className="num">{Pc(r.test.amount_recall)}</td>
                        <td className="num">{r.key === "hybrid" ? <span className="text-muted">ref.</span> : vs[r.key] ? <Delta {...vs[r.key]} /> : "—"}</td>
                        <td className="num text-muted">{secs(r.fit_seconds)}</td>
                        <td className="num">{r.latency ? ms(r.latency.p50_ms, 2) : "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="px-5 py-3 text-[11.5px] text-muted">Δ vs hybrid = hybrid PR-AUC minus this model's, paired bootstrap on the same test transactions (sig. = p &lt; 0.05). Latency is per single transaction, single-threaded.</p>
            </Card>

            <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
              <Card title="PR-AUC by model" subtitle="Whiskers show the 95% bootstrap confidence interval when computed">
                <ChartBox height={Math.max(220, chart.length * 30)}>
                  <BarChart data={chart} layout="vertical" margin={{ left: 4, right: 48, top: 4, bottom: 4 }} barCategoryGap={6}>
                    <CartesianGrid {...GRID} horizontal={false} vertical />
                    <XAxis type="number" domain={[0, 1]} {...AXIS} />
                    <YAxis type="category" dataKey="name" width={110} {...AXIS} />
                    <Tooltip content={<ChartTooltip formatter={(v) => v.toFixed(3)} />} cursor={{ fill: "#f1f5f9" }} />
                    <Bar dataKey="prAuc" name="PR-AUC" radius={[0, 4, 4, 0]} barSize={16}>
                      {chart.map((d) => <Cell key={d.name} fill={d.color} />)}
                      <ErrorBar dataKey="err" width={4} strokeWidth={1.5} stroke="#0f172a" direction="x" />
                      <LabelList dataKey="prAuc" position="right" formatter={(v) => v.toFixed(3)} style={{ fontSize: 11, fill: "#334155", fontWeight: 600 }} />
                    </Bar>
                  </BarChart>
                </ChartBox>
              </Card>
              <Card title="Money view at the cost-optimal threshold" subtitle="Threshold chosen to minimise missed-fraud dollars + $5 per alert (on validation)" noPad>
                <div className="table-wrap rounded-t-none border-x-0 border-b-0">
                  <table className="table">
                    <thead><tr><th>Model</th><th className="num">Recall</th><th className="num">Precision</th><th className="num">Alerts</th><th className="num">Fraud $ caught</th><th className="num">Savings</th></tr></thead>
                    <tbody>
                      {rows.filter((r) => r.test_cost_threshold).map((r) => {
                        const c = r.test_cost_threshold;
                        return (
                          <tr key={r.key} className={r.key === "hybrid" ? "row-highlight" : ""}>
                            <td>{SHORT[r.key] || r.label}</td>
                            <td className="num">{Pc(c.recall)}</td>
                            <td className="num">{Pc(c.precision)}</td>
                            <td className="num">{int((c.tp || 0) + (c.fp || 0))}</td>
                            <td className="num">{money(c.fraud_amount_caught, { compact: true })} <span className="text-muted">({Pc(c.amount_recall, 0)})</span></td>
                            <td className="num">{Pc(c.savings_pct)}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </Card>
            </div>
          </>
        );
      }}
    </ResultSection>
  );
}
