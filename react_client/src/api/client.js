// Thin wrapper around the FastAPI backend.
// Override the base URL with VITE_API_BASE in .env.local for non-default hosts.
const BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

function qs(filters = {}, extra = {}) {
  const params = new URLSearchParams();
  if (filters.stores?.length)  params.set("stores",   filters.stores.join(","));
  if (filters.regions?.length) params.set("regions",  filters.regions.join(","));
  if (filters.states?.length)  params.set("states",   filters.states.join(","));
  if (filters.date_from)       params.set("date_from", filters.date_from);
  if (filters.date_to)         params.set("date_to",   filters.date_to);
  if (filters.reasons?.length) params.set("reasons",   filters.reasons.join("|"));
  for (const [k, v] of Object.entries(extra)) {
    if (v !== undefined && v !== null && v !== "") params.set(k, String(v));
  }
  const s = params.toString();
  return s ? `?${s}` : "";
}

// Tiny in-memory cache so re-renders don't re-fire GETs for the same params.
// Keyed by full URL. TTL=120s. POSTs are never cached.
const _cache = new Map();
const TTL_MS = 120_000;

async function getJSON(path) {
  const now = Date.now();
  const entry = _cache.get(path);
  if (entry && now - entry.t < TTL_MS) return entry.v;
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`GET ${path} failed: ${res.status}`);
  const v = await res.json();
  _cache.set(path, { v, t: now });
  return v;
}

async function postJSON(path, body) {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`POST ${path} failed: ${res.status} ${text}`);
  }
  return res.json();
}

export const api = {
  // ── analytics ────────────────────────────────────────────────────────────
  getFilters:        ()                       => getJSON(`/api/analytics/filters`),
  getOverview:       (f = {})                 => getJSON(`/api/analytics/overview${qs(f)}`),
  getWeekly:         (f = {})                 => getJSON(`/api/analytics/trends/weekly${qs(f)}`),
  getDow:            (f = {})                 => getJSON(`/api/analytics/trends/dow${qs(f)}`),
  getStores:         (f = {})                 => getJSON(`/api/analytics/stores${qs(f)}`),
  getRegions:        (f = {})                 => getJSON(`/api/analytics/regions${qs(f)}`),
  getStates:         (f = {})                 => getJSON(`/api/analytics/states${qs(f)}`),
  getReasons:        (f = {})                 => getJSON(`/api/analytics/reasons${qs(f)}`),
  getSubReasons:     (f = {})                 => getJSON(`/api/analytics/reasons/sub${qs(f)}`),
  getLag:            (f = {})                 => getJSON(`/api/analytics/cancels/lag${qs(f)}`),
  getReasonDow:      (f = {})                 => getJSON(`/api/analytics/heatmap/reason-dow${qs(f)}`),
  getStoreDept:      (f = {}, topN = 15)      => getJSON(`/api/analytics/heatmap/store-dept${qs(f, { top_stores: topN })}`),
  getProducts:       (f = {}, topN = 20, sortBy = "qty") =>
                                                 getJSON(`/api/analytics/products${qs(f, { top_n: topN, sort_by: sortBy })}`),
  getProductStatus:  (f = {}, windowDays = 30) => getJSON(`/api/analytics/products/status${qs(f, { window_days: windowDays })}`),
  getCategories:     (f = {})                 => getJSON(`/api/analytics/categories${qs(f)}`),
  getInventory:      (f = {})                 => getJSON(`/api/analytics/inventory${qs(f)}`),
  getSaveRate:       (f = {})                 => getJSON(`/api/analytics/save-rate${qs(f)}`),
  getDataQuality:    (f = {})                 => getJSON(`/api/analytics/data-quality${qs(f)}`),
  getInsights:       (f = {})                 => getJSON(`/api/analytics/insights${qs(f)}`),

  // ── ai ────────────────────────────────────────────────────────────────────
  getModels:         ()                       => getJSON(`/api/insights/models`),
  getNarrative:      (f = {})                 => getJSON(`/api/insights/narrative${qs(f)}`),
  getRecommendations:(f = {})                 => getJSON(`/api/insights/recommendations${qs(f)}`),
  getSuggestions:    (f = {})                 => getJSON(`/api/insights/suggestions${qs(f)}`),
  queryInsights:     (body)                   => postJSON(`/api/insights/query`, body),

  // ── cache management ─────────────────────────────────────────────────────
  clearCache: () => _cache.clear(),
};
