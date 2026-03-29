-- Users & risk profiles
CREATE TABLE IF NOT EXISTS users (
    id           TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    name         TEXT NOT NULL,
    risk_profile TEXT CHECK(risk_profile IN ('CONSERVATIVE','MODERATE','AGGRESSIVE')),
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Portfolio holdings
CREATE TABLE IF NOT EXISTS portfolio_holdings (
    user_id    TEXT REFERENCES users(id) ON DELETE CASCADE,
    ticker     TEXT NOT NULL,
    qty        INTEGER NOT NULL,
    avg_price  REAL NOT NULL,
    sector     TEXT,
    added_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, ticker)
);

-- Signals detected (append-only)
CREATE TABLE IF NOT EXISTS signals (
    id           TEXT PRIMARY KEY,
    ticker       TEXT NOT NULL,
    event_type   TEXT NOT NULL,
    magnitude    REAL,
    net_signal   TEXT,
    confidence   REAL,
    filing_url   TEXT,
    raw_event    JSON,
    detected_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Alerts sent to users (full audit trail)
CREATE TABLE IF NOT EXISTS alerts (
    id            TEXT PRIMARY KEY,
    user_id       TEXT REFERENCES users(id),
    signal_id     TEXT REFERENCES signals(id),
    action        TEXT,
    reasoning     TEXT,
    estimated_pnl REAL,
    confidence    REAL,
    agent_trace   JSON,   -- full step-by-step audit
    citations     JSON,
    disclaimer    TEXT,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    acknowledged  BOOLEAN DEFAULT FALSE
);

-- Pattern backtest cache
CREATE TABLE IF NOT EXISTS pattern_backtest (
    ticker        TEXT,
    pattern       TEXT,
    success_rate  REAL,
    sample_size   INTEGER,
    updated_at    TIMESTAMP,
    PRIMARY KEY (ticker, pattern)
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_alerts_user ON alerts(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_signals_ticker ON signals(ticker, detected_at DESC);
