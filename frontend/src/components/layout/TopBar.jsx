import { Clock3, Menu, RefreshCw } from "lucide-react";
import { useApiStatus } from "../../context/ApiStatus.jsx";
import { fmtDateTime } from "../../lib/format.js";

export function StatusPill({ compact = false }) {
  const { online, health, refresh } = useApiStatus();
  const state = online === null ? "checking" : online ? "online" : "offline";
  const styles = {
    online: "bg-emerald-50 text-emerald-800 border-emerald-200",
    offline: "bg-red-50 text-red-700 border-red-200",
    checking: "bg-slate-50 text-slate-600 border-slate-200",
  }[state];
  const dot = { online: "bg-emerald-500 animate-pulse-dot", offline: "bg-red-500", checking: "bg-slate-400" }[state];
  return (
    <button
      type="button"
      onClick={refresh}
      className={`pill border ${styles} hover:brightness-95 transition`}
      title={state === "online" ? "API reachable (click to re-check)" : state === "offline" ? "API unreachable (click to re-check)" : "Checking API"}
    >
      <span className={`h-2 w-2 rounded-full ${dot}`} />
      {state === "online" && (
        <>
          API online
          {!compact && <span className="font-mono font-medium text-[11px] text-emerald-700/80">· {health?.model_version || "model"}</span>}
        </>
      )}
      {state === "offline" && "API offline"}
      {state === "checking" && "Checking API"}
    </button>
  );
}

export default function TopBar({ title, onMenu }) {
  const { health, online } = useApiStatus();
  const clock = health?.simulated_clock;
  const pos = health?.stream_position;
  const total = health?.stream_total;
  return (
    <header className="topbar sticky top-0 z-20 border-b border-line bg-white/85 backdrop-blur">
      <div className="mx-auto flex max-w-[1500px] items-center gap-3 px-4 py-3 sm:px-6">
        <button className="lg:hidden rounded-lg p-2 text-ink-2 hover:bg-slate-100" onClick={onMenu} aria-label="Open menu">
          <Menu size={20} />
        </button>
        <h1 className="flex-1 truncate text-[16px] sm:text-[18px] font-semibold">{title}</h1>
        <div className="hidden md:flex items-center gap-2 rounded-xl border border-line bg-slate-50 px-3 py-1.5 text-[12px] text-ink-2" title="Simulated clock of the replayed test period">
          <Clock3 size={14} className="text-muted" />
          {online && clock ? (
            <>
              <span className="font-mono">{fmtDateTime(clock)}</span>
              {Number.isFinite(pos) && Number.isFinite(total) && (
                <span className="text-muted">· {pos.toLocaleString("en-US")} / {total.toLocaleString("en-US")}</span>
              )}
            </>
          ) : (
            <span className="text-muted">simulated clock unavailable</span>
          )}
        </div>
        <StatusPill />
      </div>
    </header>
  );
}

export function RefreshButton({ onClick, busy, label = "Refresh" }) {
  return (
    <button className="btn-secondary btn-sm" onClick={onClick} disabled={busy}>
      <RefreshCw size={14} className={busy ? "animate-spin" : ""} /> {label}
    </button>
  );
}
