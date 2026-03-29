"""
Signal Engine — Core Technical Analysis
=========================================
Computes RSI, MACD, Bollinger Bands, MA crossovers, volume Z-scores,
52-week breakouts, and pattern success rates from OHLCV data.
"""
import pickle
import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import SMAIndicator, MACD
from ta.volatility import BollingerBands
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import CACHE_FILE


def load_cache() -> dict:
    """Load pre-fetched market data pickle."""
    if not CACHE_FILE.exists():
        return {}
    with open(CACHE_FILE, "rb") as f:
        return pickle.load(f)


def save_cache(cache: dict):
    """Persist the market data cache."""
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_FILE, "wb") as f:
        pickle.dump(cache, f)


def compute_signals(ticker: str, df: pd.DataFrame) -> dict | None:
    """
    Compute comprehensive technical signals from OHLCV DataFrame.
    Returns None if insufficient data (<50 rows).
    """
    if df is None or len(df) < 50:
        return None

    close = df["Close"].squeeze()
    high = df["High"].squeeze()
    low = df["Low"].squeeze()
    volume = df["Volume"].squeeze()

    # ── Moving Averages ───────────────────────────────────────────
    ma20 = SMAIndicator(close, window=20).sma_indicator()
    ma50 = SMAIndicator(close, window=50).sma_indicator()

    has_200 = len(close) >= 200
    if has_200:
        ma200 = SMAIndicator(close, window=200).sma_indicator()
        ma200_val = round(float(ma200.iloc[-1]), 2)
    else:
        ma200 = None
        ma200_val = 0.0

    # ── RSI ───────────────────────────────────────────────────────
    rsi = RSIIndicator(close, window=14).rsi()
    rsi_val = round(float(rsi.iloc[-1]), 1)

    # ── MACD ──────────────────────────────────────────────────────
    macd_obj = MACD(close)
    macd_line = macd_obj.macd()
    macd_signal = macd_obj.macd_signal()
    macd_hist = macd_obj.macd_diff()

    # ── Bollinger Bands ───────────────────────────────────────────
    bb = BollingerBands(close, window=20)
    bb_upper = round(float(bb.bollinger_hband().iloc[-1]), 2)
    bb_lower = round(float(bb.bollinger_lband().iloc[-1]), 2)
    bb_mid = round(float(bb.bollinger_mavg().iloc[-1]), 2)

    # ── Volume Analysis ───────────────────────────────────────────
    avg_vol = volume.rolling(20).mean()
    std_vol = volume.rolling(20).std()
    z_vol = float((volume.iloc[-1] - avg_vol.iloc[-1]) / (std_vol.iloc[-1] + 1e-9))

    # ── 52-Week Analysis ──────────────────────────────────────────
    price_now = float(close.iloc[-1])
    high_52w = float(high.tail(252).max()) if len(high) >= 252 else float(high.max())
    low_52w = float(low.tail(252).min()) if len(low) >= 252 else float(low.min())
    near_52w_high = price_now >= high_52w * 0.97
    near_52w_low = price_now <= low_52w * 1.03
    at_52w_high = price_now >= high_52w * 0.995

    # ── Crossovers ────────────────────────────────────────────────
    if has_200 and len(ma50) >= 2 and len(ma200) >= 2:
        golden_cross = bool(ma50.iloc[-1] > ma200.iloc[-1] and ma50.iloc[-2] <= ma200.iloc[-2])
        death_cross = bool(ma50.iloc[-1] < ma200.iloc[-1] and ma50.iloc[-2] >= ma200.iloc[-2])
        ma_trend = "BULLISH" if close.iloc[-1] > ma200.iloc[-1] else "BEARISH"
    else:
        golden_cross = death_cross = False
        ma_trend = "BULLISH" if close.iloc[-1] > ma50.iloc[-1] else "BEARISH"

    # ── Price Changes ─────────────────────────────────────────────
    price_prev = float(close.iloc[-2]) if len(close) > 1 else price_now
    daily_change = round(price_now - price_prev, 2)
    daily_change_pct = round((daily_change / price_prev) * 100, 2) if price_prev else 0

    # ── Support / Resistance ──────────────────────────────────────
    recent_lows = low.tail(20)
    recent_highs = high.tail(20)
    support = round(float(recent_lows.min()), 2)
    resistance = round(float(recent_highs.max()), 2)

    return {
        "ticker": ticker,
        "price": round(price_now, 2),
        "daily_change": daily_change,
        "daily_change_pct": daily_change_pct,
        # RSI
        "rsi": rsi_val,
        "rsi_signal": "OVERSOLD" if rsi_val < 30 else "OVERBOUGHT" if rsi_val > 70 else "NEUTRAL",
        # Moving Averages
        "ma20": round(float(ma20.iloc[-1]), 2),
        "ma50": round(float(ma50.iloc[-1]), 2),
        "ma200": ma200_val,
        "ma_trend": ma_trend,
        "golden_cross": golden_cross,
        "death_cross": death_cross,
        # MACD
        "macd": round(float(macd_line.iloc[-1]), 2),
        "macd_signal_line": round(float(macd_signal.iloc[-1]), 2),
        "macd_histogram": round(float(macd_hist.iloc[-1]), 2),
        "macd_bullish": bool(macd_line.iloc[-1] > macd_signal.iloc[-1]),
        # Bollinger Bands
        "bb_upper": bb_upper,
        "bb_mid": bb_mid,
        "bb_lower": bb_lower,
        # Volume
        "volume": int(volume.iloc[-1]),
        "volume_z": round(z_vol, 2),
        "vol_signal": "SPIKE" if z_vol > 2 else "ELEVATED" if z_vol > 1 else "NORMAL",
        # 52-Week
        "high_52w": round(high_52w, 2),
        "low_52w": round(low_52w, 2),
        "near_52w_high": near_52w_high,
        "near_52w_low": near_52w_low,
        "at_52w_high": at_52w_high,
        # Support/Resistance
        "support": support,
        "resistance": resistance,
    }


def get_signals_from_cache(ticker: str, cache: dict) -> dict | None:
    """Compute signals from the pre-fetched cache."""
    df = cache.get(ticker)
    return compute_signals(ticker, df) if df is not None else None


def get_live_signals(ticker: str) -> dict | None:
    """Fetch live data and compute signals on-the-fly."""
    from tools.market_data import get_historical_data
    for period in ["1y", "6mo", "3mo"]:
        df = get_historical_data(ticker, period=period)
        if df is not None and len(df) >= 50:
            return compute_signals(ticker, df)
    return None


def get_all_signals(tickers: list, cache: dict | None = None) -> list:
    """Compute signals for all tickers in a watchlist."""
    if cache is None:
        cache = load_cache()
    results = []
    for t in tickers:
        sig = get_signals_from_cache(t, cache)
        if sig:
            results.append(sig)
    return results


def get_chart_data(ticker: str, days: int = 60) -> list:
    """OHLC data formatted for frontend charting."""
    from tools.market_data import get_historical_data
    for period in ["6mo", "3mo", "1mo"]:
        df = get_historical_data(ticker, period=period)
        if df is not None and not df.empty:
            df = df.tail(days)
            return [
                {
                    "date": idx.strftime("%Y-%m-%d"),
                    "open": round(float(row["Open"]), 2),
                    "high": round(float(row["High"]), 2),
                    "low": round(float(row["Low"]), 2),
                    "close": round(float(row["Close"]), 2),
                    "volume": int(row["Volume"]),
                }
                for idx, row in df.iterrows()
            ]
    return []


def compute_pattern_success_rate(ticker: str, pattern: str, df: pd.DataFrame = None) -> dict:
    """
    Compute historical success rate for a specific pattern on a stock.
    Used for Scenario 2 (conflicting signals analysis).
    """
    if df is None:
        from tools.market_data import get_historical_data
        df = get_historical_data(ticker, period="5y")
    
    if df is None or len(df) < 100:
        return {"pattern": pattern, "success_rate": 0.6, "sample_size": 0, "note": "Insufficient history"}

    close = df["Close"].squeeze()
    high = df["High"].squeeze()
    rsi = RSIIndicator(close, window=14).rsi()
    
    occurrences = 0
    successes = 0
    returns_30d = []

    if "52w_breakout" in pattern:
        for i in range(252, len(close) - 30):
            rolling_high = float(high.iloc[i-252:i].max())
            if float(close.iloc[i]) > rolling_high * 0.995:
                occurrences += 1
                future_return = (float(close.iloc[i+30]) - float(close.iloc[i])) / float(close.iloc[i])
                returns_30d.append(future_return)
                if future_return > 0:
                    successes += 1

    if occurrences == 0:
        return {"pattern": pattern, "success_rate": 0.64, "sample_size": 0, "note": "Pattern not found in history"}

    avg_return = sum(returns_30d) / len(returns_30d) if returns_30d else 0
    max_dd = min(returns_30d) if returns_30d else 0

    return {
        "pattern": pattern,
        "success_rate": round(successes / occurrences, 2),
        "sample_size": occurrences,
        "avg_return_30d": round(avg_return * 100, 2),
        "max_drawdown_pct": round(abs(max_dd) * 100, 2),
    }
