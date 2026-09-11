const usd = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 2 });
const usd0 = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });

export const isNum = (v) => typeof v === "number" && Number.isFinite(v);

export function money(v, { compact = false, decimals = 2 } = {}) {
  if (!isNum(v)) return "—";
  if (compact) {
    const abs = Math.abs(v);
    if (abs >= 1e6) return `$${(v / 1e6).toFixed(2)}M`;
    if (abs >= 1e4) return `$${(v / 1e3).toFixed(1)}k`;
    return usd0.format(v);
  }
  return decimals === 0 ? usd0.format(v) : usd.format(v);
}

export function pct(v, digits = 1) {
  if (!isNum(v)) return "—";
  return `${(v * 100).toFixed(digits)}%`;
}

export function num(v, digits = 3) {
  if (!isNum(v)) return "—";
  return v.toLocaleString("en-US", { maximumFractionDigits: digits, minimumFractionDigits: digits });
}

export function int(v) {
  if (!isNum(v)) return "—";
  return Math.round(v).toLocaleString("en-US");
}

export function ms(v, digits = 1) {
  if (!isNum(v)) return "—";
  return `${v.toFixed(digits)} ms`;
}

export function secs(v) {
  if (!isNum(v)) return "—";
  if (v < 1) return `${(v * 1000).toFixed(0)} ms`;
  if (v < 120) return `${v.toFixed(1)} s`;
  return `${(v / 60).toFixed(1)} min`;
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

// Timestamps from the API are naive ISO strings in the simulated (UTC) clock.
export function parseIso(iso) {
  if (!iso) return null;
  const s = String(iso).replace(" ", "T");
  const d = new Date(/[zZ]|[+-]\d\d:?\d\d$/.test(s) ? s : `${s}Z`);
  return Number.isNaN(d.getTime()) ? null : d;
}

export function fmtDateTime(iso, { seconds = true, year = true } = {}) {
  const d = parseIso(iso);
  if (!d) return "—";
  const p = (n) => String(n).padStart(2, "0");
  const time = `${p(d.getUTCHours())}:${p(d.getUTCMinutes())}${seconds ? `:${p(d.getUTCSeconds())}` : ""}`;
  return `${p(d.getUTCDate())} ${MONTHS[d.getUTCMonth()]}${year ? ` ${d.getUTCFullYear()}` : ""}, ${time}`;
}

export function fmtDate(iso) {
  const d = parseIso(iso);
  if (!d) return "—";
  return `${String(d.getUTCDate()).padStart(2, "0")} ${MONTHS[d.getUTCMonth()]} ${d.getUTCFullYear()}`;
}

export function fmtTime(iso) {
  const d = parseIso(iso);
  if (!d) return "—";
  const p = (n) => String(n).padStart(2, "0");
  return `${p(d.getUTCHours())}:${p(d.getUTCMinutes())}:${p(d.getUTCSeconds())}`;
}

export function fmtUnix(u) {
  return isNum(u) ? fmtDateTime(new Date(u * 1000).toISOString()) : "—";
}

export const last4 = (s) => `•••• ${s ?? "????"}`;

export function titleCase(s) {
  return String(s || "")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export function minutesLabel(m) {
  if (!isNum(m)) return "—";
  if (m < 60) return `+${m} min`;
  const h = Math.floor(m / 60);
  const r = m % 60;
  return r ? `+${h} h ${r} min` : `+${h} h`;
}
