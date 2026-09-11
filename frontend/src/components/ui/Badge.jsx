import { AlertTriangle, CheckCircle2, ShieldBan, ShieldCheck, ShieldQuestion } from "lucide-react";
import { decisionOf, REVIEW, riskOf } from "../../lib/risk.js";

export function RiskChip({ score, level, size = "md" }) {
  const r = riskOf(level);
  const pad = size === "sm" ? "px-2 py-0 text-[11px]" : "px-2.5 py-0.5 text-[12px]";
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full font-semibold tabular-nums ${pad}`}
      style={{ backgroundColor: r.soft, color: r.ink }}
      title={`${r.label} risk`}
    >
      <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: r.color }} />
      {Number.isFinite(score) ? score.toFixed(size === "sm" ? 0 : 1) : "—"}
    </span>
  );
}

export function RiskLevelBadge({ level }) {
  const r = riskOf(level);
  return (
    <span className="pill" style={{ backgroundColor: r.soft, color: r.ink }}>
      <span className="h-2 w-2 rounded-full" style={{ backgroundColor: r.color }} />
      {r.label} risk
    </span>
  );
}

const DECISION_ICON = { APPROVE: ShieldCheck, STEP_UP: ShieldQuestion, BLOCK: ShieldBan };

export function DecisionBadge({ decision, size = "md" }) {
  const d = decisionOf(decision);
  const Icon = DECISION_ICON[String(decision || "").toUpperCase()] || ShieldCheck;
  const pad = size === "sm" ? "px-2 py-0 text-[10.5px]" : size === "lg" ? "px-3.5 py-1.5 text-[13px]" : "px-2.5 py-0.5 text-[11px]";
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-md font-bold uppercase tracking-wide text-white ${pad}`}
      style={{ backgroundColor: d.color }}
    >
      <Icon size={size === "lg" ? 15 : 12} /> {d.label}
    </span>
  );
}

export function TruthTag({ label }) {
  if (label === null || label === undefined) return <span className="tag bg-slate-100 text-slate-500">no label</span>;
  return Number(label) === 1 ? (
    <span className="tag bg-red-50 text-red-700 border border-red-200">Fraud</span>
  ) : (
    <span className="tag bg-slate-100 text-slate-600 border border-slate-200">Genuine</span>
  );
}

export function ReviewBadge({ status }) {
  const r = REVIEW[status] || REVIEW["n/a"];
  return (
    <span className="pill" style={{ backgroundColor: r.soft, color: r.ink }}>
      {status === "confirmed" && <AlertTriangle size={12} />}
      {status === "dismissed" && <CheckCircle2 size={12} />}
      {r.label}
    </span>
  );
}

export function Pill({ children, tone = "slate", className = "" }) {
  const tones = {
    slate: "bg-slate-100 text-slate-700",
    indigo: "bg-primary-soft text-primary",
    violet: "bg-accent-soft text-accent",
    teal: "bg-teal-soft text-teal-800",
    green: "bg-green-50 text-green-800",
    amber: "bg-amber-50 text-amber-800",
    red: "bg-red-50 text-red-800",
  };
  return <span className={`pill ${tones[tone] || tones.slate} ${className}`}>{children}</span>;
}
