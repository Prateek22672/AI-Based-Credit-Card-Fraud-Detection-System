// Single source of truth for risk colours, decision labels and band edges.
export const RISK = {
  LOW: { label: "Low", color: "#16A34A", soft: "#DCFCE7", ink: "#166534", ring: "#86efac" },
  MEDIUM: { label: "Medium", color: "#F59E0B", soft: "#FEF3C7", ink: "#92400E", ring: "#fcd34d" },
  HIGH: { label: "High", color: "#DC2626", soft: "#FEE2E2", ink: "#991B1B", ring: "#fca5a5" },
};

export const DECISION = {
  APPROVE: { label: "APPROVE", ...RISK.LOW },
  STEP_UP: { label: "STEP-UP", ...RISK.MEDIUM },
  BLOCK: { label: "BLOCK", ...RISK.HIGH },
};

export const BANDS = [
  { level: "LOW", from: 0, to: 30 },
  { level: "MEDIUM", from: 30, to: 60 },
  { level: "HIGH", from: 60, to: 100 },
];

export const riskOf = (level) => RISK[String(level || "").toUpperCase()] || RISK.LOW;
export const decisionOf = (d) => DECISION[String(d || "").toUpperCase()] || DECISION.APPROVE;

export function levelFromScore(score) {
  if (score >= 60) return "HIGH";
  if (score >= 30) return "MEDIUM";
  return "LOW";
}

export const REVIEW = {
  open: { label: "Open", color: "#4F46E5", soft: "#EEF2FF", ink: "#3730A3" },
  confirmed: { label: "Confirmed fraud", color: "#DC2626", soft: "#FEE2E2", ink: "#991B1B" },
  dismissed: { label: "Marked genuine", color: "#16A34A", soft: "#DCFCE7", ink: "#166534" },
  "n/a": { label: "No review", color: "#94A3B8", soft: "#F1F5F9", ink: "#475569" },
};

// Chart palette (validated with the dataviz palette checker): fixed order, never cycled.
export const CHART = {
  primary: "#4F46E5",
  teal: "#0D9488",
  amber: "#F59E0B",
  violet: "#7C3AED",
  red: "#DC2626",
  slate: "#94A3B8",
  green: "#16A34A",
};
export const SERIES = [CHART.primary, CHART.teal, CHART.amber, CHART.violet, CHART.slate];
