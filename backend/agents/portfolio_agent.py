import logging
import time
from typing import Dict, Any, List
from graph.state import AgentState

logger = logging.getLogger("copilot.portfolio_agent")

async def portfolio_agent(state: AgentState) -> Dict[str, Any]:
    """Agent 5: Calculates relevance based on actual user holdings."""
    ticker = state["ticker"]
    portfolio = state.get("user_portfolio", {})
    
    print(f"\n[💼 PORTFOLIO AGENT] Calculating exposure for {ticker}...")
    time.sleep(0.4) # Simulate calculation
    
    holding = portfolio.get(ticker) or portfolio.get(f"{ticker}.NS")
    
    if not holding:
        print(f"  └─ ⚠️ No holding found. Relevance = 0.2 (Watchlist alert only).")
        relevance = 0.2
        impact = {"exposure": 0, "qty": 0, "relevance": relevance}
    else:
        qty = holding.get("qty", 0)
        avg_price = holding.get("avg_price", 0)
        exposure = qty * avg_price
        
        # Calculate weight if total value known
        total_value = sum(h.get('qty', 0) * h.get('avg_price', 0) for h in portfolio.values())
        weight = (exposure / total_value * 100) if total_value > 0 else 0
        
        relevance = 1.0 if weight > 10 else 0.8
        
        impact = {
            "exposure": exposure,
            "qty": qty,
            "weight": round(weight, 2),
            "relevance": relevance,
            "avg_price": avg_price
        }
        
        # CLI Logging
        print(f"  ├─ Position: {qty} units @ ₹{avg_price}")
        print(f"  ├─ Weight: {round(weight, 2)}% of total portfolio")
        print(f"  └─ Relevance: {relevance} (HIGH PRIORITY)")
        
    trace = state.get("agent_trace", [])
    trace.append({
        "agent": "portfolio_agent",
        "timestamp": time.strftime("%H:%M:%SZ"),
        "output": f"Impact Assessment: {relevance} (Exposure: ₹{impact.get('exposure', 0)})",
        "confidence": 1.0
    })
    
    return {
        "portfolio_impact": impact,
        "agent_trace": trace
    }
