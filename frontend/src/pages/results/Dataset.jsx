import { Bar, BarChart, CartesianGrid, Cell, Tooltip, XAxis, YAxis } from "recharts";
import { CalendarRange, CreditCard, Percent, Store } from "lucide-react";
import Card from "../../components/ui/Card.jsx";
import KpiTile, { KpiGrid } from "../../components/ui/KpiTile.jsx";
import { AXIS, ChartBox, ChartTooltip, GRID } from "../../components/charts/ChartBits.jsx";
import { fmtDate, int, isNum, money, pct, titleCase } from "../../lib/format.js";
import { CHART } from "../../lib/risk.js";
import { ResultSection } from "./shared.jsx";

export default function Dataset() {
  return (
    <ResultSection name="dataset_sparkov" hint="stage: features">
      {(d) => {
        const byHour = Object.entries(d.fraud_by_hour || {}).map(([h, v]) => ({ hour: `${String(h).padStart(2, "0")}h`, rate: v, night: Number(h) >= 22 || Number(h) < 4 }));
        const byCat = Object.entries(d.fraud_by_category || {}).map(([k, v]) => ({ name: titleCase(k), rate: v.mean, n: v.size, frauds: v.sum })).sort((a, b) => b.rate - a.rate);
        const splits = d.splits || {};
        const amt = d.amount_by_class || {};
        return (
          <>
            <KpiGrid cols={4}>
              <KpiTile label="Transactions" value={int(d.rows)} sub={`${int(d.frauds)} frauds (${pct(d.fraud_rate, 2)})`} icon={Percent} tone="indigo" />
              <KpiTile label="Cards" value={int(d.cards)} sub={`${int(d.compromised_cards)} compromised · ${isNum(d.frauds_per_compromised_card) ? d.frauds_per_compromised_card.toFixed(1) : "—"} frauds each`} icon={CreditCard} tone="violet" />
              <KpiTile label="Merchants" value={int(d.merchants)} sub={`${d.n_features_deployed ?? "—"} deployed features of ${d.n_features_all ?? "—"}`} icon={Store} tone="teal" />
              <KpiTile label="Period" value={`${fmtDate(d.start)} →`} sub={`${fmtDate(d.end)} · features built at ${isNum(d.microseconds_per_txn) ? d.microseconds_per_txn.toFixed(0) : "—"} µs/txn`} icon={CalendarRange} tone="amber" />
            </KpiGrid>
            <Card title="Chronological split with a 7-day label-delay gap" subtitle="Train on 2019, validate on Q1 2020, test on the unseen Q2 2020" noPad>
              <div className="table-wrap rounded-t-none border-x-0 border-b-0">
                <table className="table">
                  <thead><tr><th>Split</th><th>From</th><th>To</th><th className="num">Transactions</th><th className="num">Frauds</th><th className="num">Fraud rate</th></tr></thead>
                  <tbody>
                    {["train", "gap", "val", "test"].filter((s) => splits[s]).map((s) => (
                      <tr key={s} className={s === "test" ? "row-highlight" : s === "gap" ? "text-muted" : ""}>
                        <td className="font-medium">{{ train: "Training", gap: "Gap (labels not yet known)", val: "Validation", test: "Test (replayed by the live monitor)" }[s]}</td>
                        <td className="font-mono text-[12px]">{fmtDate(splits[s].start)}</td>
                        <td className="font-mono text-[12px]">{fmtDate(splits[s].end)}</td>
                        <td className="num">{int(splits[s].rows)}</td>
                        <td className="num">{int(splits[s].frauds)}</td>
                        <td className="num">{pct(splits[s].frauds / Math.max(splits[s].rows, 1), 2)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
            <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
              <Card title="Fraud rate by hour of day" subtitle="Night hours (22:00–04:00) highlighted: fraud is ~10× more likely">
                <ChartBox height={220}>
                  <BarChart data={byHour} margin={{ left: -8, right: 8, top: 8, bottom: 0 }} barCategoryGap={2}>
                    <CartesianGrid {...GRID} />
                    <XAxis dataKey="hour" {...AXIS} interval={2} />
                    <YAxis {...AXIS} tickFormatter={(v) => `${(v * 100).toFixed(1)}%`} />
                    <Tooltip content={<ChartTooltip formatter={(v) => pct(v, 2)} />} cursor={{ fill: "#f1f5f9" }} />
                    <Bar dataKey="rate" name="Fraud rate" radius={[3, 3, 0, 0]}>
                      {byHour.map((h) => <Cell key={h.hour} fill={h.night ? CHART.red : CHART.primary} />)}
                    </Bar>
                  </BarChart>
                </ChartBox>
              </Card>
              <Card title="Fraud rate by merchant category" subtitle="Online shopping and online miscellaneous carry the most risk">
                <ChartBox height={Math.max(220, byCat.length * 18)}>
                  <BarChart data={byCat} layout="vertical" margin={{ left: 4, right: 30, top: 0, bottom: 0 }} barCategoryGap={3}>
                    <CartesianGrid {...GRID} horizontal={false} vertical />
                    <XAxis type="number" {...AXIS} tickFormatter={(v) => `${(v * 100).toFixed(1)}%`} />
                    <YAxis type="category" dataKey="name" width={140} {...AXIS} tick={{ fontSize: 10.5, fill: "#64748b" }} />
                    <Tooltip content={<ChartTooltip formatter={(v, n, p) => (n === "Fraud rate" ? `${pct(v, 2)} (${int(p.payload.frauds)} of ${int(p.payload.n)})` : v)} />} cursor={{ fill: "#f1f5f9" }} />
                    <Bar dataKey="rate" name="Fraud rate" fill={CHART.teal} radius={[0, 3, 3, 0]} barSize={11} />
                  </BarChart>
                </ChartBox>
              </Card>
            </div>
            {amt["0"] && amt["1"] && (
              <Card title="Transaction amounts by class" subtitle="Fraudulent purchases are much larger and less dispersed in the low range" noPad>
                <div className="table-wrap rounded-t-none border-x-0 border-b-0">
                  <table className="table">
                    <thead><tr><th>Class</th><th className="num">Count</th><th className="num">Mean</th><th className="num">Std</th><th className="num">25%</th><th className="num">Median</th><th className="num">75%</th><th className="num">Max</th></tr></thead>
                    <tbody>
                      {[["0", "Genuine"], ["1", "Fraud"]].map(([k, l]) => (
                        <tr key={k}><td className="font-medium">{l}</td><td className="num">{int(amt[k].count)}</td><td className="num">{money(amt[k].mean)}</td><td className="num">{money(amt[k].std)}</td><td className="num">{money(amt[k]["25%"])}</td><td className="num">{money(amt[k]["50%"])}</td><td className="num">{money(amt[k]["75%"])}</td><td className="num">{money(amt[k].max)}</td></tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Card>
            )}
          </>
        );
      }}
    </ResultSection>
  );
}
