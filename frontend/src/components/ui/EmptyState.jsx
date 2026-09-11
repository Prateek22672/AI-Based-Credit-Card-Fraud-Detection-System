import { Inbox, PlugZap, ServerOff, Terminal } from "lucide-react";
import { useApiStatus } from "../../context/ApiStatus.jsx";

export function EmptyState({ icon: Icon = Inbox, title, children, className = "" }) {
  return (
    <div className={`flex flex-col items-center justify-center gap-2 rounded-2xl border border-dashed border-slate-300 bg-slate-50/60 px-6 py-12 text-center ${className}`}>
      <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-white text-muted shadow-sm border border-line">
        <Icon size={20} />
      </div>
      {title && <div className="text-[14px] font-semibold text-ink-2">{title}</div>}
      {children && <div className="max-w-md text-[12.5px] text-muted">{children}</div>}
    </div>
  );
}

export function OfflineState({ compact = false }) {
  const { refresh } = useApiStatus();
  if (compact) {
    return (
      <div className="flex items-center gap-2 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-[12.5px] text-red-800">
        <ServerOff size={14} /> Backend offline — start the API.
      </div>
    );
  }
  return (
    <div className="card overflow-hidden">
      <div className="flex flex-col items-center gap-3 px-6 py-12 text-center">
        <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-red-50 text-red-600 border border-red-100">
          <ServerOff size={26} />
        </div>
        <h2 className="text-[18px] font-semibold">Backend offline — start the API</h2>
        <p className="max-w-lg text-[13px] text-muted">
          This page talks to the FraudLens API in real time. Start it, then this page reconnects automatically.
        </p>
        <pre className="code mt-2 w-full max-w-lg text-left">
          <span className="text-slate-400"># from the project root</span>
          {"\n"}uvicorn fraudlens.api.main:app --port 8000
        </pre>
        <p className="text-[12px] text-muted">
          Static hosting? Set <span className="kbd">VITE_API_URL</span> to the API host at build time and{" "}
          <span className="kbd">FRAUDLENS_CORS_ORIGINS</span> on the API.
        </p>
        <button className="btn-primary mt-1" onClick={refresh}>
          <PlugZap size={15} /> Retry connection
        </button>
      </div>
    </div>
  );
}

export function NotGenerated({ name, hint }) {
  return (
    <EmptyState icon={Terminal} title="Result not generated yet">
      <span>
        <span className="font-mono">reports/results/{name}.json</span> does not exist yet. It is written by the research pipeline
        {hint ? ` (${hint})` : ""}. Refresh this page once the pipeline stage has finished.
      </span>
    </EmptyState>
  );
}
