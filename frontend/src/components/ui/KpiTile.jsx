export default function KpiTile({ label, value, sub, icon: Icon, tone = "indigo", className = "" }) {
  const tones = {
    indigo: "bg-primary-soft text-primary",
    violet: "bg-accent-soft text-accent",
    teal: "bg-teal-soft text-teal-800",
    green: "bg-green-50 text-green-700",
    amber: "bg-amber-50 text-amber-700",
    red: "bg-red-50 text-red-700",
    slate: "bg-slate-100 text-slate-600",
  };
  return (
    <div className={`card flex items-start gap-3.5 p-4 ${className}`}>
      {Icon && (
        <div className={`mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl ${tones[tone] || tones.indigo}`}>
          <Icon size={18} />
        </div>
      )}
      <div className="min-w-0">
        <div className="kpi-label truncate">{label}</div>
        <div className="kpi-value mt-1.5 truncate">{value ?? "—"}</div>
        {sub && <div className="mt-1 text-[12px] text-muted truncate">{sub}</div>}
      </div>
    </div>
  );
}

export function KpiGrid({ children, cols = 4, className = "" }) {
  const map = {
    2: "grid-cols-1 sm:grid-cols-2",
    3: "grid-cols-1 sm:grid-cols-3",
    4: "grid-cols-2 lg:grid-cols-4",
    5: "grid-cols-2 md:grid-cols-3 xl:grid-cols-5",
    // six tiles only fit on one row on very wide screens; otherwise two rows of three
    6: "grid-cols-2 md:grid-cols-3 2xl:grid-cols-6",
  };
  return <div className={`grid gap-3 sm:gap-4 ${map[cols] || map[4]} ${className}`}>{children}</div>;
}
