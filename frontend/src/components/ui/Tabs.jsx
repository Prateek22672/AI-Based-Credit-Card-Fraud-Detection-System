export default function Tabs({ tabs, value, onChange, className = "" }) {
  return (
    <div className={`flex gap-1 overflow-x-auto rounded-xl border border-line bg-white p-1 ${className}`} role="tablist">
      {tabs.map((t) => (
        <button
          key={t.value}
          role="tab"
          aria-selected={value === t.value}
          onClick={() => onChange(t.value)}
          className={`tab ${value === t.value ? "tab-active" : ""}`}
        >
          {t.label}
          {t.count !== undefined && (
            <span className={`ml-1.5 rounded-full px-1.5 text-[11px] ${value === t.value ? "bg-primary/10" : "bg-slate-100"}`}>{t.count}</span>
          )}
        </button>
      ))}
    </div>
  );
}
