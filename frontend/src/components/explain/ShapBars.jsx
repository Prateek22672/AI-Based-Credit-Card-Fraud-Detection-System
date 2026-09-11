import { RISK } from "../../lib/risk.js";

function fmtValue(feature, v) {
  if (!Number.isFinite(v)) return "";
  if (feature === "amt" || feature === "sum_24h") return `$${v.toLocaleString("en-US", { maximumFractionDigits: 2 })}`;
  if (feature.startsWith("is_") || feature.startsWith("cat_") || feature === "gender_m") return v >= 0.5 ? "yes" : "no";
  if (feature === "hour") return `${String(Math.round(v)).padStart(2, "0")}:00`;
  if (feature === "night_share" || feature === "cat_share") return `${(v * 100).toFixed(0)}%`;
  if (feature === "log_secs_since_last") {
    const s = Math.expm1(v);
    return s < 3600 ? `${(s / 60).toFixed(0)} min` : s < 86400 * 2 ? `${(s / 3600).toFixed(1)} h` : `${(s / 86400).toFixed(0)} d`;
  }
  if (feature === "card_history_len") return `${Math.round(Math.expm1(v))} txns`;
  if (feature === "log_city_pop") return `${Math.round(Math.expm1(v)).toLocaleString("en-US")} people`;
  if (feature === "log_amt") return `$${Math.expm1(v).toFixed(0)}`;
  if (Math.abs(v) >= 100) return v.toFixed(0);
  return v.toFixed(2);
}

// Horizontal SHAP bars: positive (towards fraud) grows red to the right,
// negative (towards genuine) grows green to the left of a shared centre axis.
export default function ShapBars({ items = [], max = 10 }) {
  const rows = items.slice(0, max);
  if (!rows.length) return <div className="text-[12.5px] text-muted">No SHAP contributions available for this record.</div>;
  const scale = Math.max(...rows.map((r) => Math.abs(r.shap || 0)), 0.01);
  return (
    <div>
      <div className="mb-2 flex items-center justify-between text-[11px] font-semibold uppercase tracking-wide">
        <span style={{ color: RISK.LOW.ink }}>← towards genuine</span>
        <span style={{ color: RISK.HIGH.ink }}>towards fraud →</span>
      </div>
      <ul className="space-y-1.5">
        {rows.map((r, i) => {
          const v = Number(r.shap) || 0;
          const w = (Math.abs(v) / scale) * 50;
          const pos = v >= 0;
          return (
            <li key={`${r.feature}-${i}`} className="grid grid-cols-[minmax(0,1fr)_minmax(0,1.15fr)] items-center gap-3 text-[12px]" title={`SHAP ${v.toFixed(3)} log-odds`}>
              <div className="min-w-0">
                <div className="truncate font-medium text-ink-2">{r.label || r.feature}</div>
                <div className="truncate font-mono text-[11px] text-muted">{fmtValue(r.feature || "", Number(r.value))}</div>
              </div>
              <div className="relative h-5 rounded bg-slate-50">
                <div className="absolute inset-y-0 left-1/2 w-px bg-slate-300" />
                <div
                  className="absolute top-0.5 bottom-0.5 rounded-sm"
                  style={{
                    left: pos ? "50%" : `${50 - w}%`,
                    width: `${Math.max(w, 0.6)}%`,
                    backgroundColor: pos ? RISK.HIGH.color : RISK.LOW.color,
                    opacity: 0.9,
                  }}
                />
                <span
                  className="absolute top-0 text-[10.5px] font-semibold tabular-nums leading-5"
                  style={{
                    color: pos ? RISK.HIGH.ink : RISK.LOW.ink,
                    ...(pos ? { left: `calc(${50 + w}% + 4px)` } : { right: `calc(${50 + w}% + 4px)` }),
                  }}
                >
                  {v > 0 ? "+" : ""}
                  {v.toFixed(2)}
                </span>
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
