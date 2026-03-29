import logging
import time
from typing import Any, Dict

import yfinance as yf

from graph.state import AgentState

logger = logging.getLogger("copilot.chart_intel")


def _extract_scalar(value: Any) -> float:
    """Handle yfinance values that can arrive as Series-like objects."""
    if hasattr(value, "iloc"):
        value = value.iloc[0]
    if hasattr(value, "item"):
        try:
            value = value.item()
        except Exception:
            pass
    return float(value)


async def chart_intel_agent(state: AgentState) -> Dict[str, Any]:
    """Agent 2: Conduct technical analysis and pattern detection."""
    ticker = state["ticker"]

    print(f"\n[CHART INTEL] Running TA scanners for {ticker}.NS...")

    try:
        df = yf.download(f"{ticker}.NS", period="6mo", interval="1d", progress=False, auto_adjust=False)

        if df is None or df.empty:
            print(f"  - Empty dataset for {ticker}. Check ticker format.")
            return {"chart_signals": [], "errors": ["No market data found"]}

        if hasattr(df.columns, "nlevels") and df.columns.nlevels > 1:
            df.columns = [col[0] for col in df.columns]

        required_columns = {"Close", "High", "Volume"}
        if not required_columns.issubset(set(df.columns)):
            print(f"  - Missing expected OHLCV columns for {ticker}.")
            return {"chart_signals": [], "errors": ["Incomplete market data found"]}

        delta = df["Close"].diff()
        gain = delta.where(delta > 0, 0).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df["rsi"] = 100 - (100 / (1 + rs))
        df["sma20"] = df["Close"].rolling(window=20).mean()
        df["sma50"] = df["Close"].rolling(window=50).mean()
        df["volume_avg_20"] = df["Volume"].rolling(window=20).mean()

        latest_rsi = round(_extract_scalar(df["rsi"].iloc[-1]), 2)
        latest_close = round(_extract_scalar(df["Close"].iloc[-1]), 2)
        latest_sma20 = _extract_scalar(df["sma20"].iloc[-1])
        latest_sma50 = _extract_scalar(df["sma50"].iloc[-1])
        max_high = _extract_scalar(df["High"].max())
        latest_volume = _extract_scalar(df["Volume"].iloc[-1])
        avg_volume = _extract_scalar(df["volume_avg_20"].iloc[-1]) if len(df.index) >= 20 else latest_volume

        is_uptrend = latest_sma20 > latest_sma50
        near_52w = latest_close >= (max_high * 0.98)
        volume_spike = latest_volume > (avg_volume * 1.5 if avg_volume else 0)

        chart_result = {
            "ticker": ticker,
            "rsi": latest_rsi,
            "trend": "UP" if is_uptrend else "DOWN",
            "near_52w_high": near_52w,
            "vol_spike": volume_spike,
        }

        print(f"  - RSI: {latest_rsi}")
        print(f"  - Trend: {chart_result['trend']}")
        print(f"  - 52W Proximity: {'NEAR HIGH' if near_52w else 'NORMAL'}")

        trace = state.get("agent_trace", [])
        trace.append(
            {
                "agent": "chart_intel",
                "timestamp": time.strftime("%H:%M:%SZ"),
                "output": f"TA Complete: RSI={latest_rsi}, Trend={chart_result['trend']}",
                "confidence": 0.95,
            }
        )

        return {
            "chart_signals": [chart_result],
            "agent_trace": trace,
        }

    except Exception as exc:
        logger.error(f"Chart Intel error for {ticker}: {exc}")
        print(f"  - Fatal TA Engine failure: {exc}")
        return {"errors": [f"Chart Intel Failure: {str(exc)}"]}
