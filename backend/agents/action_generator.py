import json
import logging
import re
import time
from typing import Any, Dict

from graph.state import AgentState
from tools.llm_provider import call_llm

logger = logging.getLogger("copilot.action_generator")

ACTION_GENERATOR_PROMPT = """You are a senior investment strategist at an Indian family office.
Synthesize the following 7-agent pipeline findings for the investor:
- Ticker: {ticker}
- Event Type: {event_type}
- Conflict Resolution: {resolution}
- P&L Impact: INR {pnl}
- Confidence: {confidence}

1. Provide an AI VERDICT (BULLISH/BEARISH/MIXED/CAUTION).
2. Recommend exactly ONE ACTION (BUY, SELL, HOLD, REDUCE, WAIT).
3. Provide "REASONING" (max 3 bullets) in Plain English.
4. CITE the exact source from context.
5. Ensure a SEBI-compliant disclaimer is included.

Respond in EXACTLY this JSON format:
{{
  "verdict": "VERDICT",
  "action": "ACTION",
  "reasoning": ["Bullet 1", "Bullet 2"],
  "sources": ["NSE Filing XYZ"],
  "disclaimer": "AI-generated portfolio analysis. Not licensed financial advice."
}}"""


def format_estimated_pnl_label(pnl: float, exposure: float) -> str:
    if not exposure or abs(float(pnl or 0.0)) < 0.005:
        return "Watchlist Alert"
    prefix = "₹" if pnl >= 0 else "-₹"
    return f"{prefix}{abs(round(pnl, 2)):,}"


async def action_generator_agent(state: AgentState) -> Dict[str, Any]:
    """Agent 7: Generate the final synthesized action and response."""
    ticker = state["ticker"]
    event = state.get("event_type", "GENERAL_UPDATE")
    pnl = state.get("estimated_pnl", 0.0)
    resolution = state.get("net_signal", "NEUTRAL")
    confidence = state.get("confidence", 0.75)
    exposure = state.get("portfolio_impact", {}).get("exposure", 0)

    print(f"\n[ACTION GENERATOR] Synthesizing final recommendation for {ticker}...")
    time.sleep(1.0)

    try:
        response = call_llm(
            prompt=ACTION_GENERATOR_PROMPT.format(
                ticker=ticker,
                event_type=event,
                resolution=resolution,
                pnl=f"{round(pnl, 2):,}",
                confidence=confidence,
            ),
            task="primary",
            max_tokens=600,
            temperature=0.3,
        )

        match = re.search(r"\{.*\}", response, re.DOTALL)
        if match:
            final = json.loads(match.group())
        else:
            final = {
                "verdict": "NEUTRAL",
                "action": "WAIT",
                "reasoning": ["Summary failed."],
                "sources": [],
                "disclaimer": "",
            }

        print(f"  - Final Verdict: {final.get('verdict')}")
        print(f"  - Action: {final.get('action')}")
        print(f"  - Confidence: {int(confidence * 100)}%")
        print(f"\n[PIPELINE COMPLETE] Decision reached for {ticker}.\n")

        trace = state.get("agent_trace", [])
        trace.append(
            {
                "agent": "action_generator",
                "timestamp": time.strftime("%H:%M:%SZ"),
                "output": f"Final synthesized {final.get('action')} recommendation.",
                "confidence": 1.0,
            }
        )

        alert = {
            "ticker": ticker,
            "action": final.get("action"),
            "verdict": final.get("verdict"),
            "reasoning": final.get("reasoning"),
            "estimated_pnl": format_estimated_pnl_label(pnl, exposure),
            "sources": final.get("sources"),
            "disclaimer": final.get("disclaimer"),
            "confidence": confidence,
        }

        reasoning = final.get("reasoning", ["No summary available."])

        return {
            "action": final.get("action"),
            "action_reasoning": "\n".join(reasoning),
            "citations": final.get("sources", []),
            "alert": alert,
            "final_response": f"{ticker}: {final.get('action')} recommended. Reason: {reasoning[0]}",
            "agent_trace": trace,
        }
    except Exception as exc:
        logger.error(f"Action Generator error for {ticker}: {exc}")
        print(f"  - Intelligence synthesis failure: {exc}")
        return {"errors": [f"Action Generator Failure: {str(exc)}"]}
