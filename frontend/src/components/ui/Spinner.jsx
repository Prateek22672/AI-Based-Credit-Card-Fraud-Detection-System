export function Spinner({ size = 18, className = "" }) {
  return (
    <span
      className={`inline-block animate-spin rounded-full border-2 border-slate-300 border-t-primary ${className}`}
      style={{ width: size, height: size }}
      role="status"
      aria-label="Loading"
    />
  );
}

export function PageLoader({ label = "Loading" }) {
  return (
    <div className="flex items-center justify-center gap-3 py-24 text-muted">
      <Spinner /> <span className="text-[13px]">{label}…</span>
    </div>
  );
}
