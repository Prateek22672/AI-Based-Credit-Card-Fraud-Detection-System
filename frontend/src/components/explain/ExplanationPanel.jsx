import { AlertCircle, CheckCircle2, Clock3, Cpu, CreditCard, MapPin, ShieldAlert, ShoppingBag, Store, Tag } from "lucide-react";
import { fmtDateTime, last4, money, ms, pct } from "../../lib/format.js";
import { RISK, riskOf } from "../../lib/risk.js";
import { DecisionBadge, RiskLevelBadge, TruthTag } from "../ui/Badge.jsx";
import RiskGauge from "./RiskGauge.jsx";
import ShapBars from "./ShapBars.jsx";

function Vote({ label, value, meaning, color }) {
  const v = Number.isFinite(value) ? Math.max(0, Math.min(1, value)) : null;
  return (
    <div className="rounded-xl border border-line bg-white p-3">
      <div className="flex items-baseline justify-between gap-2">
        <span className="text-[12px] font-semibold text-ink-2">{label}</span>
        <span className="text-[15px] font-bold tabular-nums" style={{ color }}>
          {v === null ? "—" : `${(v * 100).toFixed(v >= 0.995 || v < 0.001 ? 2 : 1)}%`}
        </span>
      </div>
      <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-slate-100">
        <div className="h-full rounded-full" style={{ width: `${(v ?? 0) * 100}%`, backgroundColor: color }} />
      </div>
      <div className="mt-1.5 text-[11px] leading-snug text-muted">{meaning}</div>
    </div>
  );
}

/** Policy rules / novelty alarm that raised the decision above what the ML alone decided. */
function SafetyLayer({ hits, mlScore, mlLevel, finalLevel }) {
  const escalated = mlLevel && finalLevel && mlLevel !== finalLevel;
  return (
    <div className="card border-amber-300 bg-amber-50/60 p-4 sm:p-5">
      <h3 className="card-title mb-1 flex items-center gap-2 text-amber-900">
        <ShieldAlert size={16} /> Safety layer
      </h3>
      <p className="mb-3 text-[12px] text-amber-900/80">
        {escalated ? (
          <>
            ML risk <b className="tabular-nums">{Number(mlScore).toFixed(1)}</b> ({riskOf(mlLevel).label.toLowerCase()}) → escalated to{" "}
            <b>{riskOf(finalLevel).label.toLowerCase()}</b> by documented policy. Rules can only raise a decision, never approve.
          </>
        ) : (
          "These documented rules also fired. The ML decision was already at least this strict."
        )}
      </p>
      <ul className="space-y-2">
        {hits.map((h) => (
          <li key={h.id} className="flex gap-2 text-[13px] text-ink-2">
            <span className="mt-0.5 inline-flex h-5 shrink-0 items-center rounded bg-amber-500 px-1.5 text-[10.5px] font-bold text-white">
              {h.id}
            </span>
            <span>
              <b className="font-semibold">{h.title}.</b> {String(h.reason || "").replace(/^(Policy P\d|Novelty alarm): ?/, "")}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function Fact({ icon: Icon, label, value }) {
  return (
    <div className="flex items-start gap-2 min-w-0">
      <Icon size={14} className="mt-0.5 shrink-0 text-muted" />
      <div className="min-w-0">
        <div className="text-[10.5px] font-semibold uppercase tracking-wide text-muted">{label}</div>
        <div className="truncate text-[12.5px] font-medium text-ink">{value ?? "—"}</div>
      </div>
    </div>
  );
}

/**
 * Shared explanation panel. Accepts a ScoreResult (score / stream / scenario step)
 * or a full decision record (/api/transactions/{id}); missing sections are skipped.
 */
export default function ExplanationPanel({ result, showTruth = true, compact = false }) {
  if (!result) return null;
  const r = result;
  const lvl = riskOf(r.risk_level);
  const comps = r.components || {};
  // policy reasons are shown in the safety-layer card; this list holds the model's own reasons
  const reasons = (r.reasons || []).filter((t) => !/^(Policy P\d|Novelty alarm):/.test(t));
  const mitigating = r.mitigating || [];
  const shap = r.shap || [];
  const anomalyPct = comps.anomaly_percentile;

  return (
    <div className="space-y-4">
      {/* verdict */}
      <div className="card p-4 sm:p-5">
        <div className="flex flex-col items-center gap-4 sm:flex-row sm:items-center">
          <div className="shrink-0">
            <RiskGauge score={r.risk_score} level={r.risk_level} size={compact ? 200 : 230} />
          </div>
          <div className="flex-1 space-y-3 text-center sm:text-left">
            <div className="flex flex-wrap items-center justify-center gap-2 sm:justify-start">
              <RiskLevelBadge level={r.risk_level} />
              <DecisionBadge decision={r.decision} size="lg" />
              {showTruth && r.label !== undefined && r.label !== null && (
                <span className="inline-flex items-center gap-1.5 text-[11.5px] text-muted">
                  dataset truth: <TruthTag label={r.label} />
                </span>
              )}
            </div>
            <div>
              <div className="kpi-label">Fraud probability</div>
              <div className="text-[30px] font-extrabold leading-none tracking-tight" style={{ color: lvl.color }}>
                {pct(r.probability, r.probability < 0.01 ? 2 : 1)}
              </div>
              <div className="mt-1 text-[12px] text-muted">
                calibrated stacking output · {r.decision === "BLOCK" ? "auto-blocked (alerts ≥ 90% precise at this level)" : r.decision === "STEP_UP" ? "step-up verification / analyst review" : "approved without friction"}
              </div>
            </div>
            <div className="flex flex-wrap items-center justify-center gap-x-4 gap-y-1 text-[11.5px] text-muted sm:justify-start">
              <span className="inline-flex items-center gap-1"><Clock3 size={12} /> {ms(r.latency_ms, 1)} scoring latency</span>
              <span className="inline-flex items-center gap-1 font-mono"><Cpu size={12} /> {r.model_version || "model version n/a"}</span>
            </div>
          </div>
        </div>
      </div>

      {r.policy?.length > 0 && (
        <SafetyLayer hits={r.policy} mlScore={r.ml_risk_score} mlLevel={r.ml_risk_level} finalLevel={r.risk_level} />
      )}

      {/* model votes */}
      <div className="card p-4 sm:p-5">
        <h3 className="card-title mb-3">Model votes</h3>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <Vote label="XGBoost" value={comps.xgboost} color="#4F46E5" meaning="Main supervised classifier: probability this matches known fraud patterns." />
          <Vote label="Random Forest" value={comps.random_forest} color="#7C3AED" meaning="Second supervised opinion with a different inductive bias." />
          <Vote
            label="Anomaly percentile"
            value={anomalyPct}
            color="#0D9488"
            meaning={
              Number.isFinite(anomalyPct)
                ? `Isolation Forest: more unusual than ${(anomalyPct * 100).toFixed(1)}% of normal spending, even if no similar fraud was ever labelled.`
                : "Isolation Forest novelty score vs normal spending."
            }
          />
        </div>
        <p className="mt-3 text-[11.5px] text-muted">A logistic-regression meta-learner combines the three votes into the calibrated probability above.</p>
      </div>

      {/* reasons */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="card p-4 sm:p-5">
          <h3 className="card-title mb-2 flex items-center gap-2" style={{ color: RISK.HIGH.ink }}>
            <AlertCircle size={16} /> Why flagged
          </h3>
          {reasons.length ? (
            <ul className="space-y-2">
              {reasons.map((t, i) => (
                <li key={i} className="flex gap-2 text-[13px] text-ink-2">
                  <AlertCircle size={15} className="mt-0.5 shrink-0" style={{ color: RISK.HIGH.color }} />
                  <span>{t}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-[12.5px] text-muted">No risk factors strong enough to report: nothing about this transaction pushed the model towards fraud.</p>
          )}
        </div>
        <div className="card p-4 sm:p-5">
          <h3 className="card-title mb-2 flex items-center gap-2" style={{ color: RISK.LOW.ink }}>
            <CheckCircle2 size={16} /> Looks genuine because
          </h3>
          {mitigating.length ? (
            <ul className="space-y-2">
              {mitigating.map((t, i) => (
                <li key={i} className="flex gap-2 text-[13px] text-ink-2">
                  <CheckCircle2 size={15} className="mt-0.5 shrink-0" style={{ color: RISK.LOW.color }} />
                  <span>{t}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-[12.5px] text-muted">{r.mitigating ? "No strong mitigating signals." : "Mitigating factors are not stored in this summary record."}</p>
          )}
        </div>
      </div>

      {/* SHAP */}
      {shap.length > 0 && (
        <div className="card p-4 sm:p-5">
          <h3 className="card-title">Top feature contributions (SHAP)</h3>
          <p className="card-sub mb-3">TreeSHAP values from the XGBoost component, in log-odds. Red pushes the score up, green pulls it down.</p>
          <ShapBars items={shap} />
        </div>
      )}

      {/* facts */}
      <div className="card p-4 sm:p-5">
        <h3 className="card-title mb-3">Transaction facts</h3>
        <div className="grid grid-cols-2 gap-x-4 gap-y-3 md:grid-cols-3">
          <Fact icon={Clock3} label="Time" value={fmtDateTime(r.txn_time)} />
          <Fact icon={ShoppingBag} label="Amount" value={money(r.amount)} />
          <Fact icon={Tag} label="Category" value={r.category_label || r.category} />
          <Fact icon={Store} label="Merchant" value={r.merchant} />
          <Fact icon={CreditCard} label="Card" value={last4(r.card_last4)} />
          <Fact icon={MapPin} label="Home" value={r.home ? `${r.home.city}, ${r.home.state}` : r.home_city ? `${r.home_city}` : "—"} />
        </div>
        {r.card && r.card.n_txns > 0 && (
          <div className="mt-3 border-t border-line pt-3 text-[12px] text-muted">
            Card history at scoring time: {r.card.n_txns?.toLocaleString("en-US")} transactions · avg {money(r.card.mean_amt)} · {r.card.txns_per_day} per day ·{" "}
            {pct(r.card.night_share, 0)} at night · {r.card.n_merchants?.toLocaleString("en-US")} merchants
          </div>
        )}
      </div>
    </div>
  );
}
