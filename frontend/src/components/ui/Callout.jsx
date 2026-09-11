import { Info, Lightbulb, AlertTriangle } from "lucide-react";

const TONES = {
  info: { cls: "border-indigo-200 bg-primary-soft text-indigo-900", Icon: Info },
  tip: { cls: "border-teal-200 bg-teal-50 text-teal-900", Icon: Lightbulb },
  warn: { cls: "border-amber-200 bg-amber-50 text-amber-900", Icon: AlertTriangle },
};

export default function Callout({ tone = "info", title, children, className = "" }) {
  const { cls, Icon } = TONES[tone] || TONES.info;
  return (
    <div className={`flex gap-3 rounded-xl border px-4 py-3 text-[13px] leading-relaxed ${cls} ${className}`}>
      <Icon size={16} className="mt-0.5 shrink-0 opacity-80" />
      <div>
        {title && <div className="font-semibold">{title}</div>}
        <div className={title ? "mt-0.5 opacity-90" : "opacity-90"}>{children}</div>
      </div>
    </div>
  );
}
