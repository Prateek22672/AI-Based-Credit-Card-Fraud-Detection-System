// Shield + magnifying-lens mark.
export function LogoMark({ size = 36, className = "" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" className={className} aria-hidden="true">
      <defs>
        <linearGradient id="fl-grad" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#6366F1" />
          <stop offset="1" stopColor="#8B5CF6" />
        </linearGradient>
      </defs>
      <path d="M32 4 L54 12 V30 C54 44 44 54 32 60 C20 54 10 44 10 30 V12 Z" fill="url(#fl-grad)" />
      <path d="M32 4 L54 12 V30 C54 44 44 54 32 60" fill="none" stroke="rgba(255,255,255,0.25)" strokeWidth="1.5" />
      <circle cx="29" cy="29" r="9" fill="none" stroke="#fff" strokeWidth="4" />
      <circle cx="29" cy="29" r="4" fill="rgba(255,255,255,0.35)" />
      <path d="M36 36 L44 44" stroke="#fff" strokeWidth="4.5" strokeLinecap="round" />
    </svg>
  );
}

export default function Logo({ compact = false }) {
  return (
    <div className="flex items-center gap-3">
      <LogoMark size={36} />
      {!compact && (
        <div className="leading-tight">
          <div className="text-white font-bold text-[17px] tracking-tight">FraudLens</div>
          <div className="text-indigo-200/80 text-[10.5px] font-medium uppercase tracking-[0.14em]">Fraud detection</div>
        </div>
      )}
    </div>
  );
}
