import { ArrowDown, ArrowRight, Boxes, Database, GitMerge, Globe, Layers, MonitorSmartphone, Server, Smartphone, Terminal } from "lucide-react";
import Card from "../components/ui/Card.jsx";

function Box({ icon: Icon, title, sub, tone = "indigo", className = "" }) {
  const tones = {
    indigo: "border-indigo-200 bg-primary-soft text-indigo-900",
    violet: "border-violet-200 bg-accent-soft text-violet-900",
    teal: "border-teal-200 bg-teal-50 text-teal-900",
    slate: "border-slate-200 bg-slate-50 text-slate-800",
    dark: "border-navy-900 bg-navy-900 text-white",
  };
  return (
    <div className={`rounded-xl border px-3 py-3 ${tones[tone]} ${className}`}>
      <div className="flex items-center gap-2 text-[13px] font-semibold"><Icon size={16} /> {title}</div>
      {sub && <div className="mt-0.5 text-[11.5px] opacity-80 leading-snug">{sub}</div>}
    </div>
  );
}

// Mirrors fraudlens/policy.py (kept static so the page also works on static hosting).
const LAYERS = [
  {
    n: 1,
    title: "ML risk engine",
    tone: "indigo",
    text: "XGBoost + Random Forest + Isolation Forest, stacked into a calibrated probability. Catches the fraud patterns present in the training labels, with ~98% recall on the unseen test quarter.",
  },
  {
    n: 2,
    title: "Novelty alarm (N1)",
    tone: "teal",
    text: "If the Isolation Forest finds a transaction more unusual than 99.95% of normal spending, it goes to step-up verification even when the supervised models see no known pattern. Stacking alone gives the anomaly score almost no weight, because it is fitted on known fraud only.",
  },
  {
    n: 3,
    title: "Documented policy rules",
    tone: "amber",
    text: "Parameterised alerts on velocity and geo-location, as required by the RBI Master Direction on Digital Payment Security Controls (2021, paras 36-37), which also allows risk-based step-up authentication (para 34).",
  },
];
const RULES = [
  ["P1", "Burst then jump", "3+ transactions in the past hour, then an amount 5x or more the card's average"],
  ["P2", "Impossible travel", "500 km+ from the previous transaction at an implied speed above 800 km/h (cloned card)"],
  ["P3", "Micro-charge burst", "A tiny (< $5) online charge after 3+ others in the past hour: the card-testing pattern"],
  ["N1", "Novelty alarm", "Anomaly percentile at least 99.95% vs genuine training transactions"],
];

const STACK = [
  ["Python 3.11 · pandas · NumPy", "Data pipeline & feature store", "Fast columnar processing of 1.3 M transactions; the feature store is plain Python objects, pickled as the API snapshot."],
  ["XGBoost", "Main supervised detector", "Top PR-AUC among single models and ~2 ms per prediction; exact TreeSHAP is built into the predictor, so explanations need no extra library at run time."],
  ["scikit-learn Random Forest", "Second supervised detector", "Different inductive bias (bagging) gives the stack an independent opinion."],
  ["scikit-learn Isolation Forest", "Unsupervised novelty detector", "Trained on genuine transactions only: catches behaviour unlike normal spending even without labelled examples."],
  ["Logistic-regression meta-learner", "Stacking + calibration", "Fitted on the untouched validation quarter, so the output is a calibrated probability."],
  ["Policy rules + novelty alarm", "Safety layer", "Documented, parameterised rules (RBI 2021) and an Isolation-Forest novelty route cover attacks absent from the training data."],
  ["SHAP (TreeSHAP)", "Explainability", "Exact per-feature contributions, grouped into human sentences (reason codes)."],
  ["FastAPI · Pydantic · Uvicorn", "REST API", "Type-checked JSON API with auto-generated Swagger docs; async server handles the dashboard's polling."],
  ["SQLAlchemy · SQLite / PostgreSQL", "Decision log", "Every decision stored with model version, feature vector and explanation; swap the URL for PostgreSQL in production."],
  ["React 18 · React Router", "Dashboard", "Component model suits a live-updating operations UI; routing keeps every page linkable for the report."],
  ["Vite · Tailwind CSS v4", "Build & styling", "Instant dev server, small hashed bundles; utility CSS keeps the design system consistent."],
  ["Recharts · lucide-react", "Charts & icons", "SVG charts that print cleanly; a single consistent icon set."],
  ["Matplotlib · python-docx", "Report figures & documents", "Figures regenerated from result JSON; the Word/PDF report is built from the same numbers."],
];

const RUN = [
  ["Create the environment", "python -m venv .venv\n.venv\\Scripts\\pip install -r requirements.txt"],
  ["Optional: re-run the research (the trained models and held-out test data are already in artifacts/)", "python -m fraudlens.download\npython -m fraudlens.pipeline all"],
  ["Start the API (serves the dashboard build when frontend/dist exists)", "uvicorn fraudlens.api.main:app --port 8000"],
  ["Dashboard: development server with hot reload", "cd frontend\nnpm install\nnpm run dev          # http://localhost:5173 (proxies /api to :8000)"],
  ["Dashboard: production build served by the API", "npm run build        # writes frontend/dist (and syncs results/figures into public/data)"],
];

export default function About() {
  return (
    <div className="space-y-5">
      <Card title="System architecture" subtitle="Request path from the dashboard to an explained, logged decision">
        <div className="grid grid-cols-1 gap-3 lg:grid-cols-[1fr_auto_1.6fr_auto_1fr] lg:items-center">
          <div className="space-y-2">
            <Box icon={MonitorSmartphone} title="React dashboard" sub="Vite + Tailwind · analysts, reviewers, demo" tone="indigo" />
            <div className="text-center text-[11px] text-muted">HTTPS · JSON · optional X-API-Key</div>
          </div>
          <ArrowRight size={18} className="hidden text-slate-300 lg:block" />
          <div className="space-y-2">
            <Box icon={Server} title="FastAPI service" sub="/api/score · /api/stream · /api/scenarios · /api/transactions · /api/results" tone="dark" />
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
              <Box icon={Database} title="Feature store" sub="per-card state → 39 behavioural features, updated after each transaction" tone="teal" />
              <div className="rounded-xl border border-violet-200 bg-accent-soft p-2.5">
                <div className="flex items-center gap-2 text-[13px] font-semibold text-violet-900"><Boxes size={16} /> Hybrid engine</div>
                <div className="mt-2 grid grid-cols-3 gap-1.5 text-center text-[10.5px] font-semibold">
                  <span className="rounded-lg bg-white/80 px-1 py-1.5 text-indigo-800">XGBoost</span>
                  <span className="rounded-lg bg-white/80 px-1 py-1.5 text-violet-800">Random Forest</span>
                  <span className="rounded-lg bg-white/80 px-1 py-1.5 text-teal-800">Isolation Forest</span>
                </div>
                <div className="my-1 flex justify-center text-violet-400"><ArrowDown size={14} /></div>
                <div className="rounded-lg bg-white/80 px-2 py-1.5 text-center text-[11px] font-semibold text-violet-900"><GitMerge size={12} className="mr-1 inline" />Meta-learner → probability → risk score → decision</div>
              </div>
            </div>
            <Box icon={Layers} title="SHAP explainer" sub="TreeSHAP contributions → grouped reason codes (why flagged / looks genuine)" tone="violet" />
          </div>
          <ArrowRight size={18} className="hidden text-slate-300 lg:block" />
          <Box icon={Database} title="Decision log" sub="SQLite (dev) / PostgreSQL (prod): model version, feature snapshot, reasons, analyst review" tone="slate" />
        </div>
        <p className="mt-4 text-[12.5px] text-muted">
          Card numbers never leave the server: the API addresses cards by a keyed HMAC token and shows only the last four digits. State-changing endpoints can be protected with <span className="kbd">FRAUDLENS_API_KEY</span>; CORS origins are set with <span className="kbd">FRAUDLENS_CORS_ORIGINS</span>.
        </p>
      </Card>

      <Card title="Defence in depth" subtitle="Three layers decide together; the safety layers can only raise a decision, never approve">
        <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
          {LAYERS.map((l) => (
            <div
              key={l.n}
              className={`rounded-xl border p-3.5 ${
                l.tone === "indigo" ? "border-indigo-200 bg-primary-soft" : l.tone === "teal" ? "border-teal-200 bg-teal-50" : "border-amber-200 bg-amber-50"
              }`}
            >
              <div className="flex items-center gap-2 text-[13.5px] font-semibold text-ink">
                <span className="flex h-6 w-6 items-center justify-center rounded-full bg-white text-[12px] font-bold">{l.n}</span>
                {l.title}
              </div>
              <p className="mt-1.5 text-[12.5px] leading-relaxed text-ink-2">{l.text}</p>
            </div>
          ))}
        </div>
        <div className="table-wrap mt-4">
          <table className="table">
            <thead><tr><th>Rule</th><th>Name</th><th>Fires when</th><th>Action</th></tr></thead>
            <tbody>
              {RULES.map(([id, name, when]) => (
                <tr key={id}>
                  <td><span className="tag bg-amber-500 font-bold text-white">{id}</span></td>
                  <td className="font-medium">{name}</td>
                  <td className="whitespace-normal text-[12.5px] text-ink-2">{when}</td>
                  <td className="text-[12.5px] text-ink-2">at least STEP-UP</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-3 text-[12px] text-muted">
          Measured on the unseen test quarter, the safety layer adds well under one extra step-up per day, and it is what catches
          attacks that never appear in the training data (card testing, cloned cards). See Results → Safety layer and Results → Unseen fraud.
        </p>
      </Card>

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-5">
        <Card title="Technology stack" subtitle="What each part uses and why" className="xl:col-span-3" noPad>
          <div className="table-wrap rounded-t-none border-x-0 border-b-0">
            <table className="table">
              <thead><tr><th>Technology</th><th>Role</th><th>Why</th></tr></thead>
              <tbody>
                {STACK.map(([tech, role, why]) => (
                  <tr key={tech}><td className="font-medium">{tech}</td><td className="text-ink-2">{role}</td><td className="whitespace-normal text-[12.5px] text-muted">{why}</td></tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>

        <Card title="Why a web platform and not a mobile app" className="xl:col-span-2">
          <ul className="space-y-3 text-[13px] text-ink-2">
            <li className="flex gap-3"><Server size={16} className="mt-0.5 shrink-0 text-primary" /><span><strong>Scoring must run server-side, inside the payment authorisation path.</strong> The bank's switch calls the API for every transaction and needs an answer within its authorisation budget (well under a second), before the merchant is told yes or no.</span></li>
            <li className="flex gap-3"><Database size={16} className="mt-0.5 shrink-0 text-primary" /><span><strong>It needs every card's history.</strong> Velocity, spend-vs-average and travel-speed features come from the card's past transactions, which only the server holds. A phone app can only see its own device.</span></li>
            <li className="flex gap-3"><Globe size={16} className="mt-0.5 shrink-0 text-primary" /><span><strong>A model on the phone would be exposed.</strong> Shipping the model to devices lets attackers probe and reverse-engineer it; on the server it stays private and can be retrained centrally.</span></li>
            <li className="flex gap-3"><MonitorSmartphone size={16} className="mt-0.5 shrink-0 text-primary" /><span><strong>The users are analysts and reviewers.</strong> They need large tables, charts and side-by-side explanations: a responsive web dashboard fits that job and also works on a phone browser.</span></li>
            <li className="flex gap-3"><Smartphone size={16} className="mt-0.5 shrink-0 text-teal" /><span><strong>A customer-facing mobile app can be added later</strong> on the same API, for push alerts and one-tap "it was me / it wasn't me" step-up confirmation.</span></li>
          </ul>
        </Card>
      </div>

      <Card title="How to run" subtitle="From a clean checkout on Windows (PowerShell); use forward slashes and `source .venv/bin/activate` on Linux/macOS">
        <ol className="space-y-3">
          {RUN.map(([title, cmd], i) => (
            <li key={i}>
              <div className="mb-1.5 flex items-center gap-2 text-[13px] font-semibold"><span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary-soft text-[11.5px] font-bold text-primary">{i + 1}</span>{title}</div>
              <pre className="code"><Terminal size={12} className="mr-2 inline text-slate-400" />{cmd}</pre>
            </li>
          ))}
        </ol>
        <p className="mt-4 text-[12.5px] text-muted">
          Environment variables — API: <span className="kbd">FRAUDLENS_DB_URL</span>, <span className="kbd">FRAUDLENS_API_KEY</span>, <span className="kbd">FRAUDLENS_CORS_ORIGINS</span>, <span className="kbd">FRAUDLENS_TOKEN_SECRET</span>. Dashboard: <span className="kbd">VITE_API_URL</span>, <span className="kbd">VITE_API_KEY</span>, <span className="kbd">VITE_PROXY_TARGET</span> (see frontend/README.md).
        </p>
      </Card>
    </div>
  );
}
