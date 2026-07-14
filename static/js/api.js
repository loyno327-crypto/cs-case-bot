// API-клиент. Передаёт Telegram initData в каждом запросе через заголовок.
const tg = window.Telegram ? window.Telegram.WebApp : null;
const INIT_DATA = tg && tg.initData ? tg.initData : "";

async function apiFetch(path, options = {}) {
  const headers = {
    "Content-Type": "application/json",
    "X-Init-Data": INIT_DATA,
    ...(options.headers || {}),
  };
  const res = await fetch(path, { ...options, headers });
  if (!res.ok) {
    let detail = res.statusText;
    try { detail = (await res.json()).detail || detail; } catch (e) {}
    throw new Error(detail);
  }
  return res.json();
}

const API = {
  state: () => apiFetch("/api/state"),
  click: (taps) => apiFetch("/api/click", { method: "POST", body: JSON.stringify({ taps }) }),
  daily: () => apiFetch("/api/daily", { method: "POST" }),
  boost: () => apiFetch("/api/boost", { method: "POST" }),
  upgrade: (kind) => apiFetch("/api/upgrade", { method: "POST", body: JSON.stringify({ kind }) }),
  cases: () => apiFetch("/api/cases"),
  openCase: (case_id) => apiFetch("/api/cases/open", { method: "POST", body: JSON.stringify({ case_id }) }),
  inventory: () => apiFetch("/api/inventory"),
  sell: (inv_id) => apiFetch("/api/inventory/sell", { method: "POST", body: JSON.stringify({ inv_id }) }),
  items: () => apiFetch("/api/items"),
  upgradeItem: (inv_id, target_item_id) =>
    apiFetch("/api/items/upgrade", { method: "POST", body: JSON.stringify({ inv_id, target_item_id }) }),
  contract: (inv_ids) => apiFetch("/api/contract", { method: "POST", body: JSON.stringify({ inv_ids }) }),
  battle: (case_id) => apiFetch("/api/battle", { method: "POST", body: JSON.stringify({ case_id }) }),
  recentDrops: () => apiFetch("/api/recent-drops"),
  topPlayers: (sort) => apiFetch(`/api/top-players?sort=${sort}`),
};
