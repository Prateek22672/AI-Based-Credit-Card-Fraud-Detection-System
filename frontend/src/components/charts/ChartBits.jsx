import { ResponsiveContainer } from "recharts";

export const AXIS = { tick: { fontSize: 11, fill: "#64748b" }, axisLine: { stroke: "#e2e8f0" }, tickLine: false };
export const GRID = { stroke: "#eef2f7", vertical: false };

export function ChartTooltip({ active, payload, label, formatter, labelFormatter }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-xl border border-line bg-white px-3 py-2 text-[12px] shadow-pop">
      {label !== undefined && <div className="mb-1 font-semibold text-ink">{labelFormatter ? labelFormatter(label) : label}</div>}
      <ul className="space-y-0.5">
        {payload.map((p, i) => (
          <li key={i} className="flex items-center justify-between gap-4">
            <span className="inline-flex items-center gap-1.5 text-muted">
              <span className="h-2 w-2 rounded-sm" style={{ backgroundColor: p.color || p.fill || p.stroke }} />
              {p.name}
            </span>
            <span className="font-semibold tabular-nums text-ink">{formatter ? formatter(p.value, p.name, p) : p.value?.toLocaleString?.() ?? p.value}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function ChartBox({ height = 240, children, className = "" }) {
  return (
    <div className={`w-full ${className}`} style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        {children}
      </ResponsiveContainer>
    </div>
  );
}

export function LegendDots({ items }) {
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[11.5px] text-ink-2">
      {items.map((it) => (
        <span key={it.label} className="inline-flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-sm" style={{ backgroundColor: it.color }} /> {it.label}
        </span>
      ))}
    </div>
  );
}
