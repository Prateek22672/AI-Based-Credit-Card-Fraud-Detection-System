// Data layer. API base is same-origin by default (FastAPI serves the build);
// set VITE_API_URL for static hosting and VITE_API_KEY if the API requires it.
export const API = (import.meta.env.VITE_API_URL || "").replace(/\/$/, "");
const API_KEY = import.meta.env.VITE_API_KEY;

export class ApiError extends Error {
  constructor(message, status = 0, detail = null) {
    super(message);
    this.name = "ApiError";
    this.status = status; // 0 = network / backend unreachable
    this.detail = detail;
  }
  get offline() {
    return this.status === 0;
  }
}

function isJson(res) {
  return (res.headers.get("content-type") || "").includes("application/json");
}

async function request(path, { method = "GET", body, signal } = {}) {
  const headers = { Accept: "application/json" };
  if (method === "POST") {
    headers["Content-Type"] = "application/json";
    if (API_KEY) headers["X-API-Key"] = API_KEY;
  }
  let res;
  try {
    res = await fetch(`${API}${path}`, { method, headers, body, signal });
  } catch (e) {
    if (e?.name === "AbortError") throw e;
    throw new ApiError("Backend offline: the FraudLens API is not reachable.", 0);
  }
  // A static host with an SPA fallback answers unknown paths with index.html (200):
  // treat a non-JSON answer as "no API here".
  if (!isJson(res)) {
    if (res.status === 404 || res.ok) throw new ApiError("Backend offline: no API at this origin.", 0);
  }
  if (!res.ok) {
    let detail = null;
    try {
      const j = await res.json();
      detail = typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail);
    } catch {
      /* ignore */
    }
    throw new ApiError(detail || `${res.status} ${res.statusText}`, res.status, detail);
  }
  return res.json();
}

export const get = (path, opts) => request(path, opts);
export const post = (path, body, opts) =>
  request(path, { ...opts, method: "POST", body: body === undefined ? undefined : JSON.stringify(body) });

const qs = (params = {}) =>
  Object.entries(params)
    .filter(([, v]) => v !== undefined && v !== null && v !== "")
    .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`)
    .join("&");

export const api = {
  health: (opts) => get("/api/health", opts),
  model: () => get("/api/model"),
  cards: (limit = 200) => get(`/api/cards?limit=${limit}`),
  card: (token) => get(`/api/cards/${encodeURIComponent(token)}`),
  score: (body) => post("/api/score", body),
  streamNext: (n) => post(`/api/stream/next?n=${n}`),
  streamStatus: () => get("/api/stream/status"),
  reset: () => post("/api/reset"),
  stats: () => get("/api/stats"),
  transactions: (params) => get(`/api/transactions?${qs(params)}`),
  transaction: (id) => get(`/api/transactions/${id}`),
  review: (id, body) => post(`/api/transactions/${id}/review`, body),
  scenarios: () => get("/api/scenarios"),
  runScenario: (id, cardToken) => post(`/api/scenarios/${encodeURIComponent(id)}/run`, cardToken ? { card_token: cardToken } : {}),
};

// ---------------------------------------------------------------- research data
// Result sets: API first (always fresh), then the static copy made by `npm run sync-data`.
const resultCache = new Map();

export async function fetchResult(name) {
  if (resultCache.has(name)) return resultCache.get(name);
  const p = (async () => {
    try {
      const data = await get(`/api/results/${name}`);
      return { data, source: "api", error: null };
    } catch (e) {
      const notYet = e instanceof ApiError && e.status === 404;
      try {
        const res = await fetch(`/data/results/${name}.json`, { headers: { Accept: "application/json" } });
        if (res.ok && isJson(res)) return { data: await res.json(), source: "static", error: null };
      } catch {
        /* ignore */
      }
      return { data: null, source: null, error: notYet ? "not_generated" : e?.message || "unavailable" };
    }
  })();
  resultCache.set(name, p);
  const r = await p;
  if (!r.data) resultCache.delete(name); // let a later visit retry once the file appears
  return r;
}

export function figureUrls(name) {
  return [`${API}/figures/${name}.png`, `/data/figures/${name}.png`];
}
