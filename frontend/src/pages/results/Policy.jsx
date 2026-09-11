import { ShieldAlert, ShieldPlus, Siren, Timer } from "lucide-react";
import Card from "../../components/ui/Card.jsx";
import Callout from "../../components/ui/Callout.jsx";
import KpiTile, { KpiGrid } from "../../components/ui/KpiTile.jsx";
import { int, isNum, num } from "../../lib/format.js";
import { P, Pc, ResultSection } from "./shared.jsx";

const SPLITS = [
  ["test", "Unseen test quarter"],
  ["val", "Validation quarter"],
];

function Compare({ block }) {
  const a = block.ml_only || {};
  const b = block.ml_plus_policy || {};
  const row = (label, f) => (
    <tr>
      <td className="font-medium">{label}</td>
      <td className="num">{f(a)}</td>
      <td className="num font-semibold">{f(b)}</td>
    </tr>
  );
  return (
    <div className="table-wrap">
      <table className="table">
        <thead><tr><th>At the alert (step-up) level</th><th className="num">ML only</th><th className="num">ML + safety layer</th></tr></thead>
        <tbody>
          {row("Alerts", (m) => (isNum(m.tp) ? int(m.tp + m.fp) : "—"))}
          {row("Frauds caught", (m) => (isNum(m.tp) ? `${int(m.tp)} / ${int(m.tp + m.fn)}` : "—"))}
          {row("Recall", (m) => Pc(m.recall))}
          {row("Precision", (m) => Pc(m.precision))}
          {row("False-alarm rate", (m) => Pc(m.fpr, 3))}
          {row("Fraud losses avoided (net of $5/alert)", (m) => Pc(m.savings_pct))}
        </tbody>
      </table>
    </div>
  );
}

export default function Policy() {
  return (
    <ResultSection name="policy" hint="stage: policy">
      {(data) => {
        const t = data.test || {};
        const rules = data.rules || [];
        const title = Object.fromEntries(rules.map((r) => [r.id, r.title]));
        return (
          <>
            <Callout tone="info" title="Why a safety layer on top of the ML?">
              The stacking meta-learner is fitted on labelled fraud, which XGBoost already explains, so it gives the Isolation Forest almost no weight.
              Attacks that never appear in the training data (card testing, cloned cards) are invisible to every supervised model. The safety layer adds a
              novelty route and a few documented rules (the kind the RBI 2021 Master Direction asks banks to parameterise). It can only raise a decision to
              step-up, never approve. This tab measures what that insurance costs on real, unseen traffic.
            </Callout>

            <KpiGrid cols={4}>
              <KpiTile label="Extra step-ups per day" value={isNum(t.extra_alerts_per_day) ? num(t.extra_alerts_per_day, 2) : "—"} sub="test quarter, beyond the ML's own alerts" icon={Timer} tone="amber" />
              <KpiTile label="Rules" value={rules.length || "—"} sub="P1-P3 policy rules + N1 novelty alarm" icon={ShieldPlus} tone="indigo" />
              <KpiTile label="Novelty threshold" value={isNum(data.novelty_percentile) ? Pc(data.novelty_percentile, 2) : "—"} sub="anomaly percentile vs genuine training data" icon={Siren} tone="teal" />
              <KpiTile label="Recall with safety layer" value={Pc(t.ml_plus_policy?.recall)} sub={`ML alone: ${Pc(t.ml_only?.recall)}`} icon={ShieldAlert} tone="violet" />
            </KpiGrid>

            {SPLITS.filter(([k]) => data[k]).map(([k, label]) => {
              const block = data[k];
              const rr = block.rules || {};
              return (
                <Card key={k} title={label} subtitle={`${num(block.days, 0)} days · extra alerts beyond the ML: ${num(block.extra_alerts_per_day, 2)} per day`} noPad>
                  <div className="space-y-4 p-5">
                    <div className="table-wrap">
                      <table className="table">
                        <thead><tr><th>Rule</th><th className="num">Fires</th><th className="num">On genuine</th><th className="num">Fraud rate</th><th className="num">Extra alerts</th><th className="num">Extra frauds</th><th className="num">Extra / day</th></tr></thead>
                        <tbody>
                          {Object.entries(rr).map(([id, v]) => (
                            <tr key={id}>
                              <td title={title[id] || ""}>
                                <span className="tag mr-1.5 bg-amber-500 font-bold text-white">{id}</span>
                                {(title[id] || "").split(" (")[0]}
                              </td>
                              <td className="num">{int(v.fires)}</td>
                              <td className="num">{int(v.fires_on_genuine)}</td>
                              <td className="num">{v.fires ? Pc(v.fraud_rate) : "—"}</td>
                              <td className="num">{int(v.extra_alerts)}</td>
                              <td className="num">{int(v.extra_frauds)}</td>
                              <td className="num">{P(v.extra_alerts_per_day, 2)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                    <div className="max-w-2xl"><Compare block={block} /></div>
                  </div>
                </Card>
              );
            })}

            <Callout tone="tip" title="How to read this">
              &quot;Extra alerts&quot; are transactions the safety layer escalates that the ML alone would have approved. On Sparkov the ML already catches almost
              every known fraud, so the extra frauds here are few; the layer&apos;s value shows on attack types absent from the training data (see the Unseen fraud tab and
              the Scam Scenarios page).
            </Callout>
          </>
        );
      }}
    </ResultSection>
  );
}
