/**
 * API Utility Module
 * Centralized API caller for all backend endpoints.
 */
const BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '');

export async function apiFetch(endpoint, options = {}) {
  const url = BASE_URL ? `${BASE_URL}${endpoint}` : endpoint;
  const config = {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  };
  const response = await fetch(url, config);
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `API Error: ${response.status}`);
  }
  return response.json();
}

// ── Endpoints ─────────────────────────────────────────────────────
export const queryAgent = (query) =>
  apiFetch('/api/query', { method: 'POST', body: JSON.stringify({ query }) });

export const getSignals = () => apiFetch('/api/alerts/history');
export const refreshLiveSignals = () =>
  apiFetch('/api/alerts/live-refresh', {
    method: 'POST',
  });
export const getPortfolio = () => apiFetch('/api/portfolio');
export const getLivePrice = (ticker) => apiFetch(`/api/price/${ticker}`);
export const getStockInfo = (ticker) => apiFetch(`/api/stock/${ticker}`);
export const getChartData = (ticker, range = '1mo') =>
  apiFetch(`/api/chart/${ticker}?range=${encodeURIComponent(range)}`);
export const analyzeLive = (ticker, options = {}) => 
  apiFetch('/api/analyze', { 
    method: 'POST', 
    body: JSON.stringify({ ticker, user_id: 'demo_user_123' }),
    ...options,
  });
export const addToPortfolio = ({ ticker, quantity, price }) =>
  apiFetch('/api/portfolio/holdings', {
    method: 'POST',
    body: JSON.stringify({
      user_id: 'demo_user_123',
      ticker,
      qty: quantity,
      avg_price: price,
    }),
  });
export const removeFromPortfolio = ({ ticker, quantity }) =>
  apiFetch('/api/portfolio/holdings/remove', {
    method: 'POST',
    body: JSON.stringify({
      user_id: 'demo_user_123',
      ticker,
      qty: quantity,
    }),
  });
export const getMarketMovers = () => apiFetch('/api/market/movers');
export const getStockNews = (ticker) => apiFetch(`/api/news/${ticker}`);
export const healthCheck = () => apiFetch('/api/health');
export const searchTickers = (q) => apiFetch(`/api/tickers/search?q=${q}`);

export const setAlert = (ticker, targetPrice, direction = 'below') =>
  apiFetch('/api/alert', {
    method: 'POST',
    body: JSON.stringify({ ticker, target_price: targetPrice, direction }),
  });

export const getAlerts = () => apiFetch('/api/alerts');

// ── Scenario Endpoints ───────────────────────────────────────────
export const runScenario1 = (ticker = 'BRITANNIA') =>
  apiFetch(`/api/scenario/1?ticker=${ticker}`, { method: 'POST' });

export const runScenario2 = (ticker = 'TCS') =>
  apiFetch(`/api/scenario/2?ticker=${ticker}`, { method: 'POST' });

export const runScenario3 = () =>
  apiFetch('/api/scenario/3', { method: 'POST' });
