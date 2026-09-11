import { BANDS, RISK, levelFromScore } from "../../lib/risk.js";

// Semicircular 0-100 gauge with the three risk bands and a needle at `score`.
export default function RiskGauge({ score = 0, level, size = 240 }) {
  const w = size;
  const h = size * 0.58;
  const cx = w / 2;
  const cy = h - size * 0.06;
  const r = size * 0.42;
  const thick = size * 0.085;
  const s = Math.max(0, Math.min(100, Number(score) || 0));
  const lvl = level || levelFromScore(s);
  const col = RISK[lvl]?.color || RISK.LOW.color;

  const pt = (v, rad) => {
    const t = Math.PI * (1 - v / 100);
    return [cx + rad * Math.cos(t), cy - rad * Math.sin(t)];
  };
  const arc = (from, to, rad) => {
    const [x1, y1] = pt(from, rad);
    const [x2, y2] = pt(to, rad);
    return `M ${x1} ${y1} A ${rad} ${rad} 0 ${to - from > 50 ? 1 : 0} 1 ${x2} ${y2}`;
  };
  // short marker across the arc (a full needle from the centre would run through the score text)
  const [ax, ay] = pt(s, r - thick * 1.05);
  const [bx, by] = pt(s, r + thick * 0.7);
  const ticks = [0, 30, 60, 100];

  return (
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} className="overflow-visible" role="img" aria-label={`Risk score ${s.toFixed(1)} of 100, ${lvl} risk`}>
      {BANDS.map((b) => (
        <path
          key={b.level}
          d={arc(b.from + (b.from ? 0.6 : 0), b.to - (b.to < 100 ? 0.6 : 0), r)}
          stroke={RISK[b.level].color}
          strokeWidth={thick}
          fill="none"
          strokeLinecap="butt"
          opacity={lvl === b.level ? 1 : 0.3}
        />
      ))}
      {ticks.map((t) => {
        const [x1, y1] = pt(t, r + thick * 0.7);
        const [x2, y2] = pt(t, r + thick * 0.95);
        const [lx, ly] = pt(t, r + thick * 1.45);
        return (
          <g key={t}>
            <line x1={x1} y1={y1} x2={x2} y2={y2} stroke="#94a3b8" strokeWidth={1.5} />
            <text x={lx} y={ly + 3} textAnchor="middle" fontSize={size * 0.045} fill="#64748b" fontWeight={600}>
              {t}
            </text>
          </g>
        );
      })}
      {/* marker */}
      <line x1={ax} y1={ay} x2={bx} y2={by} stroke="#fff" strokeWidth={size * 0.036} strokeLinecap="round" />
      <line x1={ax} y1={ay} x2={bx} y2={by} stroke="#0f172a" strokeWidth={size * 0.02} strokeLinecap="round" />
      {/* score */}
      <text x={cx} y={cy - size * 0.07} textAnchor="middle" fontSize={size * 0.17} fontWeight={800} fill={col} style={{ letterSpacing: "-0.03em" }}>
        {s.toFixed(1)}
      </text>
      <text x={cx} y={cy - size * 0.005} textAnchor="middle" fontSize={size * 0.045} fill="#64748b" fontWeight={600} letterSpacing="0.08em">
        RISK SCORE
      </text>
    </svg>
  );
}
