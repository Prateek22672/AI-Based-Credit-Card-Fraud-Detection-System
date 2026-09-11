import { useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { ChevronRight, CreditCard, Play, PlayCircle, ShieldAlert, ShieldCheck, Signal } from "lucide-react";
import { CartesianGrid, Line, LineChart, ReferenceArea, ReferenceDot, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../lib/api.js";
import { useAsync } from "../hooks/useAsync.js";
import { useApiStatus } from "../context/ApiStatus.jsx";
import { fmtTime, int, last4, minutesLabel, money, titleCase } from "../lib/format.js";
import { RISK, riskOf } from "../lib/risk.js";
import Card from "../components/ui/Card.jsx";
import { OfflineState } from "../components/ui/EmptyState.jsx";
import { DecisionBadge, RiskChip, RiskLevelBadge } from "../components/ui/Badge.jsx";
import { AXIS, ChartBox, ChartTooltip } from "../components/charts/ChartBits.jsx";
import ExplanationPanel from "../components/explain/ExplanationPanel.jsx";
import Drawer from "../components/ui/Drawer.jsx";
import { Spinner } from "../components/ui/Spinner.jsx";
import Callout from "../components/ui/Callout.jsx";

const ICONS = {
  card_testing: "🧪", stolen_card_spree: "🛍️", midnight_online: "🌙", impossible_travel: "✈️", escalation: "📈", normal_day: "☀️",
};

function VerdictBanner({ run }) {
  const v = riskOf(run.verdict);
  const peak = run.steps.reduce((a, b) => (b.risk_score > (a?.risk_score ?? -1) ? b : a), null);
  const first = run.steps.find((s) => s.risk_level === run.verdict) || peak;
  const byPolicy = first && first.policy?.length > 0 && first.ml_risk_level && first.ml_risk_level !== first.risk_level;
  const isNormal = run.scenario.id === "normal_day";
  const when = minutesLabel(first?.minutes_from_start).replace("+", "");
  const how = byPolicy
    ? ` The ML score alone was ${riskOf(first.ml_risk_level).label.toLowerCase()} (this attack is absent from the training data); the safety layer escalated it (${first.policy.map((h) => `${h.id} ${h.title.toLowerCase()}`).join("; ")}).`
    : "";
  const caughtText =
    run.verdict === "HIGH"
      ? `Blocked at step ${first?.step}: the attack was stopped after ${when}.${how}`
      : run.verdict === "MEDIUM"
        ? `Sent to step-up verification at step ${first?.step}: the cardholder must confirm (OTP) before money moves.${how}`
        : isNormal
          ? "Every purchase approved without friction: the engine recognised the card's usual behaviour."
          : "Not flagged: this attack pattern stayed below the alert threshold on this card.";
  return (
    <div className="flex items-start gap-3 rounded-2xl border px-4 py-3.5" style={{ backgroundColor: v.soft, borderColor: v.ring }}>
      {run.verdict === "LOW" ? <ShieldCheck size={22} style={{ color: v.color }} /> : <ShieldAlert size={22} style={{ color: v.color }} />}
      <div>
        <div className="text-[14px] font-bold" style={{ color: v.ink }}>
          Verdict: {v.label.toUpperCase()} risk · peak score {peak?.risk_score?.toFixed(1)} / 100
        </div>
        <div className="text-[12.5px]" style={{ color: v.ink }}>{caughtText}</div>
      </div>
    </div>
  );
}

function StepChart({ steps, onPick }) {
  const data = steps.map((s) => ({ ...s, x: s.minutes_from_start, y: s.risk_score, ml: s.ml_risk_score ?? s.risk_score }));
  const escalated = data.some((d) => d.ml !== d.y);
  return (
    <ChartBox height={240}>
      <LineChart data={data} margin={{ left: -10, right: 16, top: 10, bottom: 4 }}>
        <ReferenceArea y1={0} y2={30} fill={RISK.LOW.color} fillOpacity={0.09} />
        <ReferenceArea y1={30} y2={60} fill={RISK.MEDIUM.color} fillOpacity={0.12} />
        <ReferenceArea y1={60} y2={100} fill={RISK.HIGH.color} fillOpacity={0.09} />
        <CartesianGrid stroke="#e2e8f0" strokeDasharray="2 4" vertical={false} />
        <XAxis dataKey="x" type="number" {...AXIS} domain={[0, "dataMax"]} tickFormatter={(v) => `+${v} min`} />
        <YAxis dataKey="y" domain={[0, 100]} ticks={[0, 30, 60, 100]} {...AXIS} />
        <Tooltip
          content={
            <ChartTooltip
              labelFormatter={(l) => `${minutesLabel(l)} from start`}
              formatter={(v, name, p) => (name === "Risk score" ? `${v.toFixed(1)} (${p.payload.decision})` : Number(v).toFixed(1))}
            />
          }
        />
        {escalated && (
          <Line type="monotone" dataKey="ml" name="ML-only risk" stroke="#64748b" strokeWidth={1.5} strokeDasharray="5 4" dot={false} isAnimationActive={false} />
        )}
        <Line type="monotone" dataKey="y" name="Risk score" stroke="#0f172a" strokeWidth={2} dot={false} isAnimationActive={false} />
        {data.map((d) => (
          <ReferenceDot
            key={d.step}
            x={d.x}
            y={d.y}
            r={7}
            fill={riskOf(d.risk_level).color}
            stroke="#fff"
            strokeWidth={2}
            onClick={() => onPick?.(d)}
            style={{ cursor: "pointer" }}
            label={{ value: `${d.step}`, position: "top", fontSize: 10, fill: "#334155", fontWeight: 700, dy: -4 }}
          />
        ))}
      </LineChart>
    </ChartBox>
  );
}

export default function Scenarios() {
  const { online } = useApiStatus();
  const scenarios = useAsync(() => api.scenarios(), [online], { enabled: online === true });
  const cards = useAsync(() => api.cards(60), [online], { enabled: online === true });
  const [cardToken, setCardToken] = useState("");
  const [runs, setRuns] = useState({}); // id -> result
  const [busy, setBusy] = useState({}); // id -> bool
  const [active, setActive] = useState(null); // scenario id shown in detail
  const [pick, setPick] = useState(null); // step for the drawer
  const [error, setError] = useState(null);
  const [runningAll, setRunningAll] = useState(false);

  const run = async (id) => {
    setBusy((b) => ({ ...b, [id]: true }));
    setError(null);
    try {
      const r = await api.runScenario(id, cardToken || undefined);
      setRuns((x) => ({ ...x, [id]: r }));
      setActive(id);
      return r;
    } catch (e) {
      setError(`${id}: ${e.message}`);
    } finally {
      setBusy((b) => ({ ...b, [id]: false }));
    }
  };

  const runAll = async () => {
    setRunningAll(true);
    for (const s of scenarios.data || []) await run(s.id);
    setRunningAll(false);
  };

  // Deep link for demos: /scenarios?run=card_testing (or run=all) starts on load.
  const [params] = useSearchParams();
  const autoRan = useRef(false);
  useEffect(() => {
    const id = params.get("run");
    if (!id || autoRan.current || !scenarios.data?.length) return;
    autoRan.current = true;
    if (id === "all") runAll();
    else if (scenarios.data.some((s) => s.id === id)) run(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scenarios.data, params]);

  const comparison = useMemo(
    () =>
      (scenarios.data || [])
        .filter((s) => runs[s.id])
        .map((s) => {
          const r = runs[s.id];
          const max = Math.max(...r.steps.map((x) => x.risk_score));
          const first = r.steps.find((x) => x.risk_level !== "LOW");
          return { id: s.id, title: s.title, steps: r.steps.length, max, verdict: r.verdict, firstAlert: first ? `step ${first.step} (${minutesLabel(first.minutes_from_start)})` : "—", blocked: r.steps.filter((x) => x.decision === "BLOCK").length };
        }),
    [scenarios.data, runs],
  );

  if (online === false) return <OfflineState />;
  const list = scenarios.data || [];
  const current = active ? runs[active] : null;

  return (
    <div className="space-y-5">
      <Callout tone="info">
        Each scenario plays a short sequence of transactions against a <strong>sandbox copy</strong> of a real card&apos;s history, so
        the live demo is never affected. Watch how the risk score climbs as the behavioural signals stack up: a genuine day stays green.
      </Callout>

      <Card noPad>
        <div className="flex flex-col gap-3 px-5 py-4 md:flex-row md:items-center md:justify-between">
          <div className="flex flex-wrap items-center gap-2">
            <label className="inline-flex items-center gap-2 text-[12.5px] text-ink-2">
              <CreditCard size={15} className="text-muted" /> Card
              <select className="input w-auto min-w-[220px]" value={cardToken} onChange={(e) => setCardToken(e.target.value)}>
                <option value="">Default: typical daytime customer</option>
                {(cards.data || []).map((c) => (
                  <option key={c.token} value={c.token}>{last4(c.last4)} · {c.city}, {c.state} · {int(c.n_txns)} txns · avg {money(c.mean_amt, { decimals: 0 })}</option>
                ))}
              </select>
            </label>
          </div>
          <button className="btn-primary" onClick={runAll} disabled={runningAll || !list.length}>
            {runningAll ? <Spinner size={14} className="border-white/40 border-t-white" /> : <PlayCircle size={15} />} Run all scenarios
          </button>
        </div>
      </Card>

      {error && <Callout tone="warn">{error}</Callout>}

      {/* scenario cards */}
      {scenarios.loading && !list.length ? (
        <div className="flex items-center gap-2 text-[12.5px] text-muted"><Spinner size={14} /> Loading scenarios…</div>
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {list.map((s) => {
            const r = runs[s.id];
            const v = r ? riskOf(r.verdict) : null;
            return (
              <div key={s.id} className={`card flex flex-col p-4 transition ${active === s.id ? "ring-2 ring-primary/40" : ""}`}>
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="text-[22px] leading-none">{ICONS[s.id] || "🔎"}</span>
                    <h3 className="text-[14px] font-semibold leading-tight">{s.title}</h3>
                  </div>
                  {r && <span className="pill shrink-0" style={{ backgroundColor: v.soft, color: v.ink }}>{v.label}</span>}
                </div>
                <p className="mt-2 text-[12.5px] leading-relaxed text-ink-2">{s.scam}</p>
                <div className="mt-3">
                  <div className="kpi-label mb-1.5 flex items-center gap-1"><Signal size={11} /> Signals the engine looks for</div>
                  <ul className="space-y-1">
                    {s.signals.map((sig) => (
                      <li key={sig} className="flex gap-1.5 text-[12px] text-muted"><ChevronRight size={13} className="mt-0.5 shrink-0 text-primary" />{sig}</li>
                    ))}
                  </ul>
                </div>
                <div className="mt-4 flex items-center justify-between gap-2 border-t border-line pt-3">
                  <span className="text-[11.5px] text-muted">{s.n_steps} step{s.n_steps === 1 ? "" : "s"}</span>
                  <div className="flex gap-2">
                    {r && active !== s.id && <button className="btn-secondary btn-sm" onClick={() => setActive(s.id)}>View</button>}
                    <button className={`${r ? "btn-secondary" : "btn-primary"} btn-sm`} onClick={() => run(s.id)} disabled={!!busy[s.id]}>
                      {busy[s.id] ? <Spinner size={12} /> : <Play size={13} />} {r ? "Re-run" : "Run"}
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* detail */}
      {current && (
        <Card
          title={`${ICONS[current.scenario.id] || ""} ${current.scenario.title}`}
          subtitle={`Card ${last4(current.card.last4)} · ${current.card.home_city}, ${current.card.state} · avg spend ${money(current.card.mean_amt)} · ${int(current.card.n_txns)} past transactions`}
        >
          <div className="space-y-4">
            <VerdictBanner run={current} />
            <div className="grid grid-cols-1 gap-5 lg:grid-cols-5">
              <div className="lg:col-span-2">
                <div className="kpi-label mb-1">Risk score per step</div>
                <StepChart steps={current.steps} onPick={setPick} />
                <p className="mt-1 text-[11px] text-muted">
                  Bands: Low 0–30 · Medium 30–60 · High 60–100. Solid line = final risk; dashed line = ML-only risk where the
                  safety layer escalated. Click a dot for the full explanation.
                </p>
              </div>
              <div className="lg:col-span-3">
                <div className="kpi-label mb-2">Step timeline</div>
                <ol className="space-y-2">
                  {current.steps.map((st) => {
                    const rc = riskOf(st.risk_level);
                    return (
                      <li key={st.step} className="flex cursor-pointer gap-3 rounded-xl border border-line bg-white p-3 transition hover:border-indigo-300" onClick={() => setPick(st)}>
                        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-[12px] font-bold text-white" style={{ backgroundColor: rc.color }}>{st.step}</div>
                        <div className="min-w-0 flex-1">
                          <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[12.5px]">
                            <span className="font-mono text-muted">{minutesLabel(st.minutes_from_start)} · {fmtTime(st.txn_time).slice(0, 5)}</span>
                            <span className="font-semibold">{money(st.amount)}</span>
                            <span className="text-ink-2">{st.category_label || titleCase(st.category)}</span>
                            <span className="truncate text-muted">{st.merchant}</span>
                          </div>
                          <div className="mt-1.5 flex flex-wrap items-center gap-2">
                            <RiskChip score={st.risk_score} level={st.risk_level} />
                            <DecisionBadge decision={st.decision} size="sm" />
                            {st.policy?.map((h) => (
                              <span key={h.id} className="tag border border-amber-200 bg-amber-50 text-amber-800" title={h.reason}>
                                {h.id} · {h.title}
                              </span>
                            ))}
                          </div>
                          {st.reasons?.length ? (
                            <ul className="mt-1.5 space-y-0.5">
                              {st.reasons.slice(0, 3).map((t, i) => <li key={i} className="text-[12px] text-ink-2">• {t}</li>)}
                            </ul>
                          ) : (
                            <div className="mt-1.5 text-[12px] text-muted">No risk factors reported{st.mitigating?.[0] ? ` · ${st.mitigating[0]}` : ""}</div>
                          )}
                        </div>
                      </li>
                    );
                  })}
                </ol>
              </div>
            </div>
          </div>
        </Card>
      )}

      {/* comparison */}
      {comparison.length > 1 && (
        <Card title="Scenario comparison" subtitle="Peak risk and verdict for every scenario run in this session">
          <div className="table-wrap">
            <table className="table">
              <thead><tr><th>Scenario</th><th className="num">Steps</th><th className="num">Max risk</th><th>First alert</th><th className="num">Blocked steps</th><th>Verdict</th><th /></tr></thead>
              <tbody>
                {comparison.map((c) => (
                  <tr key={c.id}>
                    <td className="font-medium">{ICONS[c.id]} {c.title}</td>
                    <td className="num">{c.steps}</td>
                    <td className="num"><RiskChip score={c.max} level={c.verdict} /></td>
                    <td>{c.firstAlert}</td>
                    <td className="num">{c.blocked}</td>
                    <td><RiskLevelBadge level={c.verdict} /></td>
                    <td><button className="btn-ghost btn-sm" onClick={() => setActive(c.id)}>View</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      <Drawer open={!!pick} onClose={() => setPick(null)} title={pick ? `Step ${pick.step} · ${money(pick.amount)} · ${pick.category_label || pick.category}` : ""} subtitle={pick ? `${minutesLabel(pick.minutes_from_start)} from start · ${pick.merchant}` : ""} width="max-w-[640px]">
        {pick && <ExplanationPanel result={pick} showTruth={false} compact />}
      </Drawer>
    </div>
  );
}
