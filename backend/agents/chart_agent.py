"""
Chart Intelligence Agent
=========================
Technical pattern detection with conflicting signal analysis.
Handles Hackathon Scenario 2: Conflicting Technical Signals.

Responsibilities:
  - Multi-timeframe technical analysis
  - Breakout pattern detection (52-week high, support/resistance)
  - Conflicting signal identification and weighing
  - Historical pattern success rate computation
  - LLM-powered plain-English explanations
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.llm_provider import call_llm
from tools.signal_engine import compute_signals, get_live_signals, compute_pattern_success_rate
from tools.market_data import get_historical_data


CHART_SYSTEM_PROMPT = """You are an expert technical analyst specializing in Indian equities (NSE/BSE).
You explain chart patterns in plain English for retail investors.
Always:
- Be specific with price levels (Rs. X)
- Mention timeframes (next 5 days, 30 days)
- Identify conflicting signals honestly
- Give balanced recommendations, never binary buy/sell
- Include a conviction level: LOW / MEDIUM / HIGH
Include risk disclaimers."""


CHART_PROMPT = """Stock: {ticker} | Price: Rs.{price} | Daily Change: {daily_change_pct}%

TECHNICAL INDICATORS:
- RSI(14): {rsi} ({rsi_signal})
- MA Trend: {ma_trend} | MA20: {ma20} | MA50: {ma50} | MA200: {ma200}
- Golden Cross: {golden_cross} | Death Cross: {death_cross}
- MACD: {macd} vs Signal: {macd_signal_line} | Histogram: {macd_histogram} | MACD Bullish: {macd_bullish}
- Bollinger Bands: Upper={bb_upper}, Mid={bb_mid}, Lower={bb_lower}
- Volume: {vol_signal} (z-score={volume_z})
- 52W High: {high_52w} | 52W Low: {low_52w} | Near 52W High: {near_52w_high}
- Support: {support} | Resistance: {resistance}

{extra_context}

Write exactly 4 analysis points for this retail investor:
1. What the chart shows right now (be specific with price levels)
2. Key conflicting signals, if any
3. Risk to watch in the next 5 trading sessions
4. Specific price level to monitor for entry or exit

End with: Conviction: LOW / MEDIUM / HIGH"""


def run_chart_analysis(tickers: list, cache: dict = None) -> list[dict]:
    """Analyze a list of tickers with full technical analysis + LLM explanation."""
    results = []

    for ticker in tickers:
        # Compute signals
        if cache and ticker in cache:
            sig = compute_signals(ticker, cache[ticker])
        else:
            sig = get_live_signals(ticker)

        if not sig:
            continue

        # Generate LLM explanation
        try:
            explanation = call_llm(
                prompt=CHART_PROMPT.format(**sig, extra_context=""),
                system_prompt=CHART_SYSTEM_PROMPT,
                task="primary",
                max_tokens=400,
                temperature=0.2,
            )
            sig["explanation"] = explanation
        except Exception as e:
            sig["explanation"] = f"Analysis unavailable: {e}"

        results.append(sig)

    return results


def analyze_conflicting_signals(ticker: str, rsi_override: float = None,
                                 fii_selling: bool = False, fii_amount: str = "") -> dict:
    """
    Deep analysis of a stock with conflicting technical signals.
    Used for Hackathon Scenario 2.
    """
    audit_trail = []

    # Step 1: Fetch historical data
    audit_trail.append({"step": 1, "action": f"Fetching historical data for {ticker}"})
    df = get_historical_data(ticker, period="2y")
    if df is None or df.empty:
        return {"error": f"No data available for {ticker}"}

    # Step 2: Compute full signals
    audit_trail.append({"step": 2, "action": "Computing technical signals"})
    sig = compute_signals(ticker, df)
    if not sig:
        return {"error": f"Insufficient data for {ticker}"}

    # Apply overrides for scenario demonstration
    if rsi_override:
        sig["rsi"] = rsi_override
        sig["rsi_signal"] = "OVERBOUGHT" if rsi_override > 70 else "OVERSOLD" if rsi_override < 30 else "NEUTRAL"

    # Step 3: Compute pattern success rate
    audit_trail.append({"step": 3, "action": "Computing historical pattern success rate"})
    pattern_type = "52w_breakout" if sig.get("near_52w_high") or sig.get("at_52w_high") else "ma_breakout"
    success_data = compute_pattern_success_rate(ticker, pattern_type, df)

    # Step 4: Identify conflicting signals
    audit_trail.append({"step": 4, "action": "Identifying conflicting signals"})
    conflicts = []
    if sig["rsi"] > 70:
        conflicts.append({"type": "rsi_overbought", "value": sig["rsi"], "severity": "high"})
    if sig["rsi"] < 30:
        conflicts.append({"type": "rsi_oversold", "value": sig["rsi"], "severity": "high"})
    if fii_selling:
        conflicts.append({"type": "fii_selling", "amount": fii_amount, "severity": "medium"})
    if sig.get("death_cross"):
        conflicts.append({"type": "death_cross", "severity": "high"})
    if sig["volume_z"] < 0:
        conflicts.append({"type": "low_volume", "value": sig["volume_z"], "severity": "low"})

    # Step 5: LLM deep analysis
    audit_trail.append({"step": 5, "action": "Running LLM deep analysis"})
    conflict_text = ""
    if conflicts:
        conflict_text = "\nCONFLICTING SIGNALS DETECTED:\n"
        for c in conflicts:
            conflict_text += f"- {c['type'].upper()}: {c.get('value', c.get('amount', ''))} (Severity: {c['severity']})\n"
    if fii_selling:
        conflict_text += f"\nFII Activity: Key FII has REDUCED exposure — sold Rs.{fii_amount} worth in last 2 weeks\n"

    conflict_text += f"\nHISTORICAL PATTERN DATA:\n"
    conflict_text += f"- Pattern: {pattern_type}\n"
    conflict_text += f"- Success Rate: {success_data['success_rate']*100:.0f}% ({success_data['sample_size']} occurrences)\n"
    conflict_text += f"- Avg 30-day Return: {success_data.get('avg_return_30d', 'N/A')}%\n"

    explanation = call_llm(
        prompt=CHART_PROMPT.format(**sig, extra_context=conflict_text),
        system_prompt=CHART_SYSTEM_PROMPT,
        task="primary",
        max_tokens=600,
        temperature=0.2,
    )

    audit_trail.append({"step": 6, "action": "Generating balanced recommendation"})

    # Determine recommendation based on signal balance
    bullish_count = sum([
        sig.get("macd_bullish", False),
        sig.get("near_52w_high", False),
        sig["ma_trend"] == "BULLISH",
        sig["volume_z"] > 1,
    ])
    bearish_count = len(conflicts)

    if bullish_count > bearish_count + 1:
        recommendation = "CAUTIOUS_BUY"
    elif bearish_count > bullish_count + 1:
        recommendation = "CAUTIOUS_SELL"
    else:
        recommendation = "HOLD_AND_WATCH"

    # Calculate key levels
    stop_loss = round(sig["price"] * 0.95, 2)
    target_1 = round(sig["price"] * 1.05, 2)
    target_2 = round(sig["price"] * 1.10, 2)

    return {
        "alert_type": "CONFLICTING_SIGNALS",
        "ticker": ticker,
        "price": sig["price"],
        "primary_signal": {
            "type": pattern_type,
            "strength": "strong" if sig.get("at_52w_high") else "moderate",
            "volume_confirmation": sig["volume_z"] > 1,
        },
        "conflicting_signals": conflicts,
        "historical_analysis": success_data,
        "technical_indicators": {
            "rsi": sig["rsi"],
            "rsi_signal": sig["rsi_signal"],
            "macd_bullish": sig["macd_bullish"],
            "ma_trend": sig["ma_trend"],
            "volume_z": sig["volume_z"],
        },
        "llm_analysis": explanation,
        "balanced_recommendation": recommendation,
        "position_size": "3-5% of portfolio" if recommendation == "CAUTIOUS_BUY" else "Reduce to 2-3%",
        "key_levels": {
            "stop_loss": f"Rs.{stop_loss}",
            "target_1": f"Rs.{target_1}",
            "target_2": f"Rs.{target_2}",
        },
        "audit_trail": audit_trail,
    }
