import logging
import time
from typing import Any, Dict

import yfinance as yf

from graph.state import AgentState

logger = logging.getLogger("copilot.signal_radar")


async def signal_radar_agent(state: AgentState) -> Dict[str, Any]:
    """Agent 1: Detect and classify market signals from raw events or live news."""
    ticker = state["ticker"]
    raw = state.get("raw_event", {}) or {}
    event_type = state.get("event_type", "GENERAL_UPDATE")

    print(f"\n[SIGNAL RADAR] Initializing analysis for {ticker}...")

    if event_type == "MANUAL_SCAN" and not raw:
        print(f"  - Querying live internet news for {ticker}...")
        try:
            stock = yf.Ticker(f"{ticker}.NS")
            news = stock.news or []
            if news:
                latest = news[0]
                title = latest.get("title")
                publisher = latest.get("publisher")
                link = latest.get("link")

                if title and publisher and link:
                    title_lower = title.lower()
                    if any(token in title_lower for token in ["rise", "growth", "profit", "win", "surge"]):
                        event_type = "NEWS_POSITIVE"
                    elif any(token in title_lower for token in ["fall", "loss", "crash", "drop", "hit"]):
                        event_type = "NEWS_NEGATIVE"
                    else:
                        event_type = "NEWS_GENERAL"

                    raw = {
                        "source": publisher,
                        "title": title,
                        "url": link,
                        "event_type": event_type,
                    }
                    print(f"  - Live signal captured: {title}")
                else:
                    print(f"  - Incomplete news payload for {ticker}. Analyzing chart/context only.")
            else:
                print(f"  - No recent news found for {ticker}. Analyzing technicals only.")
        except Exception as exc:
            print(f"  - Internet fetch failed: {exc}")

    time.sleep(0.5)

    signal = {
        "ticker": ticker,
        "event": event_type,
        "magnitude_pct": raw.get("quantity_pct", 0),
        "discount_pct": raw.get("price_discount", 0),
        "seller_type": raw.get("client_type", "UNKNOWN"),
        "filing_url": raw.get("attachment_url") or raw.get("url") or "https://www.nseindia.com/notices",
        "confidence": "HIGH",
    }

    print(f"  - Detected Event: {event_type}")
    if signal["magnitude_pct"]:
        print(f"  - Magnitude: {signal['magnitude_pct']}% of outstanding equity")
    print(f"  - Source: {signal['filing_url']}")

    trace = state.get("agent_trace", [])
    trace.append(
        {
            "agent": "signal_radar",
            "timestamp": time.strftime("%H:%M:%SZ"),
            "output": f"Signal captured: {event_type}",
            "confidence": 1.0,
        }
    )

    return {
        "signal": signal,
        "agent_trace": trace,
        "event_type": event_type,
    }
