import React, { useEffect, useRef, useState } from 'react';
import { AnalysisResult } from '../types';
import StockChart from './StockChart';
import { addToPortfolio, analyzeLive, getSignals, refreshLiveSignals, removeFromPortfolio, searchTickers } from '../api';

const FIFTEEN_MINUTES = 15 * 60 * 1000;

function formatSignalTime(timestamp?: string) {
  if (!timestamp) return 'Just now';
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) return 'Just now';
  return date.toLocaleString([], {
    hour: 'numeric',
    minute: '2-digit',
    day: 'numeric',
    month: 'short',
  });
}

function formatSignalImpactLabel(estimatedPnl?: string) {
  if (!estimatedPnl) return 'Watchlist Alert';
  const normalized = estimatedPnl.replace(/\s/g, '').toLowerCase();
  if (
    normalized === '₹0.0'.toLowerCase() ||
    normalized === '₹0'.toLowerCase() ||
    normalized === '-₹0.0'.toLowerCase() ||
    normalized === '-₹0'.toLowerCase()
  ) {
    return 'Watchlist Alert';
  }
  return estimatedPnl;
}

function isTrackedInPortfolio(estimatedPnl?: string) {
  if (!estimatedPnl) return false;
  const normalized = estimatedPnl.replace(/\s/g, '').toLowerCase();
  return normalized !== 'notinportfolio' && normalized !== 'watchlistalert';
}

const Dashboard: React.FC = () => {
  const [signals, setSignals] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchInput, setSearchInput] = useState('');
  const [isScanning, setIsScanning] = useState(false);
  const [scanResult, setScanResult] = useState<AnalysisResult | null>(null);
  const [suggestions, setSuggestions] = useState<any[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [selectedInstrument, setSelectedInstrument] = useState<{ symbol: string; name: string } | null>(null);
  const [tradeQuantity, setTradeQuantity] = useState(1);
  const [tradeFeedback, setTradeFeedback] = useState('');
  const [lastSignalsRefreshAt, setLastSignalsRefreshAt] = useState<string | null>(null);
  const [portfolioMembershipOverride, setPortfolioMembershipOverride] = useState<boolean | null>(null);
  const scanAbortRef = useRef<AbortController | null>(null);
  const isScanningRef = useRef(false);

  useEffect(() => {
    isScanningRef.current = isScanning;
  }, [isScanning]);

  useEffect(() => {
    if (selectedInstrument?.name && !isScanning) {
      setSearchInput(selectedInstrument.name);
    }
  }, [selectedInstrument, isScanning]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      if (selectedInstrument || searchInput.trim().length < 3) {
        if (!selectedInstrument) {
          setSuggestions([]);
          setShowSuggestions(false);
        }
        return;
      }

      fetchSuggestions(searchInput);
    }, 200);

    return () => window.clearTimeout(timer);
  }, [searchInput, selectedInstrument]);

  useEffect(() => {
    refreshDashboardData(false);

    const refreshInterval = window.setInterval(() => {
      if (!isScanningRef.current) {
        refreshDashboardData(false);
      }
    }, FIFTEEN_MINUTES);

    return () => {
      window.clearInterval(refreshInterval);
      scanAbortRef.current?.abort();
    };
  }, []);

  async function refreshDashboardData(fetchLive = false) {
    await loadDashboard();
    if (fetchLive) {
      try {
        const history = await refreshLiveSignals();
        setSignals(history);
        setLastSignalsRefreshAt(new Date().toISOString());
        return;
      } catch (error) {
        console.error('Live refresh failed:', error);
      }
    }
    await fetchHistory();
  }

  async function fetchSuggestions(query: string) {
    try {
      const data = await searchTickers(query);
      setSuggestions(data);
      setShowSuggestions(data.length > 0);
    } catch (error) {
      console.error('Suggestions error:', error);
    }
  }

  async function fetchHistory() {
    try {
      const history = await getSignals();
      setSignals(history);
      setLastSignalsRefreshAt(new Date().toISOString());
    } catch (error) {
      console.error('History fetch failed:', error);
    }
  }

  async function loadDashboard() {
    setLoading(true);
    try {
      await new Promise((resolve) => setTimeout(resolve, 300));
    } catch (error) {
      console.error('Dashboard load error:', error);
    } finally {
      setLoading(false);
    }
  }

  function selectSuggestion(ticker: any) {
    setSelectedInstrument({ symbol: ticker.symbol, name: ticker.name });
    setSearchInput(ticker.name);
    setSuggestions([]);
    setShowSuggestions(false);
    setTradeFeedback('');
    setPortfolioMembershipOverride(null);
  }

  function handleInputChange(value: string) {
    setSearchInput(value);
    setSelectedInstrument(null);
    setTradeFeedback('');
    setPortfolioMembershipOverride(null);
  }

  async function handleManualScan(explicitTicker?: string, explicitName?: string) {
    if (isScanning) {
      scanAbortRef.current?.abort();
      scanAbortRef.current = null;
      setIsScanning(false);
      setTradeFeedback('Analysis stopped');
      return;
    }

    const tickerToAnalyze = explicitTicker || selectedInstrument?.symbol || searchInput.trim();
    if (!tickerToAnalyze) return;

    const controller = new AbortController();
    scanAbortRef.current = controller;
    setIsScanning(true);
    setScanResult(null);
    setTradeFeedback('');
    setPortfolioMembershipOverride(null);

    try {
      const data = await analyzeLive(tickerToAnalyze, { signal: controller.signal });
      const resolvedName =
        data.company_name || data.alert?.company_name || explicitName || selectedInstrument?.name || tickerToAnalyze;

      setScanResult(data);
      setSelectedInstrument({ symbol: data.ticker, name: resolvedName });
      setSearchInput(resolvedName);
      setTradeQuantity(1);

      window.setTimeout(() => {
        document.getElementById('deep-dive-result')?.scrollIntoView({ behavior: 'smooth' });
      }, 100);
    } catch (error: any) {
      if (error?.name !== 'AbortError') {
        console.error('Manual scan failed:', error);
      }
    } finally {
      scanAbortRef.current = null;
      setIsScanning(false);
    }
  }

  async function handlePortfolioTrade(mode: 'buy' | 'sell') {
    if (!scanResult?.ticker || tradeQuantity < 1) return;

    try {
      if (mode === 'buy') {
        await addToPortfolio({
          ticker: scanResult.ticker,
          quantity: tradeQuantity,
        });
        setTradeFeedback(`${scanResult.ticker} added to demo portfolio`);
        setPortfolioMembershipOverride(true);
      } else {
        await removeFromPortfolio({
          ticker: scanResult.ticker,
          quantity: tradeQuantity,
        });
        setTradeFeedback(`${scanResult.ticker} updated in demo portfolio`);
        setPortfolioMembershipOverride(false);
      }

      window.dispatchEvent(new CustomEvent('portfolio:updated'));
    } catch (error) {
      console.error(`${mode} portfolio action failed:`, error);
      setTradeFeedback(`Unable to ${mode} this stock right now`);
    }
  }

  if (loading) {
    return (
      <div className="flex-center h-full">
        <div className="loader">
          <div className="loader-dot"></div>
          <div className="loader-dot"></div>
          <div className="loader-dot"></div>
          <span className="ml-2 font-mono tracking-widest text-muted uppercase">Terminal Booting...</span>
        </div>
      </div>
    );
  }

  const resultAction = (scanResult?.alert?.action || scanResult?.action || 'WATCH').toUpperCase();
  const hasExpandedAnalysis = Boolean(scanResult) || isScanning;
  const displayCompanyName =
    scanResult?.company_name || scanResult?.alert?.company_name || selectedInstrument?.name || '';
  const actionConfidence = Math.round((scanResult?.alert?.confidence || scanResult?.confidence || 0) * 100);
  const estimatedPnl = scanResult?.alert?.estimated_pnl || 'Not In Portfolio';
  const isInPortfolio = portfolioMembershipOverride ?? isTrackedInPortfolio(estimatedPnl);
  const canAddToPortfolio = !isInPortfolio;
  const canReducePortfolio = isInPortfolio;
  const portfolioRelevanceLabel =
    portfolioMembershipOverride === true
      ? 'Tracking Position'
      : portfolioMembershipOverride === false
        ? 'Watchlist Alert'
        : estimatedPnl;

  return (
    <div className="dashboard-container fade-in">
      <div className="page-header glass-card">
        <div className="header-info">
          <h2 className="title">Avalon Intelligence Dashboard</h2>
          <p className="subtitle text-muted flex items-center gap-1">
            <span className="pulse-dot"></span> Universal Market Monitoring Active
          </p>
        </div>

        <div className="header-search">
          <div className="search-pill">
            <input
              type="text"
              placeholder="Search 500+ NSE Stocks..."
              value={searchInput}
              onChange={(event) => handleInputChange(event.target.value)}
              onKeyDown={(event) => event.key === 'Enter' && handleManualScan()}
              onBlur={() => window.setTimeout(() => setShowSuggestions(false), 200)}
            />
            <button
              className={`btn-search ${isScanning ? 'is-active' : ''}`}
              onClick={() => handleManualScan()}
              disabled={!isScanning && !selectedInstrument?.symbol && !searchInput.trim()}
            >
              {isScanning ? 'STOP' : 'ANALYZE'}
            </button>

            {showSuggestions && (
              <div className="suggestions-list">
                {suggestions.map((ticker) => (
                  <div
                    key={ticker.symbol}
                    className="suggestion-item"
                    onMouseDown={(event) => {
                      event.preventDefault();
                      selectSuggestion(ticker);
                    }}
                  >
                    <span className="sym">{ticker.symbol}</span>
                    <span className="name">{ticker.name}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
          {selectedInstrument && !isScanning && (
            <div className="selected-instrument-note">
              Ready to analyze: <strong>{selectedInstrument.name}</strong>
            </div>
          )}
        </div>

        <div className="header-actions">
          <div className="badge badge-outline">v3.0.0-PS6</div>
          <button className="btn btn-sm glass" onClick={() => refreshDashboardData(true)}>
            Refresh
          </button>
        </div>
      </div>

      <div className={`immersive-grid ${hasExpandedAnalysis ? 'analysis-active' : 'analysis-idle'}`}>
        <div className={`main-viewport ${hasExpandedAnalysis ? 'expanded' : 'compact'}`}>
          {scanResult && !isScanning ? (
            <div id="deep-dive-result" className="deep-dive-section fade-in">
              <div className="intelligence-grid mt-1">
                <div className="analysis-main-column">
                  <div className="verdict-row mb-2">
                    <div className={`glass-card verdict-card ${resultAction.toLowerCase()}`}>
                      <div className="badge badge-accent">Expert Verdict</div>
                      {displayCompanyName && <div className="result-company-name">{displayCompanyName}</div>}
                      <h1 className="ticker-display">{scanResult.ticker}</h1>
                      <div className="verdict-content">
                        <div className={`verdict-badge ${resultAction.toLowerCase()}`}>{resultAction}</div>
                        <div className="confidence-meter">
                          <div className="label">Confidence: {actionConfidence}%</div>
                          <div className="track">
                            <div className="fill" style={{ width: `${actionConfidence}%` }}></div>
                          </div>
                        </div>
                      </div>
                      {scanResult.alert?.created_at && (
                        <div className="sync-timestamp">
                          Intelligence Sync: {new Date(scanResult.alert.created_at).toLocaleTimeString()}
                        </div>
                      )}
                    </div>

                    <div className="glass-card pnl-impact-card">
                      <div className="label">Portfolio Relevance</div>
                      <div className={`pnl-value ${portfolioRelevanceLabel.includes('-') ? 'negative' : 'positive'}`}>
                        {portfolioRelevanceLabel}
                      </div>

                      <div className="portfolio-action-box">
                        <label htmlFor="trade-qty">Demo Quantity</label>
                        <div className="demo-buy-controls">
                          <input
                            id="trade-qty"
                            type="number"
                            min="1"
                            value={tradeQuantity}
                            onChange={(event) => setTradeQuantity(Math.max(1, Number(event.target.value) || 1))}
                          />
                          {canAddToPortfolio && (
                            <button type="button" className="btn btn-primary" onClick={() => handlePortfolioTrade('buy')}>
                              Add To Portfolio
                            </button>
                          )}
                          {canReducePortfolio && (
                            <button type="button" className="btn btn-secondary" onClick={() => handlePortfolioTrade('sell')}>
                              Remove From Portfolio
                            </button>
                          )}
                        </div>
                        {tradeFeedback && <div className="demo-buy-feedback">{tradeFeedback}</div>}
                      </div>
                    </div>
                  </div>

                  <div className="expert-chart-pane glass-card">
                    <h3 className="section-title mb-0-5">Market Intelligence Terminal</h3>
                    <StockChart ticker={scanResult.ticker} height={235} />
                  </div>
                </div>

                <div className="expert-reasoning-pane">
                  <div className="glass-card reasoning-card h-full">
                    <h3 className="section-title mb-1">Decision Synthesis</h3>
                    <div className="synthesis-text">
                      {scanResult.alert?.reasoning?.length
                        ? scanResult.alert.reasoning.map((line: string, index: number) => <p key={index}>{`\u2022 ${line}`}</p>)
                        : scanResult.final_response?.split('\n').map((line, index) => <p key={index}>{line}</p>)}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ) : isScanning ? (
            <div className="flex-center h-full glass-card analysis-loading-card">
              <div className="loader">
                <div className="loader-dot"></div>
                <span className="ml-2 font-mono tracking-widest text-accent uppercase">
                  Synthesizing Market Intelligence...
                </span>
              </div>
            </div>
          ) : (
            <div className="glass-card placeholder-hero compact-placeholder flex-center flex-row gap-2">
              <div className="hero-icon">M</div>
              <div className="text-left">
                <h2 className="mb-0">Universal Market Intelligence Ready</h2>
                <p className="subtitle text-muted opacity-70">Enter any NSE ticker or select a mover to engage the engine.</p>
              </div>
            </div>
          )}
        </div>

        <div className="autonomous-stream-pane signal-feed">
          <div className="signals-stream-header">
            <h3 className="section-title">Autonomous Signal Stream</h3>
            <div className="signal-refresh-meta">Last updated {formatSignalTime(lastSignalsRefreshAt)}</div>
          </div>

          <div className="signals-grid">
            {signals.length === 0 ? (
              <div className="glass-card placeholder-card">
                <div className="icon">S</div>
                <p>Monitoring market events...</p>
              </div>
            ) : (
              signals.map((signal: any, index) => {
                const impactLabel = formatSignalImpactLabel(signal.estimated_pnl);
                const companyLabel = signal.company_name && signal.company_name !== signal.ticker ? signal.company_name : '';

                return (
                  <div
                    key={`${signal.ticker}-${index}`}
                    className="glass-card signal-item animate-slide-in"
                    onClick={() => handleManualScan(signal.ticker, signal.company_name)}
                  >
                    <div className="item-header">
                      <div>
                        <span className="ticker">{signal.ticker}</span>
                        {companyLabel && <div className="signal-company">{companyLabel}</div>}
                      </div>
                      <div
                        className={`pnl-badge ${
                          impactLabel.includes('+') ? 'pos' : impactLabel === 'Watchlist Alert' ? 'neutral' : 'neg'
                        }`}
                      >
                        {impactLabel}
                      </div>
                    </div>
                    <p className="reasoning-summary">
                      <strong>{signal.action}:</strong> {signal.reasoning?.[0] || 'Synthesizing...'}
                    </p>
                    <div className="signal-timestamp">{formatSignalTime(signal.timestamp || signal.created_at)}</div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
