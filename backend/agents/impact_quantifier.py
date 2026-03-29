import logging
import time
from typing import Dict, Any, List
from graph.state import AgentState

logger = logging.getLogger("copilot.impact_quantifier")

MOVE_ESTIMATES = {
    "BULK_DEAL": -0.07,         # 7% downside for distress sell
    "BREAKOUT": 0.05,          # 5% upside for breakout
    "NEWS_POSITIVE": 0.03,      # 3% for general news
    "NEWS_NEGATIVE": -0.04,     # 4% for regulation/repo
    "EARNINGS_UP": 0.06,
    "EARNINGS_DOWN": -0.08
}

async def impact_quantifier_agent(state: AgentState) -> Dict[str, Any]:
    """Agent 6: Mathematically quantifies the rupee (₹) impact on the user's portfolio."""
    ticker = state["ticker"]
    impact = state.get("portfolio_impact", {})
    confidence = state.get("confidence", 0.75)
    event_type = state.get("event_type", "GENERAL_UPDATE")
    
    print(f"\n[📐 IMPACT QUANTIFIER] Estimating P&L impact for {ticker}...")
    time.sleep(0.5) # Simulate calculation
    
    if not impact.get("exposure"):
        print(f"  └─ ⚠️ Zero exposure found. Signal only.")
        return {"estimated_pnl": 0.0}
        
    exposure = impact.get("exposure", 0)
    expected_move = MOVE_ESTIMATES.get(event_type, 0.02 if state.get("net_signal") == "BULLISH" else -0.02)
    
    # Formula: Exposure * Expected Move * Confidence
    pnl_impact = exposure * expected_move * confidence
    
    # CLI Logging
    print(f"  ├─ Move Estimate: {round(expected_move*100, 1)}% ({event_type})")
    print(f"  ├─ Confidence Factor: {round(confidence, 2)}")
    print(f"  └─ Estimated P&L Impact: ₹{round(pnl_impact, 2):,}")
    
    trace = state.get("agent_trace", [])
    trace.append({
        "agent": "impact_quantifier",
        "timestamp": time.strftime("%H:%M:%SZ"),
        "output": f"P&L Impact: ₹{round(pnl_impact, 2):,}",
        "confidence": 1.0
    })
    
    return {
        "estimated_pnl": float(pnl_impact),
        "agent_trace": trace
    }
