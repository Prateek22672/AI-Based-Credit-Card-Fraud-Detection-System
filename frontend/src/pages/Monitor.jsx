import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Activity, AlertTriangle, CheckCheck, DollarSign, Pause, Play, RotateCcw, ShieldBan, Target, Timer, Wifi } from "lucide-react";
import { Bar, BarChart, CartesianGrid, Cell, Line, LineChart, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../lib/api.js";
import { useApiStatus } from "../context/ApiStatus.jsx";
import { fmtDateTime, fmtTime, int, last4, money, ms, pct, titleCase } from "../lib/format.js";
import { CHART, RISK, levelFromScore } from "../lib/risk.js";
import KpiTile, { KpiGrid } from "../components/ui/KpiTile.jsx";
import Card from "../components/ui/Card.jsx";
import { DecisionBadge, RiskChip, TruthTag } from "../components/ui/Badge.jsx";
import Drawer from "../components/ui/Drawer.jsx";
import { EmptyState, OfflineState } from "../components/ui/EmptyState.jsx";
import ExplanationPanel from "../components/explain/ExplanationPanel.jsx";
import { AXIS, ChartBox, ChartTooltip, GRID, LegendDots } from "../components/charts/ChartBits.jsx";
import Callout from "../components/ui/Callout.jsx";
import { Spinner } from "../components/ui/Spinner.jsx";

const SPEEDS = [10, 25, 50, 100];
const TICK_MS = 1200;
const MAX_ROWS = 200;

export default function Monitor() {
  const { online, setStream, markOffline } = useApiStatus();
  const [params, setParams] = useSearchParams();
  const feed = params.get("feed") === "alerts" ? "alerts" : "all"; // ?feed=alerts shows only medium/high
  const [running, setRunning] = useState(false);
  const [speed, setSpeed] = useState(25);
  const [rows, setRows] = useState([]);
  const [alertRows, setAlertRows] = useState([]);
  const [stats, setStats] = useState(null);
  const [selected, setSelected] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const [finished, setFinished] = useState(false);
  const inFlight = useRef(false);
  const speedRef = useRef(speed);
  speedRef.current = speed;

  const loadStats = useCallback(async () => {
    const s = await api.stats();
    setStats(s);
    setStream(s.stream);
    return s;
  }, [setStream]);

  // Hydrate from the server-side decision log so a reload keeps the feed.
  useEffect(() => {
    if (online !== true) return;
    let alive = true;
    (async () => {
      try {
        const [s, tx, al] = await Promise.all([
          loadStats(),
          api.transactions({ source: "stream", limit: MAX_ROWS }),
          api.transactions({ source: "stream", level: "MEDIUM,HIGH", limit: MAX_ROWS }),
        ]);
        if (!alive) return;
        setRows(tx.map((t) => ({ ...t, _summary: true })));
        setAlertRows(al.map((t) => ({ ...t, _summary: true })));
        if (s?.stream && s.stream.stream_position >= s.stream.stream_total) setFinished(true);
        setError(null);
      } catch (e) {
        if (alive) setError(e.message);
      }
    })();
    return () => {
      alive = false;
    };
  }, [online, loadStats]);

  const tick = useCallback(async () => {
    if (inFlight.current) return;
    inFlight.current = true;
    setBusy(true);
    try {
      const res = await api.streamNext(speedRef.current);
      if (!res.length) {
        setFinished(true);
        setRunning(false);
      } else {
        const stamped = res.slice().reverse().map((r) => ({ ...r, _new: true }));
        setRows((prev) => [...stamped, ...prev.map((p) => ({ ...p, _new: false }))].slice(0, MAX_ROWS));
        const fresh = stamped.filter((r) => r.risk_level !== "LOW");
        if (fresh.length) setAlertRows((prev) => [...fresh, ...prev.map((p) => ({ ...p, _new: false }))].slice(0, MAX_ROWS));
      }
      await loadStats();
      setError(null);
    } catch (e) {
      setError(e.message);
      if (e.offline) {
        markOffline();
        setRunning(false);
      }
    } finally {
      inFlight.current = false;
      setBusy(false);
    }
  }, [loadStats, markOffline]);

  useEffect(() => {
    if (!running) return;
    tick();
    const id = setInterval(tick, TICK_MS);
    return () => clearInterval(id);
  }, [running, tick]);

  const reset = async () => {
    setRunning(false);
    setBusy(true);
    try {
      await api.reset();
      setRows([]);
      setAlertRows([]);
      setFinished(false);
      await loadStats();
      setError(null);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  const openRow = async (row) => {
    setSelected(row);
    // approved stream rows are explained on demand by the API (exact TreeSHAP is the costly part)
    if (row.id && (row._summary || row.explained === false)) {
      try {
        const full = await api.transaction(row.id);
        setSelected((cur) => (cur?.id === row.id ? { ...row, ...full } : cur));
      } catch {
        /* keep summary */
      }
    }
  };

  const hist = useMemo(
    () => (stats?.risk_histogram || []).map((h) => ({ ...h, from: Number(h.bucket.split("-")[0]) })),
    [stats],
  );
  const timeline = useMemo(() => (stats?.timeline || []).map((t) => ({ ...t, day: t.day?.slice(5) || t.day, fullDay: t.day })), [stats]);
  const byCat = useMemo(
    () => Object.entries(stats?.alerts_by_category || {}).map(([k, v]) => ({ name: titleCase(k), count: v })).sort((a, b) => b.count - a.count),
    [stats],
  );

  if (online === false) return <OfflineState />;

  const total = stats?.total || 0;
  const s = stats || {};
  const shown = feed === "alerts" ? alertRows : rows;
  const progress = s.stream ? (s.stream.stream_position / Math.max(s.stream.stream_total, 1)) * 100 : 0;

  return (
    <div className="space-y-5">
      {/* controls */}
      <Card noPad>
        <div className="flex flex-col gap-3 px-5 py-4 md:flex-row md:items-center md:justify-between">
          <div className="flex flex-wrap items-center gap-2">
            {running ? (
              <button className="btn-secondary" onClick={() => setRunning(false)}><Pause size={15} /> Pause</button>
            ) : (
              <button className="btn-primary" onClick={() => setRunning(true)} disabled={finished || online !== true}><Play size={15} /> {rows.length ? "Resume" : "Start"} stream</button>
            )}
            <button className="btn-secondary" onClick={reset} disabled={busy && !running}><RotateCcw size={15} /> Reset</button>
            <div className="ml-1 flex items-center gap-1 rounded-xl border border-line bg-slate-50 p-1">
              <span className="px-2 text-[11.5px] font-semibold uppercase tracking-wide text-muted">Speed</span>
              {SPEEDS.map((n) => (
                <button
                  key={n}
                  onClick={() => setSpeed(n)}
                  className={`rounded-lg px-2.5 py-1 text-[12.5px] font-semibold transition ${speed === n ? "bg-white text-primary shadow-sm" : "text-ink-2 hover:bg-white/70"}`}
                >
                  {n}
                </button>
              ))}
              <span className="pr-2 text-[11px] text-muted">txns / 1.2 s</span>
            </div>
          </div>
          <div className="flex items-center gap-3 text-[12px] text-muted">
            <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 font-semibold ${running ? "bg-emerald-50 text-emerald-700" : "bg-slate-100 text-slate-600"}`}>
              {busy ? <Spinner size={12} /> : <Wifi size={13} />}
              {running ? "Streaming" : finished ? "Stream finished" : "Paused"}
            </span>
            {s.stream && (
              <span className="hidden sm:inline">
                {int(s.stream.stream_position)} / {int(s.stream.stream_total)} replayed
              </span>
            )}
          </div>
        </div>
        <div className="h-1 w-full bg-slate-100">
          <div className="h-full bg-gradient-to-r from-primary to-accent transition-all duration-500" style={{ width: `${Math.min(100, progress)}%` }} />
        </div>
      </Card>

      {error && <Callout tone="warn" title="Last request failed">{error}</Callout>}

      <Callout tone="info">
        The stream replays the <strong>held-out test period (8 Apr – 21 Jun 2020)</strong> — transactions the models never saw during
        training or threshold tuning — in their original time order, updating each card&apos;s behavioural profile as it goes. Dataset
        ground-truth labels are never given to the model; they are only used afterwards to measure live precision and recall.
      </Callout>

      {/* KPIs */}
      <KpiGrid cols={4}>
        <KpiTile label="Transactions scored" value={int(total)} sub={s.levels ? `${int(s.levels.LOW || 0)} low · ${int(s.levels.MEDIUM || 0)} medium · ${int(s.levels.HIGH || 0)} high` : "since last reset"} icon={Activity} tone="indigo" />
        <KpiTile label="Alerts raised" value={int(s.alerts)} sub={`${int(s.blocked)} auto-blocked · ${int(s.false_alarms)} false alarms`} icon={AlertTriangle} tone="amber" />
        <KpiTile label="Frauds caught / seen" value={total ? `${int(s.frauds_caught)} / ${int(s.frauds_seen)}` : "—"} sub={`${int(s.frauds_blocked)} blocked outright · ${int(s.frauds_missed)} missed`} icon={Target} tone="red" />
        <KpiTile label="Live precision" value={pct(s.precision)} sub="share of alerts that were fraud" icon={CheckCheck} tone="green" />
        <KpiTile label="Live recall" value={pct(s.recall)} sub="share of frauds alerted" icon={ShieldBan} tone="violet" />
        <KpiTile label="Fraud $ stopped" value={total ? money(s.fraud_amount_stopped, { compact: true }) : "—"} sub={total ? `of ${money(s.fraud_amount, { compact: true })} attempted` : "attempted fraud value"} icon={DollarSign} tone="teal" />
        <KpiTile label="False-alarm rate" value={pct(s.false_alarm_rate, 2)} sub="genuine transactions alerted" icon={AlertTriangle} tone="slate" />
        <KpiTile label="Avg latency" value={ms(s.avg_latency_ms, 2)} sub="scoring + explanation per transaction" icon={Timer} tone="amber" />
      </KpiGrid>

      {/* feed + charts */}
      <div className="grid grid-cols-1 gap-5 2xl:grid-cols-5">
        <Card title="Live feed" subtitle={`Newest first · last ${MAX_ROWS} kept in the browser · click a row for the full explanation`} className="2xl:col-span-3" noPad>
          <div className="flex items-center gap-1 px-5 pb-3">
            {[["all", "All transactions"], ["alerts", "Alerts only"]].map(([k, label]) => (
              <button
                key={k}
                onClick={() => setParams(k === "all" ? {} : { feed: k }, { replace: true })}
                className={`rounded-lg px-2.5 py-1 text-[12.5px] font-semibold transition ${feed === k ? "bg-primary-soft text-primary" : "text-ink-2 hover:bg-slate-100"}`}
              >
                {label}{k === "alerts" ? ` (${alertRows.length})` : ""}
              </button>
            ))}
          </div>
          {shown.length ? (
            <div className="table-wrap max-h-[640px] rounded-t-none border-x-0 border-b-0">
              <table className="table">
                <thead>
                  <tr>
                    <th>Time</th><th>Card</th><th>Merchant</th><th>Category</th><th className="num">Amount</th><th>Risk</th><th>Decision</th><th>Truth</th>
                  </tr>
                </thead>
                <tbody>
                  {shown.map((r) => (
                    <tr key={r.id ?? `${r.card_token}-${r.unix}-${r.amount}`} className={`cursor-pointer ${r._new ? "row-new" : ""}`} onClick={() => openRow(r)}>
                      <td className="font-mono text-[12px] text-ink-2" title={fmtDateTime(r.txn_time)}>{fmtDateTime(r.txn_time, { year: false })}</td>
                      <td className="font-mono text-[12px]">{last4(r.card_last4)}</td>
                      <td className="max-w-[160px] truncate">{r.merchant}</td>
                      <td className="text-ink-2">{r.category_label || titleCase(r.category)}</td>
                      <td className="num font-medium">{money(r.amount)}</td>
                      <td>
                        <span className="inline-flex items-center gap-1">
                          <RiskChip score={r.risk_score} level={r.risk_level} />
                          {r.policy?.length > 0 && (
                            <span className="tag border border-amber-200 bg-amber-50 text-amber-800" title={r.policy.map((h) => `${h.id}: ${h.title}`).join("\n")}>
                              {r.policy.map((h) => h.id).join("·")}
                            </span>
                          )}
                        </span>
                      </td>
                      <td><DecisionBadge decision={r.decision} size="sm" /></td>
                      <td><TruthTag label={r.label} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="p-5">
              {feed === "alerts" && rows.length ? (
                <EmptyState icon={Play} title="No alerts yet">Every transaction so far was approved. Keep the stream running: alerts are about 1% of traffic.</EmptyState>
              ) : (
                <EmptyState icon={Play} title="No transactions yet">Press <strong>Start stream</strong> to replay the test period through the engine.</EmptyState>
              )}
            </div>
          )}
        </Card>

        <div className="space-y-5 2xl:col-span-2">
          <Card title="Risk-score distribution" subtitle="Transactions per 10-point band since the last reset">
            {hist.length ? (
              <ChartBox height={190}>
                <BarChart data={hist} margin={{ left: -8, right: 8, top: 8, bottom: 0 }} barCategoryGap={3}>
                  <CartesianGrid {...GRID} />
                  <XAxis dataKey="bucket" {...AXIS} interval={0} tick={{ fontSize: 10, fill: "#64748b" }} />
                  <YAxis {...AXIS} scale="sqrt" tickFormatter={(v) => (v >= 1000 ? `${(v / 1000).toFixed(0)}k` : v)} />
                  <Tooltip content={<ChartTooltip labelFormatter={(l) => `Risk ${l}`} />} cursor={{ fill: "#f1f5f9" }} />
                  <Bar dataKey="count" name="Transactions" radius={[4, 4, 0, 0]}>
                    {hist.map((h) => <Cell key={h.bucket} fill={RISK[levelFromScore(h.from)].color} />)}
                  </Bar>
                </BarChart>
              </ChartBox>
            ) : (
              <div className="py-8 text-center text-[12.5px] text-muted">No data yet.</div>
            )}
            <p className="mt-1 text-[11px] text-muted">Square-root scale: genuine traffic dominates the 0–10 band. Colours follow the risk bands.</p>
          </Card>

          <Card title="Timeline per simulated day" subtitle="Volume (bars) and outcomes (lines) share the same day axis">
            {timeline.length ? (
              <>
                <ChartBox height={110}>
                  <BarChart data={timeline} margin={{ left: -8, right: 8, top: 4, bottom: 0 }} syncId="tl">
                    <CartesianGrid {...GRID} />
                    <XAxis dataKey="day" {...AXIS} hide />
                    <YAxis {...AXIS} tickFormatter={(v) => (v >= 1000 ? `${(v / 1000).toFixed(1)}k` : v)} />
                    <Tooltip content={<ChartTooltip labelFormatter={(l) => `Day ${l}`} />} cursor={{ fill: "#f1f5f9" }} />
                    <Bar dataKey="transactions" name="Transactions" fill={CHART.primary} fillOpacity={0.55} radius={[3, 3, 0, 0]} />
                  </BarChart>
                </ChartBox>
                <ChartBox height={150}>
                  <LineChart data={timeline} margin={{ left: -8, right: 8, top: 4, bottom: 0 }} syncId="tl">
                    <CartesianGrid {...GRID} />
                    <XAxis dataKey="day" {...AXIS} minTickGap={24} />
                    <YAxis {...AXIS} allowDecimals={false} />
                    <Tooltip content={<ChartTooltip labelFormatter={(l) => `Day ${l}`} />} />
                    <Line type="monotone" dataKey="alerts" name="Alerts" stroke={CHART.amber} strokeWidth={2} dot={false} />
                    <Line type="monotone" dataKey="frauds" name="Frauds (truth)" stroke={CHART.red} strokeWidth={2} dot={false} />
                    <Line type="monotone" dataKey="blocked" name="Blocked" stroke={CHART.violet} strokeWidth={2} dot={false} strokeDasharray="4 3" />
                  </LineChart>
                </ChartBox>
                <LegendDots items={[{ label: "Transactions", color: CHART.primary }, { label: "Alerts", color: CHART.amber }, { label: "Frauds (truth)", color: CHART.red }, { label: "Blocked", color: CHART.violet }]} />
              </>
            ) : (
              <div className="py-8 text-center text-[12.5px] text-muted">No data yet.</div>
            )}
          </Card>

          <Card title="Alerts by category" subtitle="Top merchant categories among medium + high alerts">
            {byCat.length ? (
              <ChartBox height={Math.max(120, byCat.length * 26)}>
                <BarChart data={byCat} layout="vertical" margin={{ left: 4, right: 28, top: 0, bottom: 0 }} barCategoryGap={4}>
                  <CartesianGrid {...GRID} horizontal={false} vertical />
                  <XAxis type="number" {...AXIS} allowDecimals={false} />
                  <YAxis type="category" dataKey="name" width={130} {...AXIS} />
                  <Tooltip content={<ChartTooltip />} cursor={{ fill: "#f1f5f9" }} />
                  <Bar dataKey="count" name="Alerts" fill={CHART.amber} radius={[0, 4, 4, 0]} barSize={14} />
                </BarChart>
              </ChartBox>
            ) : (
              <div className="py-8 text-center text-[12.5px] text-muted">No alerts yet.</div>
            )}
          </Card>
        </div>
      </div>

      <Drawer
        open={!!selected}
        onClose={() => setSelected(null)}
        title={selected ? `Transaction #${selected.id ?? "—"} · ${money(selected.amount)}` : ""}
        subtitle={selected ? `${last4(selected.card_last4)} · ${selected.merchant} · ${fmtTime(selected.txn_time)}` : ""}
        width="max-w-[640px]"
      >
        {selected && <ExplanationPanel result={selected} compact />}
      </Drawer>
    </div>
  );
}
