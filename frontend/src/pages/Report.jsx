import { useEffect, useState } from "react";
import { CalendarClock, CheckCircle2, Circle, Clock, ExternalLink, FileText, Printer, Users } from "lucide-react";
import Card from "../components/ui/Card.jsx";
import Callout from "../components/ui/Callout.jsx";
import { PageLoader } from "../components/ui/Spinner.jsx";
import { API } from "../lib/api.js";

const STATUS = {
  done: { label: "Done", cls: "bg-green-50 text-green-800 border-green-200", Icon: CheckCircle2, dot: "#16A34A" },
  "in-progress": { label: "In progress", cls: "bg-amber-50 text-amber-800 border-amber-200", Icon: Clock, dot: "#F59E0B" },
  planned: { label: "Planned", cls: "bg-slate-50 text-slate-600 border-slate-200", Icon: Circle, dot: "#94A3B8" },
};

const isTodo = (s) => typeof s === "string" && /^TODO/i.test(s.trim());

function Todo({ value }) {
  if (!isTodo(value)) return <>{value}</>;
  return <span className="rounded bg-amber-50 px-1.5 py-0.5 text-amber-800 ring-1 ring-amber-200" title="Placeholder: edit public/data/project.json">{value}</span>;
}

function StatusPill({ status }) {
  const s = STATUS[status] || STATUS.planned;
  return <span className={`pill border ${s.cls}`}><s.Icon size={12} /> {s.label}</span>;
}

export default function Report() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  useEffect(() => {
    fetch("/data/project.json", { headers: { Accept: "application/json" } })
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`${r.status} loading project.json`))))
      .then(setData)
      .catch((e) => setError(e.message));
  }, []);

  if (error) return <Callout tone="warn" title="Could not load public/data/project.json">{error}</Callout>;
  if (!data) return <PageLoader label="Loading project report" />;

  const done = data.work_distribution?.filter((w) => w.status === "done").length || 0;
  const overall = data.work_distribution?.length ? Math.round(data.work_distribution.reduce((a, w) => a + (Number(w.percent) || 0), 0) / data.work_distribution.length) : 0;

  return (
    <div className="space-y-5 print:space-y-4">
      <div className="no-print flex flex-wrap items-center justify-between gap-2">
        <Callout tone="tip" className="flex-1">
          The team updates this page by editing <span className="font-mono">frontend/public/data/project.json</span> — no code changes needed. Highlighted values are placeholders.
        </Callout>
        <button className="btn-primary" onClick={() => window.print()}><Printer size={15} /> Print / Save as PDF</button>
      </div>

      {/* title block */}
      <section className="card p-6 sm:p-8">
        <div className="text-[11px] font-semibold uppercase tracking-[0.12em] text-primary">Project report &amp; progress</div>
        <h1 className="mt-2 text-[24px] font-extrabold leading-tight tracking-tight sm:text-[28px]">{data.title}</h1>
        <p className="mt-1 text-[14px] text-ink-2">{data.subtitle}</p>
        <div className="mt-4 grid grid-cols-1 gap-x-8 gap-y-2 text-[13px] sm:grid-cols-2">
          <div><span className="text-muted">Institution: </span><Todo value={data.institution} /></div>
          <div><span className="text-muted">Academic year: </span><Todo value={data.academic_year} /></div>
          <div><span className="text-muted">Guide: </span><Todo value={data.guide} /></div>
          <div><span className="text-muted">Last updated: </span>{data.last_updated}</div>
        </div>
      </section>

      <Card title="Summary">
        <p className="text-[13.5px] leading-relaxed text-ink-2">{data.summary}</p>
      </Card>

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        <Card title="Objectives">
          <ol className="space-y-2">
            {(data.objectives || []).map((o, i) => (
              <li key={i} className="flex gap-3 text-[13px] text-ink-2">
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary-soft text-[11.5px] font-bold text-primary">{i + 1}</span>
                <span className="leading-relaxed">{o}</span>
              </li>
            ))}
          </ol>
        </Card>
        <Card title="Team" subtitle="Members and primary responsibilities">
          <ul className="space-y-2.5">
            {(data.team || []).map((m, i) => (
              <li key={i} className="flex items-center gap-3 rounded-xl border border-line px-3 py-2.5">
                <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-primary to-accent text-[13px] font-bold text-white"><Users size={16} /></span>
                <div className="min-w-0">
                  <div className="text-[13.5px] font-semibold"><Todo value={m.name} /></div>
                  <div className="text-[12px] text-muted">{m.role}{m.email ? ` · ${m.email}` : ""}</div>
                </div>
              </li>
            ))}
          </ul>
        </Card>
      </div>

      <Card title="Work distribution" subtitle={`${done} of ${data.work_distribution?.length || 0} modules complete · overall ${overall}%`} noPad>
        <div className="table-wrap rounded-t-none border-x-0 border-b-0">
          <table className="table">
            <thead><tr><th>Module</th><th>Owner</th><th>Status</th><th className="w-[220px]">Complete</th></tr></thead>
            <tbody>
              {(data.work_distribution || []).map((w, i) => (
                <tr key={i}>
                  <td className="whitespace-normal font-medium">{w.module}</td>
                  <td className="text-ink-2">{w.owner}</td>
                  <td><StatusPill status={w.status} /></td>
                  <td>
                    <div className="flex items-center gap-2">
                      <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-100"><div className="h-full rounded-full" style={{ width: `${w.percent}%`, backgroundColor: STATUS[w.status]?.dot || "#4F46E5" }} /></div>
                      <span className="w-10 text-right text-[12px] tabular-nums text-ink-2">{w.percent}%</span>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-5">
        <Card title="Milestones" subtitle="Project timeline" className="lg:col-span-3">
          <ol className="relative ml-2 border-l-2 border-slate-200 pl-6">
            {(data.milestones || []).map((m, i) => {
              const s = STATUS[m.status] || STATUS.planned;
              return (
                <li key={i} className="relative pb-5 last:pb-0">
                  <span className="absolute -left-[31px] top-0.5 flex h-4 w-4 items-center justify-center rounded-full border-2 border-white" style={{ backgroundColor: s.dot, boxShadow: `0 0 0 2px ${s.dot}` }} />
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-[13.5px] font-semibold">{m.name}</span>
                    <StatusPill status={m.status} />
                    <span className="inline-flex items-center gap-1 text-[11.5px] text-muted"><CalendarClock size={12} /> <Todo value={m.date} /></span>
                  </div>
                  {m.note && <p className="mt-0.5 text-[12.5px] text-ink-2">{m.note}</p>}
                </li>
              );
            })}
          </ol>
        </Card>
        <div className="space-y-5 lg:col-span-2">
          <Card title="Deliverables">
            <ul className="space-y-2">
              {(data.deliverables || []).map((d, i) => {
                // "api:/docs" = a page served by the API (works when the dashboard is hosted separately)
                const onApi = d.path.startsWith("api:");
                const external = /^https?:/.test(d.path) || onApi;
                const href = onApi ? `${API || ""}${d.path.slice(4)}` : external ? d.path : d.path.startsWith("/") ? d.path : `/${d.path}`;
                return (
                  <li key={i} className="flex items-center gap-2.5 text-[13px]">
                    <FileText size={15} className="shrink-0 text-primary" />
                    {isTodo(d.path) ? (
                      <span>{d.name} — <Todo value={d.path} /></span>
                    ) : (
                      <a href={href} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-ink hover:text-primary hover:underline">
                        {d.name} <ExternalLink size={11} className="text-muted" />
                      </a>
                    )}
                    <span className="ml-auto font-mono text-[11px] text-muted">{d.path.startsWith("/") || external ? "" : d.path}</span>
                  </li>
                );
              })}
            </ul>
            <p className="mt-3 text-[11.5px] text-muted">The reports are copied into the site by <span className="font-mono">npm run sync-data</span>, so these links work on static hosting as well.</p>
          </Card>
          <Card title="Latest updates" subtitle="Changelog">
            <ul className="space-y-2">
              {(data.changelog || []).map((c, i) => (
                <li key={i} className="flex gap-3 text-[12.5px]">
                  <span className="w-[84px] shrink-0 font-mono text-[11.5px] text-muted"><Todo value={c.date} /></span>
                  <span className="text-ink-2"><Todo value={c.text} /></span>
                </li>
              ))}
            </ul>
          </Card>
        </div>
      </div>
    </div>
  );
}
