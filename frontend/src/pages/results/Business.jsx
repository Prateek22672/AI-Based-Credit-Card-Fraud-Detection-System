import { Bar, BarChart, CartesianGrid, Cell, Line, LineChart, Tooltip, XAxis, YAxis } from "recharts";
import Card from "../../components/ui/Card.jsx";
import Callout from "../../components/ui/Callout.jsx";
import KpiTile, { KpiGrid } from "../../components/ui/KpiTile.jsx";
import { AXIS, ChartBox, ChartTooltip, GRID, LegendDots } from "../../components/charts/ChartBits.jsx";
import { int, isNum, money, num } from "../../lib/format.js";
import { CHART, RISK } from "../../lib/risk.js";
import { P, Pc, ResultSection } from "./shared.jsx";
import { Activity, CalendarRange, DollarSign, Gauge } from "lucide-react";

export default function Business() {
  return (
    <ResultSection name="analysis" hint="stage: analysis">
      {(data) => {
        const cost = data.cost_sensitivity || [];
        const tiers = data.tiers || {};
        const thr = data.tiers_thresholds || {};
        const monthly = Object.entries(data.monthly || {}).map(([m, v]) => ({ month: m, ...v }));
        const psi = data.psi_val_to_test;
        const base = cost.find((c) => c.alert_cost === 5) || cost[0];
        const tierRows = ["LOW", "MEDIUM", "HIGH"].filter((t) => tiers[t]).map((t) => ({ tier: t, ...tiers[t] }));
        return (
          <>
            <KpiGrid cols={4}>
              <KpiTile label="Fraud losses avoided" value={base ? Pc(base.savings_pct, 1) : "—"} sub={base ? `${money(base.fraud_amount_caught, { compact: true })} of ${money(base.fraud_amount_total, { compact: true })} caught at $${base.alert_cost}/alert` : "cost-optimal threshold"} icon={DollarSign} tone="teal" />
              <KpiTile label="Alerts per day" value={base ? num(base.alerts_per_day, 1) : "—"} sub={base ? `${Pc(base.precision)} precise · ${Pc(base.recall)} recall` : "analyst workload"} icon={Activity} tone="indigo" />
              <KpiTile label="Test period" value={isNum(data.test_days) ? `${Math.round(data.test_days)} days` : "—"} sub="unseen quarter, chronological" icon={CalendarRange} tone="violet" />
              <KpiTile label="PSI (val → test)" value={isNum(psi) ? psi.toFixed(4) : "—"} sub={isNum(psi) ? (psi < 0.1 ? "no meaningful score drift" : psi < 0.25 ? "moderate drift: monitor" : "significant drift: retrain") : "population stability index"} icon={Gauge} tone={isNum(psi) && psi >= 0.25 ? "red" : isNum(psi) && psi >= 0.1 ? "amber" : "green"} />
            </KpiGrid>

            <Card title="Cost sensitivity" subtitle="How the optimal operating point moves with the assumed cost of one alert (analyst review / OTP friction)" noPad>
              <div className="table-wrap rounded-t-none border-x-0 border-b-0">
                <table className="table">
                  <thead><tr><th className="num">Alert cost</th><th className="num">Threshold</th><th className="num">Precision</th><th className="num">Recall</th><th className="num">F1</th><th className="num">Alerts / day</th><th className="num">False alarms</th><th className="num">Fraud $ caught</th><th className="num">Net cost</th><th className="num">Savings</th></tr></thead>
                  <tbody>
                    {cost.map((c) => (
                      <tr key={c.alert_cost} className={c.alert_cost === 5 ? "row-highlight" : ""}>
                        <td className="num">${c.alert_cost}</td>
                        <td className="num">{P(c.threshold, 4)}</td>
                        <td className="num">{Pc(c.precision)}</td>
                        <td className="num">{Pc(c.recall)}</td>
                        <td className="num">{P(c.f1)}</td>
                        <td className="num">{num(c.alerts_per_day, 1)}</td>
                        <td className="num">{int(c.fp)}</td>
                        <td className="num">{money(c.fraud_amount_caught, { compact: true })} <span className="text-muted">({Pc(c.amount_recall, 0)})</span></td>
                        <td className="num">{money(c.cost, { compact: true })}</td>
                        <td className="num font-semibold">{Pc(c.savings_pct)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="px-5 py-3 text-[11.5px] text-muted">Net cost = missed-fraud dollars + alert cost × alerts. The $5 base case is the deployed alert threshold.</p>
            </Card>

            <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
              <Card title="Risk tiers on the test quarter" subtitle={`Alert at p ≥ ${P(thr.alert, 4)} (score ${thr.risk_band_medium ?? 30}) · block at p ≥ ${P(thr.block, 4)} (score ${thr.risk_band_high ?? 60})`} noPad>
                <div className="table-wrap rounded-t-none border-x-0 border-b-0">
                  <table className="table">
                    <thead><tr><th>Tier</th><th className="num">Transactions</th><th className="num">Share</th><th className="num">Per day</th><th className="num">Frauds</th><th className="num">Fraud rate</th><th className="num">Fraud $</th></tr></thead>
                    <tbody>
                      {tierRows.map((t) => (
                        <tr key={t.tier}>
                          <td><span className="pill" style={{ backgroundColor: RISK[t.tier].soft, color: RISK[t.tier].ink }}><span className="h-2 w-2 rounded-full" style={{ backgroundColor: RISK[t.tier].color }} />{RISK[t.tier].label}</span></td>
                          <td className="num">{int(t.transactions)}</td>
                          <td className="num">{Pc(t.share, 2)}</td>
                          <td className="num">{num(t.per_day, 1)}</td>
                          <td className="num">{int(t.frauds)}</td>
                          <td className="num font-semibold">{Pc(t.fraud_rate)}</td>
                          <td className="num">{money(t.fraud_amount, { compact: true })}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div className="px-5 pb-5 pt-3">
                  <ChartBox height={150}>
                    <BarChart data={tierRows} layout="vertical" margin={{ left: 4, right: 40, top: 0, bottom: 0 }} barCategoryGap={8}>
                      <CartesianGrid {...GRID} horizontal={false} vertical />
                      <XAxis type="number" domain={[0, 1]} {...AXIS} tickFormatter={(v) => `${(v * 100).toFixed(0)}%`} />
                      <YAxis type="category" dataKey="tier" width={70} {...AXIS} />
                      <Tooltip content={<ChartTooltip formatter={(v) => Pc(v)} />} cursor={{ fill: "#f1f5f9" }} />
                      <Bar dataKey="fraud_rate" name="Fraud rate" radius={[0, 4, 4, 0]} barSize={18}>
                        {tierRows.map((t) => <Cell key={t.tier} fill={RISK[t.tier].color} />)}
                      </Bar>
                    </BarChart>
                  </ChartBox>
                </div>
              </Card>

              <Card title="Monthly stability" subtitle="Does performance hold over the test quarter? (alert threshold fixed)" noPad>
                <div className="table-wrap rounded-t-none border-x-0 border-b-0">
                  <table className="table">
                    <thead><tr><th>Month</th><th className="num">Transactions</th><th className="num">Frauds</th><th className="num">PR-AUC</th><th className="num">Precision</th><th className="num">Recall</th><th className="num">F1</th></tr></thead>
                    <tbody>
                      {monthly.map((m) => (
                        <tr key={m.month}>
                          <td className="font-mono">{m.month}</td>
                          <td className="num">{int(m.transactions)}</td>
                          <td className="num">{int(m.frauds)}</td>
                          <td className="num font-semibold">{P(m.pr_auc)}</td>
                          <td className="num">{Pc(m.precision)}</td>
                          <td className="num">{Pc(m.recall)}</td>
                          <td className="num">{P(m.f1)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {monthly.length > 1 && (
                  <div className="px-5 pb-5 pt-3">
                    <ChartBox height={150}>
                      <LineChart data={monthly} margin={{ left: -8, right: 12, top: 8, bottom: 0 }}>
                        <CartesianGrid {...GRID} />
                        <XAxis dataKey="month" {...AXIS} />
                        <YAxis domain={[0, 1]} {...AXIS} />
                        <Tooltip content={<ChartTooltip formatter={(v) => (isNum(v) ? v.toFixed(3) : "—")} />} />
                        <Line type="monotone" dataKey="pr_auc" name="PR-AUC" stroke={CHART.primary} strokeWidth={2} dot={{ r: 4 }} />
                        <Line type="monotone" dataKey="recall" name="Recall" stroke={CHART.teal} strokeWidth={2} dot={{ r: 4 }} />
                        <Line type="monotone" dataKey="precision" name="Precision" stroke={CHART.amber} strokeWidth={2} dot={{ r: 4 }} />
                      </LineChart>
                    </ChartBox>
                    <LegendDots items={[{ label: "PR-AUC", color: CHART.primary }, { label: "Recall", color: CHART.teal }, { label: "Precision", color: CHART.amber }]} />
                  </div>
                )}
              </Card>
            </div>

            {data.hybrid_vs && (
              <Callout tone="tip" title="Statistical significance">
                Paired bootstrap of PR-AUC on the same test transactions, hybrid minus each model:{" "}
                {Object.entries(data.hybrid_vs).map(([k, v], i, arr) => (
                  <span key={k}>
                    {k}: {v.diff > 0 ? "+" : ""}{num(v.diff, 3)} [{num(v.ci_low, 3)}, {num(v.ci_high, 3)}], p = {v.p_value?.toFixed(3)}{i < arr.length - 1 ? "; " : "."}
                  </span>
                ))}
              </Callout>
            )}
          </>
        );
      }}
    </ResultSection>
  );
}
