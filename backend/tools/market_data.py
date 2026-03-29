"""
Market Data Utilities
======================
Wrappers around yfinance for live price fetching,
historical OHLCV data, and stock fundamentals.
Enhanced ticker resolution: company names → NSE symbols.
"""
import time
import yfinance as yf
import requests
from concurrent.futures import ThreadPoolExecutor
import logging

logger = logging.getLogger("copilot.market_data")

# ── In-Memory Cache ───────────────────────────────────────────────────
PRICE_CACHE = {}
CACHE_TTL = 60  # seconds

# ── Comprehensive Symbol Aliases (company name → NSE ticker) ─────────
SYMBOL_ALIASES = {
    # Full company names
    "INFOSYS": "INFY",
    "TATA ELXSI": "TATAELXSI",
    "TATAELXSI": "TATAELXSI",
    "TATA MOTORS": "TATAMOTORS",
    "TATA MOTOR": "TATAMOTORS",
    "RELIANCE INDUSTRIES": "RELIANCE",
    "HDFC BANK": "HDFCBANK",
    "ICICI BANK": "ICICIBANK",
    "STATE BANK": "SBIN",
    "BAJAJ FINANCE": "BAJFINANCE",
    "BAJAJFINANCE": "BAJFINANCE",
    "HINDUSTAN UNILEVER": "HINDUNILVR",
    "HUL": "HINDUNILVR",
    "ASIAN PAINTS": "ASIANPAINT",
    "LARSEN": "LT",
    "L&T": "LT",
    "BHARTI AIRTEL": "BHARTIARTL",
    "AIRTEL": "BHARTIARTL",
    "NESTLE": "NESTLEIND",
    "NESTLE INDIA": "NESTLEIND",
    "KOTAK": "KOTAKBANK",
    "KOTAK MAHINDRA": "KOTAKBANK",
    "ADANI": "ADANIENT",
    "ADANI ENTERPRISES": "ADANIENT",
    "POWER GRID": "POWERGRID",
    "SUN PHARMA": "SUNPHARMA",
    "SUN PHARMACEUTICAL": "SUNPHARMA",
    "TATAMOTOR": "TATAMOTORS",
    "AXIS": "AXISBANK",
    "AXIS BANK": "AXISBANK",
    "WIPRO": "WIPRO",
    "WIPRO TECHNOLOGIES": "WIPRO",
    "HCL": "HCLTECH",
    "RELIANCE": "RELIANCE",
    "MAHINDRA": "M&M",
    "TITAN": "TITAN",
    "TITAN COMPANY": "TITAN",
    "ULTRATECH": "ULTRACEMCO",
}

# ── Tickers that need special yfinance symbol mapping ─────────────────
# Some NSE symbols differ or have delisted siblings (e.g. TATAMOTORS DVR)
YFINANCE_OVERRIDES = {
    "TATAMOTORS": ["TATAMOTORS", "TATAMTRDG", "TATAMTRS", "TITAN", "TCS"],   # Try main, then DVR, then group fallbacks
}

NSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com",
}


def normalize_symbol(ticker: str) -> str:
    """Resolve company names and aliases to NSE ticker symbols."""
    ticker = ticker.upper().strip()
    return SYMBOL_ALIASES.get(ticker, ticker)


def search_tickers(query: str) -> list[dict]:
    """Search for tickers by symbol or company name alias."""
    query = query.upper().strip()
    if not query:
        return []
    
    results = []
    # Check SYMBOL_ALIASES (Company Names)
    for name, ticker in SYMBOL_ALIASES.items():
        if query in name or query in ticker:
            results.append({"ticker": ticker, "name": name})
    
    # Remove duplicates and limit
    seen = set()
    unique_results = []
    for r in results:
        if r["ticker"] not in seen:
            unique_results.append(r)
            seen.add(r["ticker"])
            
    return unique_results[:8]


def _yfinance_symbols(ticker: str) -> list[str]:
    """Get the yfinance-compatible symbols (main + fallbacks) for a ticker."""
    val = YFINANCE_OVERRIDES.get(ticker, [ticker])
    return val if isinstance(val, list) else [val]


def get_live_price(ticker: str) -> dict:
    """Fetch latest price with 60s cache and multi-source fallback."""
    ticker = normalize_symbol(ticker)
    now = time.time()

    if ticker in PRICE_CACHE:
        cached = PRICE_CACHE[ticker]
        if now - cached["ts"] < CACHE_TTL:
            return cached["data"]

    # Try yfinance with override mapping
    yf_symbols = _yfinance_symbols(ticker)
    
    for sym in yf_symbols:  # Try all symbols in order
        for suffix in [".NS", ".BO", ""]:
            full_sym = f"{sym}{suffix}"
            try:
                t = yf.Ticker(full_sym)
                df = t.history(period="5d", interval="1d")
                if df is not None and not df.empty:
                    cur = round(float(df["Close"].iloc[-1]), 2)
                    prev = float(df["Close"].iloc[-2]) if len(df) > 1 else cur
                    change_pct = round((cur - prev) / prev * 100, 2) if prev else 0
                    result = {
                        "ticker": ticker,
                        "price": cur,
                        "change": round(cur - prev, 2),
                        "change_pct": change_pct,
                        "source": f"yfinance ({full_sym})",
                    }
                    PRICE_CACHE[ticker] = {"ts": now, "data": result}
                    logger.info(f"✅ {ticker}: ₹{cur} ({change_pct:+.2f}%) [via {full_sym}]")
                    return result
            except Exception:
                continue

    logger.warning(f"❌ {ticker}: No price data available")
    return {"ticker": ticker, "error": "No price data available"}


def get_bulk_prices(tickers: list) -> list:
    """Fetch multiple prices in parallel."""
    with ThreadPoolExecutor(max_workers=10) as pool:
        return list(pool.map(get_live_price, [t.upper() for t in tickers]))


def get_historical_data(ticker: str, period: str = "1y") -> "pd.DataFrame | None":
    """Fetch OHLCV DataFrame for any NSE stock."""
    ticker = normalize_symbol(ticker)
    yf_symbols = _yfinance_symbols(ticker)
    
    for sym in yf_symbols:
        for suffix in [".NS", ".BO", ""]:
            full_sym = f"{sym}{suffix}"
            try:
                t = yf.Ticker(full_sym)
                df = t.history(period=period)
                if df is not None and not df.empty:
                    logger.info(f"📊 {ticker}: Fetched {len(df)} rows history via {full_sym}")
                    return df
            except Exception:
                continue
    logger.warning(f"❌ {ticker}: No historical data")
    return None


def get_stock_info(ticker: str) -> dict:
    """Fetch fundamental info (P/E, market cap, 52w high/low)."""
    ticker = normalize_symbol(ticker)
    yf_symbols = _yfinance_symbols(ticker)
    
    for sym in yf_symbols:
        for suffix in [".NS", ".BO"]:
            full_sym = f"{sym}{suffix}"
            try:
                info = yf.Ticker(full_sym).info
                if info and (info.get("regularMarketPrice") or info.get("currentPrice")):
                    return {
                        "ticker": ticker,
                        "company_name": info.get("longName", ticker),
                        "sector": info.get("sector", "Unknown"),
                        "industry": info.get("industry", "Unknown"),
                        "market_cap": info.get("marketCap", 0),
                        "pe_ratio": info.get("trailingPE"),
                        "pb_ratio": info.get("priceToBook"),
                        "dividend_yield": info.get("dividendYield"),
                        "52w_high": info.get("fiftyTwoWeekHigh"),
                        "52w_low": info.get("fiftyTwoWeekLow"),
                        "beta": info.get("beta"),
                    }
            except Exception:
                continue
    return {"ticker": ticker, "error": "No fundamental data available"}


def get_nifty_movers(watchlist: list) -> list:
    """Fetch and sort watchlist by absolute change to find biggest movers."""
    prices = get_bulk_prices(watchlist)
    movers = [p for p in prices if "error" not in p]
    movers.sort(key=lambda x: abs(x.get("change_pct", 0)), reverse=True)
    return movers[:10]
