import { NavLink } from "react-router-dom";
import { X } from "lucide-react";
import Logo from "./Logo.jsx";
import { NAV } from "./nav.js";
import { useApiStatus } from "../../context/ApiStatus.jsx";

export default function Sidebar({ open, onClose }) {
  const { online, health } = useApiStatus();
  return (
    <>
      {/* mobile backdrop */}
      <div
        className={`fixed inset-0 z-30 bg-navy-900/60 backdrop-blur-[2px] transition-opacity lg:hidden ${open ? "opacity-100" : "pointer-events-none opacity-0"}`}
        onClick={onClose}
        aria-hidden="true"
      />
      <aside
        className={`no-print fixed inset-y-0 left-0 z-40 flex w-[264px] flex-col text-white transition-transform duration-200 lg:translate-x-0 ${open ? "translate-x-0" : "-translate-x-full"}`}
        style={{ background: "linear-gradient(180deg, #0F172A 0%, #1E1B4B 100%)" }}
        aria-label="Primary navigation"
      >
        <div className="flex items-center justify-between px-5 pt-5 pb-4">
          <Logo />
          <button className="lg:hidden rounded-lg p-1.5 text-indigo-200 hover:bg-white/10" onClick={onClose} aria-label="Close menu">
            <X size={18} />
          </button>
        </div>
        <div className="mx-5 h-px bg-white/10" />
        <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-1">
          {NAV.map(({ to, label, icon: Icon, end, live }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              onClick={onClose}
              className={({ isActive }) =>
                `group flex items-center gap-3 rounded-xl px-3 py-2.5 text-[13.5px] font-medium transition-colors ${
                  isActive ? "bg-white/12 text-white shadow-[inset_0_0_0_1px_rgba(255,255,255,0.08)]" : "text-indigo-100/75 hover:bg-white/8 hover:text-white"
                }`
              }
            >
              {({ isActive }) => (
                <>
                  <Icon size={18} className={isActive ? "text-indigo-200" : "text-indigo-300/70 group-hover:text-indigo-200"} />
                  <span className="flex-1">{label}</span>
                  {live && (
                    <span
                      className={`h-1.5 w-1.5 rounded-full ${online ? "bg-emerald-400" : online === false ? "bg-red-400" : "bg-slate-500"}`}
                      title={online ? "Needs the API: online" : "Needs the API: offline"}
                    />
                  )}
                </>
              )}
            </NavLink>
          ))}
        </nav>
        <div className="px-5 pb-5 pt-3 border-t border-white/10 text-[11.5px] text-indigo-200/70 leading-relaxed">
          <div className="font-semibold text-indigo-100/90">Hybrid engine</div>
          <div>XGBoost + Random Forest + Isolation Forest</div>
          <div className="mt-1 font-mono text-[10.5px] text-indigo-200/60 truncate">{health?.model_version || "model version unknown"}</div>
        </div>
      </aside>
    </>
  );
}
