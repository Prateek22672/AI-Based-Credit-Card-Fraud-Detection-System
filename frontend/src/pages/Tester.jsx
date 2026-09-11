import { useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { CreditCard, FlaskConical, MapPin, Moon, Search, ShoppingCart, Sparkles, Zap } from "lucide-react";
import { api } from "../lib/api.js";
import { useAsync } from "../hooks/useAsync.js";
import { useApiStatus } from "../context/ApiStatus.jsx";
import { fmtUnix, int, last4, money, pct, titleCase } from "../lib/format.js";
import Card from "../components/ui/Card.jsx";
import { EmptyState, OfflineState } from "../components/ui/EmptyState.jsx";
import ExplanationPanel from "../components/explain/ExplanationPanel.jsx";
import { Spinner } from "../components/ui/Spinner.jsx";
import Callout from "../components/ui/Callout.jsx";
import { Pill } from "../components/ui/Badge.jsx";

const FALLBACK_CATEGORIES = [
  "entertainment", "food_dining", "gas_transport", "grocery_net", "grocery_pos", "health_fitness", "home", "kids_pets",
  "misc_net", "misc_pos", "personal_care", "shopping_net", "shopping_pos", "travel",
].map((c) => ({ value: c, label: titleCase(c) }));

function Toggle({ checked, onChange, label, hint }) {
  return (
    <label className="flex cursor-pointer items-start gap-3 rounded-xl border border-line bg-white px-3 py-2.5 hover:bg-slate-50">
      <span className="relative mt-0.5 inline-flex h-5 w-9 shrink-0 items-center">
        <input type="checkbox" className="peer sr-only" checked={checked} onChange={(e) => onChange(e.target.checked)} />
        <span className="absolute inset-0 rounded-full bg-slate-300 transition peer-checked:bg-primary" />
        <span className="absolute left-0.5 h-4 w-4 rounded-full bg-white shadow transition peer-checked:translate-x-4" />
      </span>
      <span>
        <span className="block text-[13px] font-medium text-ink">{label}</span>
        {hint && <span className="block text-[11.5px] text-muted">{hint}</span>}
      </span>
    </label>
  );
}

// ISO for a datetime-local input, from a unix timestamp (UTC = simulated clock).
const toLocalInput = (unix) => new Date(unix * 1000).toISOString().slice(0, 16);

export default function Tester() {
  const { online } = useApiStatus();
  const cards = useAsync(() => api.cards(200), [online], { enabled: online === true });
  const model = useAsync(() => api.model(), [online], { enabled: online === true });
  const categories = model.data?.categories?.length ? model.data.categories : FALLBACK_CATEGORIES;

  const [query, setQuery] = useState("");
  const [token, setToken] = useState(null);
  const card = useAsync(() => api.card(token), [token], { enabled: !!token, keep: false });

  const [form, setForm] = useState({ amount: 120, category: "grocery_pos", timestamp: "", distance_km: 5, known_merchant: true, commit: false });
  const [result, setResult] = useState(null);
  const [scoring, setScoring] = useState(false);
  const [error, setError] = useState(null);
  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const list = useMemo(() => {
    const q = query.trim().toLowerCase();
    const all = cards.data || [];
    if (!q) return all;
    return all.filter((c) => c.last4.includes(q) || `${c.city}, ${c.state}`.toLowerCase().includes(q));
  }, [cards.data, query]);

  useEffect(() => {
    if (!token && cards.data?.length) setToken(cards.data[0].token);
  }, [cards.data, token]);

  const c = card.data;

  const presets = [
    {
      key: "normal",
      icon: ShoppingCart,
      label: "Normal purchase",
      hint: "card's average, top category, known merchant",
      apply: () => ({ amount: Math.max(1, Math.round((c?.mean_amt || 60) * 100) / 100), category: c?.top_categories?.[0] || "grocery_pos", timestamp: "", distance_km: 5, known_merchant: true }),
    },
    {
      key: "night",
      icon: Moon,
      label: "Late-night online splurge",
      hint: "$1,150 · online shopping · 02:30",
      apply: () => {
        const base = c?.last_ts ? new Date(c.last_ts * 1000) : new Date(Date.UTC(2020, 3, 9));
        const d = new Date(Date.UTC(base.getUTCFullYear(), base.getUTCMonth(), base.getUTCDate() + 1, 2, 30));
        return { amount: 1150, category: "shopping_net", timestamp: d.toISOString().slice(0, 16), distance_km: 12, known_merchant: false };
      },
    },
    {
      key: "far",
      icon: MapPin,
      label: "Far from home",
      hint: "$400 · in-store shopping · 900 km away",
      apply: () => ({ amount: 400, category: "shopping_pos", timestamp: "", distance_km: 900, known_merchant: false }),
    },
  ];

  const score = async (f) => {
    if (!token) return;
    setScoring(true);
    setError(null);
    try {
      const body = {
        card_token: token,
        amount: Number(f.amount),
        category: f.category,
        known_merchant: !!f.known_merchant,
        distance_km: Number(f.distance_km),
        commit: !!f.commit,
      };
      if (f.timestamp) body.timestamp = `${f.timestamp}:00`;
      const r = await api.score(body);
      setResult(r);
      if (f.commit) card.reload();
    } catch (err) {
      setError(err.message);
    } finally {
      setScoring(false);
    }
  };
  const submit = (e) => {
    e?.preventDefault();
    score(form);
  };

  // Deep link for demos: /tester?preset=normal|night|far applies the preset and scores it.
  const [params] = useSearchParams();
  const autoRan = useRef(false);
  useEffect(() => {
    const p = presets.find((x) => x.key === params.get("preset"));
    if (!p || autoRan.current || !c || c.token !== token) return;
    autoRan.current = true;
    const f = { ...form, ...p.apply() };
    setForm(f);
    score(f);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [c, token, params]);

  if (online === false) return <OfflineState />;

  return (
    <div className="space-y-5">
      <Callout tone="info">
        Pick a real card from the feature store, describe a transaction and score it through the live engine. With{" "}
        <strong>commit</strong> off (default) the request is a what-if: the card&apos;s history is not changed, so you can try as many
        variants as you like.
      </Callout>

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-12">
        {/* card picker */}
        <Card title="Card" subtitle="Cards with the longest histories" className="xl:col-span-3" noPad>
          <div className="px-4 pb-3">
            <div className="relative">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
              <input className="input pl-8" placeholder="Search last 4 digits or city" value={query} onChange={(e) => setQuery(e.target.value)} />
            </div>
          </div>
          <div className="max-h-[420px] overflow-y-auto border-t border-line">
            {cards.loading && !cards.data ? (
              <div className="flex items-center gap-2 p-4 text-[12.5px] text-muted"><Spinner size={14} /> Loading cards…</div>
            ) : list.length ? (
              <ul>
                {list.map((k) => (
                  <li key={k.token}>
                    <button
                      onClick={() => { setToken(k.token); setResult(null); }}
                      className={`flex w-full items-center gap-3 border-b border-slate-100 px-4 py-2.5 text-left transition hover:bg-slate-50 ${token === k.token ? "bg-primary-soft hover:bg-primary-soft" : ""}`}
                    >
                      <span className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${token === k.token ? "bg-primary text-white" : "bg-slate-100 text-slate-500"}`}><CreditCard size={15} /></span>
                      <span className="min-w-0 flex-1">
                        <span className="flex items-center justify-between gap-2">
                          <span className="font-mono text-[13px] font-semibold">{last4(k.last4)}</span>
                          <span className="text-[11px] text-muted">{int(k.n_txns)} txns</span>
                        </span>
                        <span className="flex items-center justify-between gap-2 text-[11.5px] text-muted">
                          <span className="truncate">{k.city}, {k.state}</span>
                          <span>avg {money(k.mean_amt, { decimals: 0 })}</span>
                        </span>
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            ) : (
              <div className="p-4 text-[12.5px] text-muted">No cards match.</div>
            )}
          </div>
        </Card>

        {/* form */}
        <div className="space-y-5 xl:col-span-4">
          <Card title="Card context" subtitle={c ? `${last4(c.last4)} · ${c.city}, ${c.state}` : "Behaviour profile from the feature store"}>
            {card.loading && !c ? (
              <div className="flex items-center gap-2 text-[12.5px] text-muted"><Spinner size={14} /> Loading profile…</div>
            ) : c ? (
              <div className="grid grid-cols-2 gap-3 text-[12.5px]">
                <div className="rounded-xl bg-slate-50 p-3"><div className="kpi-label">Avg spend</div><div className="mt-1 text-[18px] font-bold">{money(c.mean_amt)}</div><div className="text-[11px] text-muted">± {money(c.std_amt, { decimals: 0 })} std</div></div>
                <div className="rounded-xl bg-slate-50 p-3"><div className="kpi-label">Txns / day</div><div className="mt-1 text-[18px] font-bold">{c.txns_per_day ?? "—"}</div><div className="text-[11px] text-muted">{int(c.n_txns)} in history</div></div>
                <div className="rounded-xl bg-slate-50 p-3"><div className="kpi-label">Night share</div><div className="mt-1 text-[18px] font-bold">{pct(c.night_share, 0)}</div><div className="text-[11px] text-muted">of past transactions 22:00–04:00</div></div>
                <div className="rounded-xl bg-slate-50 p-3"><div className="kpi-label">Merchants</div><div className="mt-1 text-[18px] font-bold">{int(c.n_merchants)}</div><div className="text-[11px] text-muted">distinct merchants used</div></div>
                <div className="col-span-2">
                  <div className="kpi-label mb-1.5">Top categories</div>
                  <div className="flex flex-wrap gap-1.5">{(c.top_categories || []).map((t) => <Pill key={t} tone="indigo">{titleCase(t)}</Pill>)}</div>
                </div>
                <div className="col-span-2 text-[11.5px] text-muted">Last transaction: {fmtUnix(c.last_ts)} · {c.recent?.length || 0} logged decisions on this card</div>
              </div>
            ) : (
              <div className="text-[12.5px] text-muted">Select a card.</div>
            )}
          </Card>

          <Card title="Transaction" subtitle="What should we score?">
            <div className="mb-4 grid grid-cols-1 gap-2 sm:grid-cols-3">
              {presets.map(({ key, icon: Icon, label, hint, apply }) => (
                <button key={key} type="button" onClick={() => setForm((f) => ({ ...f, ...apply() }))} className="flex flex-col items-start gap-1 rounded-xl border border-line bg-white px-3 py-2.5 text-left transition hover:border-indigo-300 hover:bg-primary-soft/50">
                  <span className="inline-flex items-center gap-1.5 text-[12.5px] font-semibold text-ink"><Icon size={14} className="text-primary" /> {label}</span>
                  <span className="text-[11px] leading-snug text-muted">{hint}</span>
                </button>
              ))}
            </div>
            <form onSubmit={submit} className="space-y-3.5">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="label" htmlFor="amount">Amount (USD)</label>
                  <input id="amount" type="number" min="0.01" max="100000" step="0.01" className="input" value={form.amount} onChange={(e) => set("amount", e.target.value)} required />
                </div>
                <div>
                  <label className="label" htmlFor="category">Category</label>
                  <select id="category" className="input" value={form.category} onChange={(e) => set("category", e.target.value)}>
                    {categories.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                  </select>
                </div>
              </div>
              <div>
                <label className="label" htmlFor="ts">Transaction date &amp; time <span className="font-normal text-muted">(optional)</span></label>
                <div className="flex gap-2">
                  <input id="ts" type="datetime-local" className="input" value={form.timestamp} onChange={(e) => set("timestamp", e.target.value)} />
                  {form.timestamp && <button type="button" className="btn-secondary btn-sm" onClick={() => set("timestamp", "")}>Clear</button>}
                </div>
                <p className="mt-1 text-[11.5px] text-muted">Empty = 1 h after the card&apos;s last transaction{c?.last_ts ? ` (${toLocalInput(c.last_ts + 3600).replace("T", " ")})` : ""}.</p>
              </div>
              <div>
                <label className="label" htmlFor="dist">Distance from home: <span className="font-mono text-primary">{Number(form.distance_km).toLocaleString("en-US")} km</span></label>
                <input id="dist" type="range" min="0" max="2000" step="5" value={form.distance_km} onChange={(e) => set("distance_km", e.target.value)} className="w-full accent-indigo-600" />
                <div className="flex justify-between text-[10.5px] text-muted"><span>0 km (home)</span><span>500</span><span>1,000</span><span>1,500</span><span>2,000 km</span></div>
              </div>
              <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                <Toggle checked={form.known_merchant} onChange={(v) => set("known_merchant", v)} label="Merchant used before" hint="reuse one of the card's past merchants" />
                <Toggle checked={form.commit} onChange={(v) => set("commit", v)} label="Commit to history" hint="off = what-if (card state unchanged)" />
              </div>
              {error && <Callout tone="warn">{error}</Callout>}
              <button type="submit" className="btn-primary w-full" disabled={scoring || !token}>
                {scoring ? <Spinner size={14} className="border-white/40 border-t-white" /> : <Zap size={15} />} Score transaction
              </button>
            </form>
          </Card>
        </div>

        {/* result */}
        <div className="xl:col-span-5">
          {result ? (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h2 className="text-[15px] font-semibold inline-flex items-center gap-2"><Sparkles size={16} className="text-primary" /> Result</h2>
                <span className="text-[11.5px] text-muted">{form.commit ? "committed to history" : "what-if · history unchanged"}</span>
              </div>
              <ExplanationPanel result={result} showTruth={false} />
            </div>
          ) : (
            <EmptyState icon={FlaskConical} title="No result yet" className="h-full min-h-[360px]">
              Choose a card, pick a preset or fill in the form, then press <strong>Score transaction</strong>. The gauge, model votes and SHAP reasons appear here.
            </EmptyState>
          )}
        </div>
      </div>
    </div>
  );
}
