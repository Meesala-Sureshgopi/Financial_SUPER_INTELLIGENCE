import { useEffect, useMemo, useState } from 'react';
import { getPortfolio } from '../api';
import StockChart from './StockChart';

function formatCurrency(value) {
  return `₹${Number(value || 0).toLocaleString('en-IN', { maximumFractionDigits: 2 })}`;
}

function PortfolioView() {
  const [portfolio, setPortfolio] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedTicker, setSelectedTicker] = useState(null);

  useEffect(() => {
    loadPortfolio();
    const handlePortfolioUpdated = () => loadPortfolio();
    window.addEventListener('portfolio:updated', handlePortfolioUpdated);
    return () => window.removeEventListener('portfolio:updated', handlePortfolioUpdated);
  }, []);

  async function loadPortfolio() {
    setLoading(true);
    try {
      const data = await getPortfolio();
      setPortfolio(data);

      const tickers = Object.keys(data.holdings || {});
      if (tickers.length > 0) {
        setSelectedTicker((current) => current || tickers[0]);
      }
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  }

  const holdings = useMemo(
    () => Object.entries(portfolio?.holdings || {}),
    [portfolio]
  );

  const selectedHolding = selectedTicker ? portfolio?.holdings?.[selectedTicker] : null;

  if (loading) {
    return (
      <div className="loader" style={{ padding: '4rem', justifyContent: 'center' }}>
        <div className="loader-dot"></div>
        <div className="loader-dot"></div>
        <div className="loader-dot"></div>
      </div>
    );
  }

  return (
    <div className="fade-in portfolio-page">
      <div className="page-header">
        <div>
          <h2>Portfolio Intelligence</h2>
          <div className="subtitle">Select any holding to inspect live price action, P&amp;L and trend structure.</div>
        </div>
      </div>

      <div className="stats-row">
        <div className="glass-card stat-card" style={{ background: 'var(--neon-green-dim)' }}>
          <div className="stat-label">Total Value</div>
          <div className="stat-value" style={{ color: 'var(--neon-green)' }}>{formatCurrency(portfolio?.total_value)}</div>
        </div>
        <div className="glass-card stat-card">
          <div className="stat-label">Total P&amp;L</div>
          <div className={`stat-value ${portfolio?.total_pnl >= 0 ? 'positive' : 'negative'}`}>
            {portfolio?.total_pnl >= 0 ? '+' : ''}{formatCurrency(Math.abs(portfolio?.total_pnl || 0))}
          </div>
        </div>
        <div className="glass-card stat-card">
          <div className="stat-label">Holdings</div>
          <div className="stat-value">{holdings.length}</div>
        </div>
        <div className="glass-card stat-card">
          <div className="stat-label">Risk Score</div>
          <div className="stat-value" style={{ color: 'var(--neon-blue)' }}>MEDIUM</div>
        </div>
      </div>

      <div className="portfolio-layout">
        <div className="glass-card portfolio-list-panel">
          <div className="portfolio-panel-header">
            <h3 className="section-title">Holdings</h3>
            <span className="portfolio-panel-hint">Tap a row to inspect</span>
          </div>

          <div className="portfolio-list">
            {holdings.map(([ticker, data]) => (
              <button
                key={ticker}
                className={`portfolio-row-card ${selectedTicker === ticker ? 'active' : ''}`}
                onClick={() => setSelectedTicker(ticker)}
                type="button"
              >
                <div className="portfolio-row-main">
                  <div>
                    <strong>{ticker}</strong>
                    <span>{data.sector || 'Unknown sector'}</span>
                  </div>
                  <div className="portfolio-row-price">
                    <strong>{formatCurrency(data.current_price)}</strong>
                    <span className={data.pnl_pct >= 0 ? 'positive' : 'negative'}>
                      {data.pnl_pct >= 0 ? '+' : ''}{Number(data.pnl_pct || 0).toFixed(2)}%
                    </span>
                  </div>
                </div>

                <div className="portfolio-row-sub">
                  <span>Qty {data.qty}</span>
                  <span>Avg {formatCurrency(data.avg_price)}</span>
                  <span>P&amp;L {data.pnl >= 0 ? '+' : '-'}{formatCurrency(Math.abs(data.pnl || 0))}</span>
                </div>
              </button>
            ))}
          </div>
        </div>

        <div className="glass-card portfolio-detail-panel">
          {selectedHolding ? (
            <>
              <div className="portfolio-detail-header">
                <div>
                  <div className="badge badge-accent">Selected Holding</div>
                  <h3 className="portfolio-detail-title">{selectedTicker}</h3>
                  <p>{selectedHolding.sector || 'Unknown sector'} exposure with live pricing.</p>
                </div>
                <div className="portfolio-detail-pnl">
                  <span>P&amp;L</span>
                  <strong className={selectedHolding.pnl >= 0 ? 'positive' : 'negative'}>
                    {selectedHolding.pnl >= 0 ? '+' : '-'}{formatCurrency(Math.abs(selectedHolding.pnl || 0))}
                  </strong>
                </div>
              </div>

              <div className="portfolio-detail-metrics">
                <div className="portfolio-detail-metric">
                  <span>Quantity</span>
                  <strong>{selectedHolding.qty}</strong>
                </div>
                <div className="portfolio-detail-metric">
                  <span>Avg Price</span>
                  <strong>{formatCurrency(selectedHolding.avg_price)}</strong>
                </div>
                <div className="portfolio-detail-metric">
                  <span>Live Price</span>
                  <strong>{formatCurrency(selectedHolding.current_price)}</strong>
                </div>
                <div className="portfolio-detail-metric">
                  <span>Market Value</span>
                  <strong>{formatCurrency(selectedHolding.market_value)}</strong>
                </div>
              </div>

              <StockChart
                ticker={selectedTicker}
                height={360}
                compact={false}
                color={selectedHolding.pnl_pct >= 0 ? '#15c47e' : '#ef5350'}
              />
            </>
          ) : (
            <div className="empty-state">
              <div className="icon">📊</div>
              <h3>No holding selected</h3>
              <p>Pick a stock from the left side to open its full market view here.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default PortfolioView;
