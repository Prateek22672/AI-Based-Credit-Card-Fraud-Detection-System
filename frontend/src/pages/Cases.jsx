import { useMemo, useState } from "react";
import { AlertTriangle, CheckCircle2, ClipboardList, FileSearch, Inbox, Percent, RefreshCw, XCircle } from "lucide-react";
import { api } from "../lib/api.js";
import { useAsync } from "../hooks/useAsync.js";
import { useApiStatus } from "../context/ApiStatus.jsx";
import { fmtDateTime, int, last4, money, pct, titleCase } from "../lib/format.js";
import Card from "../components/ui/Card.jsx";
import KpiTile, { KpiGrid } from "../components/ui/KpiTile.jsx";
import Tabs from "../components/ui/Tabs.jsx";
import { DecisionBadge, ReviewBadge, RiskChip, TruthTag } from "../components/ui/Badge.jsx";
import Drawer from "../components/ui/Drawer.jsx";
import { EmptyState, OfflineState } from "../components/ui/EmptyState.jsx";
import ExplanationPanel from "../components/explain/ExplanationPanel.jsx";
import { Spinner } from "../components/ui/Spinner.jsx";
import Callout from "../components/ui/Callout.jsx";

const STATUS_TABS = [
  { value: "open", label: "Open" },
  { value: "confirmed", label: "Confirmed fraud" },
  { value: "dismissed", label: "Dismissed" },
  { value: "all", label: "All" },
];

function fmtFeature(k, v) {
  if (typeof v !== "number") return String(v);
  if (k === "amt" || k === "sum_24h") return `$${v.toLocaleString("en-US", { maximumFractionDigits: 2 })}`;
  if (Number.isInteger(v)) return v.toString();
  return v.toFixed(4);
}

function ReviewForm({ record, onDone }) {
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(null);
  const [error, setError] = useState(null);
  const submit = async (label) => {
    setBusy(label);
    setError(null);
    try {
      const r = await api.review(record.id, { label, note: note.trim() || null });
      onDone(r);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(null);
    }
  };
  return (
    <div className="card p-4">
      <h3 className="card-title">Analyst verdict</h3>
      <p className="card-sub mb-3">Stored with the record and kept as a label for retraining.</p>
      <textarea className="input min-h-[64px]" placeholder="Optional note (e.g. cardholder confirmed by phone)" value={note} onChange={(e) => setNote(e.target.value)} maxLength={500} />
      {error && <div className="mt-2 text-[12px] text-red-700">{error}</div>}
      <div className="mt-3 flex flex-wrap gap-2">
        <button className="btn-danger" onClick={() => submit("fraud")} disabled={!!busy}>{busy === "fraud" ? <Spinner size={13} className="border-white/40 border-t-white" /> : <AlertTriangle size={14} />} Confirm fraud</button>
        <button className="btn-success" onClick={() => submit("genuine")} disabled={!!busy}>{busy === "genuine" ? <Spinner size={13} className="border-white/40 border-t-white" /> : <CheckCircle2 size={14} />} Mark genuine</button>
      </div>
    </div>
  );
}

export default function Cases() {
  const { online } = useApiStatus();
  const [status, setStatus] = useState("open");
  const [refreshTick, setRefreshTick] = useState(0);
  const list = useAsync(
    () => api.transactions({ level: "MEDIUM,HIGH", limit: 200, status: status === "all" ? undefined : status }),
    [status, online, refreshTick],
    { enabled: online === true },
  );
  const stats = useAsync(() => api.stats(), [online, refreshTick], { enabled: online === true });
  const [selectedId, setSelectedId] = useState(null);
  const detail = useAsync(() => api.transaction(selectedId), [selectedId], { enabled: !!selectedId, keep: false });
  const [rowBusy, setRowBusy] = useState(null);
  const [flash, setFlash] = useState(null);

  const rows = list.data || [];
  const reviews = stats.data?.reviews || {};

  // Analyst agreement with the dataset label, computed from the rows we can see.
  const agreement = useMemo(() => {
    const reviewed = rows.filter((r) => (r.review_status === "confirmed" || r.review_status === "dismissed") && (r.label === 0 || r.label === 1));
    if (!reviewed.length) return null;
    const agree = reviewed.filter((r) => (r.review_status === "confirmed") === (r.label === 1)).length;
    return { rate: agree / reviewed.length, n: reviewed.length };
  }, [rows]);

  const quickReview = async (e, r, label) => {
    e.stopPropagation();
    setRowBusy(r.id);
    try {
      await api.review(r.id, { label });
      setFlash(`#${r.id} marked ${label === "fraud" ? "confirmed fraud" : "genuine"}`);
      setRefreshTick((t) => t + 1);
    } catch (err) {
      setFlash(`Review failed: ${err.message}`);
    } finally {
      setRowBusy(null);
    }
  };

  if (online === false) return <OfflineState />;

  return (
    <div className="space-y-5">
      <KpiGrid cols={4}>
        <KpiTile label="Open cases" value={int(reviews.open ?? 0)} sub="alerts awaiting an analyst" icon={Inbox} tone="indigo" />
        <KpiTile label="Confirmed fraud" value={int(reviews.confirmed ?? 0)} sub="analyst agreed with the alert" icon={AlertTriangle} tone="red" />
        <KpiTile label="Dismissed" value={int(reviews.dismissed ?? 0)} sub="marked genuine (false alarm)" icon={XCircle} tone="green" />
        <KpiTile label="Analyst agreement" value={agreement ? pct(agreement.rate, 0) : "—"} sub={agreement ? `matches dataset label on ${agreement.n} reviewed case${agreement.n === 1 ? "" : "s"} (this view)` : "no reviewed cases in view"} icon={Percent} tone="teal" />
      </KpiGrid>

      <Card
        title="Alert queue"
        subtitle="Medium and high-risk decisions from the log, newest first (max 200)"
        noPad
        actions={
          <>
            <Tabs tabs={STATUS_TABS} value={status} onChange={setStatus} />
            <button className="btn-secondary btn-sm" onClick={() => setRefreshTick((t) => t + 1)} disabled={list.loading}><RefreshCw size={13} className={list.loading ? "animate-spin" : ""} /> Refresh</button>
          </>
        }
      >
        {flash && <div className="mx-5 mb-3"><Callout tone="tip">{flash}</Callout></div>}
        {list.loading && !rows.length ? (
          <div className="flex items-center gap-2 p-5 text-[12.5px] text-muted"><Spinner size={14} /> Loading cases…</div>
        ) : rows.length ? (
          <div className="table-wrap max-h-[640px] rounded-t-none border-x-0 border-b-0">
            <table className="table">
              <thead>
                <tr><th>ID</th><th>Time</th><th>Card</th><th>Merchant</th><th>Category</th><th className="num">Amount</th><th>Risk</th><th>Decision</th><th>Truth</th><th>Status</th><th>Review</th></tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.id} className="cursor-pointer" onClick={() => setSelectedId(r.id)}>
                    <td className="font-mono text-[12px] text-muted">#{r.id}</td>
                    <td className="font-mono text-[12px] text-ink-2">{fmtDateTime(r.txn_time, { year: false })}</td>
                    <td className="font-mono text-[12px]">{last4(r.card_last4)}</td>
                    <td className="max-w-[130px] truncate">{r.merchant}</td>
                    <td className="text-ink-2">{r.category_label || titleCase(r.category)}</td>
                    <td className="num font-medium">{money(r.amount)}</td>
                    <td><RiskChip score={r.risk_score} level={r.risk_level} /></td>
                    <td><DecisionBadge decision={r.decision} size="sm" /></td>
                    <td><TruthTag label={r.label} /></td>
                    <td><ReviewBadge status={r.review_status} /></td>
                    <td>
                      <div className="flex gap-1.5">
                        <button className="btn-secondary btn-sm !px-2" onClick={(e) => setSelectedId(r.id) || e.stopPropagation()} title="Open forensic record"><FileSearch size={13} /></button>
                        {r.review_status === "open" && (
                          <>
                            <button className="btn-danger btn-sm !px-2" title="Confirm fraud" aria-label="Confirm fraud" onClick={(e) => quickReview(e, r, "fraud")} disabled={rowBusy === r.id}><AlertTriangle size={13} /></button>
                            <button className="btn-success btn-sm !px-2" title="Mark genuine" aria-label="Mark genuine" onClick={(e) => quickReview(e, r, "genuine")} disabled={rowBusy === r.id}><CheckCircle2 size={13} /></button>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="p-5">
            <EmptyState icon={ClipboardList} title={status === "open" ? "No open cases" : "Nothing here"}>
              {status === "open" ? "Stream some transactions on the Live Monitor or score a suspicious one in the Tester: medium and high-risk decisions land here." : "Change the status filter or refresh."}
            </EmptyState>
          </div>
        )}
      </Card>

      <Drawer
        open={!!selectedId}
        onClose={() => setSelectedId(null)}
        title={selectedId ? `Case #${selectedId} · forensic audit record` : ""}
        subtitle={detail.data ? `${last4(detail.data.card_last4)} · ${detail.data.merchant} · ${fmtDateTime(detail.data.txn_time)}` : "Loading…"}
        width="max-w-[680px]"
      >
        {detail.loading && !detail.data ? (
          <div className="flex items-center gap-2 text-[12.5px] text-muted"><Spinner size={14} /> Loading record…</div>
        ) : detail.error ? (
          <Callout tone="warn">{detail.error.message}</Callout>
        ) : detail.data ? (
          <div className="space-y-4">
            {/* review state */}
            <div className="card p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <ReviewBadge status={detail.data.review_status} />
                  <span className="text-[11.5px] text-muted">source: {detail.data.source}</span>
                </div>
                <span className="font-mono text-[11px] text-muted">{detail.data.model_version}</span>
              </div>
              {(detail.data.review_note || detail.data.reviewed_at) && (
                <div className="mt-3 rounded-xl bg-slate-50 p-3 text-[12.5px]">
                  <div className="kpi-label mb-1">Review history</div>
                  <div>Reviewed at {detail.data.reviewed_at ? fmtDateTime(detail.data.reviewed_at) : "—"} (wall clock)</div>
                  {detail.data.review_note && <div className="mt-1 italic text-ink-2">“{detail.data.review_note}”</div>}
                </div>
              )}
              <div className="mt-2 text-[11.5px] text-muted">Logged at {fmtDateTime(detail.data.created_at)} (wall clock) · decision id #{detail.data.id}</div>
            </div>

            {detail.data.review_status === "open" && (
              <ReviewForm
                record={detail.data}
                onDone={() => {
                  setRefreshTick((t) => t + 1);
                  detail.reload();
                }}
              />
            )}

            <ExplanationPanel result={detail.data} compact />

            {detail.data.features && (
              <div className="card p-4">
                <h3 className="card-title">Feature snapshot</h3>
                <p className="card-sub mb-3">The exact feature vector scored at decision time: the verdict can be reproduced and justified in a dispute.</p>
                <div className="table-wrap max-h-[300px]">
                  <table className="table">
                    <thead><tr><th>Feature</th><th className="num">Value</th></tr></thead>
                    <tbody>
                      {Object.entries(detail.data.features).map(([k, v]) => (
                        <tr key={k}><td className="font-mono text-[12px]">{k}</td><td className="num font-mono text-[12px]">{fmtFeature(k, v)}</td></tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        ) : null}
      </Drawer>
    </div>
  );
}
