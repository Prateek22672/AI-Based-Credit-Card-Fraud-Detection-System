import { useMemo } from "react";
import { Link } from "react-router-dom";
import {
  Activity, ArrowRight, BarChart3, BookOpen, ClipboardList, Database, FlaskConical, GitMerge, Info, Layers, ShieldAlert,
  ShieldCheck, Sparkles, Target, Timer, TrendingUp, Zap, DollarSign,
} from "lucide-react";
import { Bar, BarChart, CartesianGrid, Cell, LabelList, XAxis, YAxis, Tooltip } from "recharts";
import { api, fetchResult } from "../lib/api.js";
import { useAsync } from "../hooks/useAsync.js";
import { useApiStatus } from "../context/ApiStatus.jsx";
import { ms, num, pct } from "../lib/format.js";
import { CHART } from "../lib/risk.js";
import KpiTile, { KpiGrid } from "../components/ui/KpiTile.jsx";
import Card from "../components/ui/Card.jsx";
import { AXIS, ChartBox, ChartTooltip, GRID } from "../components/charts/ChartBits.jsx";
import Callout from "../components/ui/Callout.jsx";

const COMPARE = [
  { key: "hybrid", label: "FraudLens hybrid", color: CHART.primary },
  { key: "rules", label: "Legacy bank rules", color: CHART.slate },
  { key: "lr", label: "Logistic regression", color: CHART.teal },
];

function Step({ icon: Icon, title, sub, tone = "indigo" }) {
  const tones = {
    indigo: "bg-primary-soft text-primary border-indigo-100",
    violet: "bg-accent-soft text-accent border-violet-100",
    teal: "bg-teal-soft text-teal-800 border-teal-100",
    slate: "bg-slate-50 text-slate-700 border-slate-200",
    dark: "bg-navy-900 text-white border-navy-900",
  };
  return (
    <div className={`flex min-w-0 flex-1 flex-col items-center rounded-xl border px-3 py-3 text-center ${tones[tone]}`}>
      <Icon size={18} />
      <div className="mt-1.5 text-[12.5px] font-semibold leading-tight">{title}</div>
      {sub && <div className="mt-0.5 text-[11px] opacity-75 leading-tight">{sub}</div>}
    </div>
  );
}

const Arrow = () => <ArrowRight size={16} className="hidden shrink-0 text-slate-300 md:block" />;

export default function Overview() {
  const { online, health } = useApiStatus();
  const model = useAsync(() => api.model(), [online], { enabled: online === true });
  const bench = useAsync(() => fetchResult("benchmark_sparkov"), []);

  const b = bench.data?.data || null;
  const metrics = model.data?.test_metrics || b?.hybrid?.test || null;
  const latency = model.data?.latency || b?.hybrid?.latency || null;
  const source = model.data ? "live model card" : b?.hybrid ? `benchmark_sparkov (${bench.data.source})` : null;

  const compare = useMemo(
    () =>
      COMPARE.map((c) => ({ ...c, row: b?.[c.key]?.test || null }))
        .filter((c) => c.row),
    [b],
  );
  const chartData = compare.map((c) => ({ name: c.label, prAuc: c.row.pr_auc, color: c.color }));

  return (
    <div className="space-y-6">
      {/* hero */}
      <section
        className="relative overflow-hidden rounded-2xl border border-indigo-900/40 px-6 py-8 text-white shadow-card sm:px-10 sm:py-10"
        style={{ background: "linear-gradient(120deg, #0F172A 0%, #1E1B4B 55%, #312E81 100%)" }}
      >
        <div className="pointer-events-none absolute -right-24 -top-24 h-72 w-72 rounded-full bg-indigo-500/20 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-32 right-40 h-72 w-72 rounded-full bg-violet-500/20 blur-3xl" />
        <div className="relative max-w-3xl">
          <div className="pill border border-white/15 bg-white/10 text-indigo-100">
            <Sparkles size={13} /> Final-year project · Cyber Security / Machine Learning
          </div>
          <h1 className="mt-4 text-[26px] font-extrabold leading-tight tracking-tight text-white sm:text-[34px]">
            FraudLens — Explainable Hybrid Credit-Card Fraud Detection
          </h1>
          <p className="mt-4 text-[14px] leading-relaxed text-indigo-100/90 sm:text-[15px]">
            FraudLens scores every card transaction in a fraction of a second, inside the payment authorisation path. Behavioural
            features built from each card&apos;s own history feed three detectors — a supervised XGBoost, a Random Forest and an
            unsupervised Isolation Forest — whose votes a stacking meta-learner turns into a calibrated fraud probability, a
            0–100 risk score and an Approve / Step-up / Block decision. A safety layer of documented policy rules and a novelty
            alarm covers attacks absent from the training data. Every decision is explained with SHAP reason codes and
            stored in a forensic audit log that analysts review from this dashboard. The system is evaluated the honest way:
            a chronological split with a label-delay gap, on an unseen test quarter, against legacy rules and eight other models.
          </p>
          <div className="mt-5 flex flex-wrap items-center gap-2 rounded-xl border border-white/15 bg-white/8 px-4 py-3 text-[13px] font-medium text-white">
            <ShieldCheck size={16} className="text-emerald-300" />
            Web platform + real-time API, powered by a hybrid ML model (XGBoost + Random Forest + Isolation Forest) with SHAP explanations
          </div>
          <div className="mt-6 flex flex-wrap gap-2">
            <Link to="/monitor" className="btn bg-white text-navy-900 hover:bg-indigo-50"><Activity size={15} /> Open live monitor</Link>
            <Link to="/tester" className="btn border border-white/25 bg-white/10 text-white hover:bg-white/15"><FlaskConical size={15} /> Score a transaction</Link>
            <Link to="/results" className="btn border border-white/25 bg-white/10 text-white hover:bg-white/15"><BarChart3 size={15} /> Research results</Link>
          </div>
        </div>
      </section>

      {/* KPIs */}
      <section>
        <div className="mb-3 flex flex-wrap items-end justify-between gap-2">
          <div>
            <h2 className="text-[17px] font-semibold">Deployed model on the unseen test quarter</h2>
            <p className="text-[12.5px] text-muted">
              Apr–Jun 2020 · {metrics ? `${(metrics.tp + metrics.fn).toLocaleString("en-US")} frauds among ${(metrics.tp + metrics.fp + metrics.fn + metrics.tn).toLocaleString("en-US")} transactions` : "held-out period"}
              {source ? ` · source: ${source}` : ""}
              {health?.model_version ? ` · ${health.model_version}` : ""}
            </p>
          </div>
        </div>
        {!metrics && !bench.loading && !model.loading && (
          <Callout tone="warn" title="Hybrid model metrics are not available yet" className="mb-3">
            The pipeline has not written the hybrid row of <span className="font-mono">benchmark_sparkov.json</span> / the model card yet. The tiles fill in automatically once it exists.
          </Callout>
        )}
        <KpiGrid cols={6}>
          <KpiTile label="PR-AUC" value={num(metrics?.pr_auc, 3)} sub="average precision (primary metric)" icon={Target} tone="indigo" />
          <KpiTile label="Recall" value={pct(metrics?.recall)} sub="frauds caught at the alert threshold" icon={ShieldAlert} tone="red" />
          <KpiTile label="Precision" value={pct(metrics?.precision)} sub="alerts that were real fraud" icon={ShieldCheck} tone="green" />
          <KpiTile label="F1 score" value={num(metrics?.f1, 3)} sub={metrics ? `MCC ${num(metrics.mcc, 3)}` : "harmonic mean"} icon={TrendingUp} tone="violet" />
          <KpiTile label="Fraud $ caught" value={pct(metrics?.amount_recall)} sub={metrics ? `of $${Math.round(metrics.fraud_amount_total).toLocaleString("en-US")} at risk` : "share of fraud value"} icon={DollarSign} tone="teal" />
          <KpiTile label="Latency p50" value={ms(latency?.p50_ms, 1)} sub={latency ? `p95 ${ms(latency.p95_ms, 1)} per transaction` : "per transaction"} icon={Timer} tone="amber" />
        </KpiGrid>
      </section>

      {/* comparison + pipeline */}
      <div className="grid grid-cols-1 gap-6 xl:grid-cols-5">
        <Card
          title="Hybrid vs legacy rules vs logistic regression"
          subtitle="Same chronological split, same unseen test quarter. Thresholds tuned on validation data only."
          className="xl:col-span-3"
        >
          {compare.length ? (
            <div className="space-y-4">
              <div>
                <div className="kpi-label mb-2">PR-AUC (higher is better)</div>
                <ChartBox height={140}>
                  <BarChart data={chartData} layout="vertical" margin={{ left: 4, right: 48, top: 4, bottom: 4 }} barCategoryGap={8}>
                    <CartesianGrid {...GRID} horizontal={false} vertical />
                    <XAxis type="number" domain={[0, 1]} {...AXIS} tickFormatter={(v) => v.toFixed(1)} />
                    <YAxis type="category" dataKey="name" width={130} {...AXIS} />
                    <Tooltip content={<ChartTooltip formatter={(v) => (typeof v === "number" ? v.toFixed(3) : v)} />} cursor={{ fill: "#f1f5f9" }} />
                    <Bar dataKey="prAuc" name="PR-AUC" radius={[0, 4, 4, 0]} barSize={20} isAnimationActive={false}>
                      {chartData.map((d) => <Cell key={d.name} fill={d.color} />)}
                      <LabelList dataKey="prAuc" position="right" formatter={(v) => (typeof v === "number" ? v.toFixed(3) : "")} style={{ fontSize: 11, fill: "#334155", fontWeight: 600 }} />
                    </Bar>
                  </BarChart>
                </ChartBox>
              </div>
              <div className="table-wrap">
                <table className="table">
                  <thead>
                    <tr><th>Model</th><th className="num">PR-AUC</th><th className="num">Recall</th><th className="num">Precision</th><th className="num">F1</th><th className="num">$ caught</th></tr>
                  </thead>
                  <tbody>
                    {compare.map((c) => (
                      <tr key={c.key} className={c.key === "hybrid" ? "row-highlight" : ""}>
                        <td><span className="inline-flex items-center gap-2"><span className="h-2.5 w-2.5 rounded-sm" style={{ backgroundColor: c.color }} />{c.label}</span></td>
                        <td className="num">{num(c.row.pr_auc, 3)}</td>
                        <td className="num">{pct(c.row.recall)}</td>
                        <td className="num">{pct(c.row.precision)}</td>
                        <td className="num">{num(c.row.f1, 3)}</td>
                        <td className="num">{pct(c.row.amount_recall)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ) : (
            <div className="text-[13px] text-muted">{bench.loading ? "Loading benchmark…" : "Benchmark results not generated yet."}</div>
          )}
          {b?.rules?.rules && (
            <p className="mt-3 text-[12px] text-muted">
              Legacy rules: {b.rules.rules.join(" · ")}.
            </p>
          )}
        </Card>

        <Card title="How a transaction flows" subtitle="From authorisation request to an explained, logged decision in well under a second." className="xl:col-span-2">
          <div className="flex flex-col gap-2">
            <div className="flex flex-col gap-2 md:flex-row md:items-stretch">
              <Step icon={Zap} title="Transaction" sub="card, amount, merchant, time" tone="slate" />
              <Arrow />
              <Step icon={Database} title="Feature store" sub="card history → 39 behavioural features" tone="teal" />
            </div>
            <div className="grid grid-cols-3 gap-2">
              <Step icon={Layers} title="XGBoost" sub="supervised" />
              <Step icon={Layers} title="Random Forest" sub="supervised" tone="violet" />
              <Step icon={Layers} title="Isolation Forest" sub="unsupervised" tone="teal" />
            </div>
            <div className="flex flex-col gap-2 md:flex-row md:items-stretch">
              <Step icon={GitMerge} title="Stacking meta-learner" sub="calibrated probability" />
              <Arrow />
              <Step icon={Target} title="Risk score 0–100" sub="Low · Medium · High" tone="slate" />
            </div>
            <div className="flex flex-col gap-2 md:flex-row md:items-stretch">
              <Step icon={ShieldAlert} title="Safety layer" sub="policy rules · novelty alarm" tone="slate" />
              <Arrow />
              <Step icon={ShieldCheck} title="Approve / Step-up / Block" sub="cost-optimal thresholds" tone="dark" />
            </div>
            <Step icon={Info} title="SHAP reasons" sub="why flagged · looks genuine · forensic audit log" tone="violet" />
          </div>
        </Card>
      </div>

      {/* quick links */}
      <section>
        <h2 className="mb-3 text-[17px] font-semibold">Explore the platform</h2>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {[
            { to: "/monitor", icon: Activity, title: "Live Monitor", text: "Replay the unseen test period through the engine and watch precision, recall and money stopped update live." },
            { to: "/tester", icon: FlaskConical, title: "Transaction Tester", text: "Pick a real card, craft a transaction and see the risk gauge, model votes and SHAP reasons." },
            { to: "/scenarios", icon: ShieldAlert, title: "Scam Scenarios", text: "Card testing, stolen-card sprees, impossible travel: how each attack looks step by step." },
            { to: "/cases", icon: ClipboardList, title: "Case Queue", text: "Analyst workflow: review medium/high alerts, confirm fraud or dismiss, with a forensic audit record." },
            { to: "/results", icon: BarChart3, title: "Research Results", text: "Benchmarks, imbalance strategies, evaluation-protocol study, ablations, unseen fraud, business impact." },
            { to: "/report", icon: BookOpen, title: "Project Report", text: "Objectives, team, work distribution, milestones and deliverables for reviewers." },
            { to: "/about", icon: Info, title: "Architecture", text: "System design, tech stack, why a web platform, and how to run it." },
          ].map(({ to, icon: Icon, title, text }) => (
            <Link key={to} to={to} className="card group flex flex-col gap-2 p-4 transition hover:-translate-y-0.5 hover:border-indigo-200 hover:shadow-pop">
              <div className="flex items-center justify-between">
                <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary-soft text-primary"><Icon size={18} /></span>
                <ArrowRight size={16} className="text-slate-300 transition group-hover:translate-x-0.5 group-hover:text-primary" />
              </div>
              <div className="text-[14px] font-semibold">{title}</div>
              <p className="text-[12.5px] text-muted leading-relaxed">{text}</p>
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}
