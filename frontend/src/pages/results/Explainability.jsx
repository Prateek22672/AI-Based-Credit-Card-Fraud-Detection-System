import { AlertCircle, CheckCircle2 } from "lucide-react";
import { Bar, BarChart, CartesianGrid, LabelList, Tooltip, XAxis, YAxis } from "recharts";
import Card from "../../components/ui/Card.jsx";
import Callout from "../../components/ui/Callout.jsx";
import { AXIS, ChartBox, ChartTooltip, GRID } from "../../components/charts/ChartBits.jsx";
import { fmtDateTime, money, pct, titleCase } from "../../lib/format.js";
import { CHART, RISK, riskOf } from "../../lib/risk.js";
import { RiskChip, TruthTag } from "../../components/ui/Badge.jsx";
import { ResultSection } from "./shared.jsx";

export default function Explainability() {
  return (
    <ResultSection name="explain" hint="stage: explain">
      {(data) => {
        const imp = (data.global_importance || []).slice(0, 20).map((g) => ({ name: g.label || g.feature, v: g.mean_abs_shap }));
        const cases = data.cases || [];
        return (
          <>
            <Callout tone="info" title="Explainability">
              Global importance is the mean absolute TreeSHAP value over all test frauds plus a random sample of genuine transactions. Case studies show the same reason codes the
              API returns live: each is a real transaction from the unseen test quarter.
            </Callout>
            <Card title="Global feature importance (mean |SHAP|)" subtitle="Top 20 features of the XGBoost component, in log-odds units">
              <ChartBox height={Math.max(300, imp.length * 24)}>
                <BarChart data={imp} layout="vertical" margin={{ left: 4, right: 48, top: 4, bottom: 4 }} barCategoryGap={4}>
                  <CartesianGrid {...GRID} horizontal={false} vertical />
                  <XAxis type="number" {...AXIS} />
                  <YAxis type="category" dataKey="name" width={210} {...AXIS} tick={{ fontSize: 11, fill: "#334155" }} />
                  <Tooltip content={<ChartTooltip formatter={(v) => v.toFixed(3)} />} cursor={{ fill: "#f1f5f9" }} />
                  <Bar dataKey="v" name="mean |SHAP|" fill={CHART.primary} radius={[0, 4, 4, 0]} barSize={13}>
                    <LabelList dataKey="v" position="right" formatter={(v) => v.toFixed(2)} style={{ fontSize: 10.5, fill: "#334155" }} />
                  </Bar>
                </BarChart>
              </ChartBox>
            </Card>
            <div>
              <h2 className="mb-3 text-[16px] font-semibold">Case studies</h2>
              <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
                {cases.map((c, i) => {
                  const r = riskOf(c.tier);
                  return (
                    <div key={i} className="card p-4">
                      <div className="flex flex-wrap items-start justify-between gap-2">
                        <div>
                          <div className="text-[11px] font-semibold uppercase tracking-wide" style={{ color: r.ink }}>{c.kind}</div>
                          <div className="mt-0.5 text-[14px] font-semibold">{money(c.amount)} · {titleCase(c.category)}</div>
                          <div className="text-[12px] text-muted">{c.merchant} · {fmtDateTime(c.ts)}</div>
                        </div>
                        <div className="flex flex-col items-end gap-1">
                          <RiskChip score={c.risk_score} level={c.tier} />
                          <TruthTag label={c.is_fraud} />
                        </div>
                      </div>
                      <div className="mt-3 grid grid-cols-4 gap-2 text-center text-[11px]">
                        <div className="rounded-lg bg-slate-50 p-2"><div className="text-muted">Probability</div><div className="font-bold" style={{ color: r.color }}>{pct(c.probability, 1)}</div></div>
                        <div className="rounded-lg bg-slate-50 p-2"><div className="text-muted">XGBoost</div><div className="font-bold">{pct(c.components?.xgb, 0)}</div></div>
                        <div className="rounded-lg bg-slate-50 p-2"><div className="text-muted">Random Forest</div><div className="font-bold">{pct(c.components?.rf, 0)}</div></div>
                        <div className="rounded-lg bg-slate-50 p-2"><div className="text-muted">Anomaly pct.</div><div className="font-bold">{pct(c.components?.anomaly_percentile, 0)}</div></div>
                      </div>
                      {(c.reasons?.length > 0 || c.mitigating?.length > 0) && (
                        <div className="mt-3 space-y-1.5">
                          {(c.reasons || []).map((t, j) => <div key={`r${j}`} className="flex gap-2 text-[12.5px] text-ink-2"><AlertCircle size={14} className="mt-0.5 shrink-0" style={{ color: RISK.HIGH.color }} />{t}</div>)}
                          {(c.mitigating || []).map((t, j) => <div key={`m${j}`} className="flex gap-2 text-[12.5px] text-ink-2"><CheckCircle2 size={14} className="mt-0.5 shrink-0" style={{ color: RISK.LOW.color }} />{t}</div>)}
                        </div>
                      )}
                      {c.top_groups?.length > 0 && (
                        <div className="mt-3 flex flex-wrap gap-1.5">
                          {c.top_groups.map((g) => (
                            <span key={g.group} className="rounded-md px-1.5 py-0.5 text-[10.5px] font-semibold" style={{ backgroundColor: g.shap >= 0 ? RISK.HIGH.soft : RISK.LOW.soft, color: g.shap >= 0 ? RISK.HIGH.ink : RISK.LOW.ink }}>
                              {g.label} {g.shap >= 0 ? "+" : ""}{Number(g.shap).toFixed(2)}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          </>
        );
      }}
    </ResultSection>
  );
}
