import json
import uuid
from typing import Literal

from langgraph.graph import END, StateGraph

from agents.action_generator import action_generator_agent
from agents.chart_intel import chart_intel_agent
from agents.conflict_resolver import conflict_resolver_agent
from agents.context_enrich import context_enrich_agent
from agents.impact_quantifier import impact_quantifier_agent
from agents.portfolio_agent import portfolio_agent
from agents.signal_radar import signal_radar_agent
from db.session import db
from graph.state import AgentState


def relevance_router(state: AgentState) -> Literal["impact_quantifier", "action_generator"]:
    """Skip portfolio impact math if the stock is not meaningfully held."""
    impact = state.get("portfolio_impact", {})
    if impact.get("relevance", 0) >= 0.8:
        return "impact_quantifier"
    return "action_generator"


def build_intelligence_graph() -> StateGraph:
    workflow = StateGraph(AgentState)

    workflow.add_node("signal_radar", signal_radar_agent)
    workflow.add_node("chart_intel", chart_intel_agent)
    workflow.add_node("context_enrich", context_enrich_agent)
    workflow.add_node("conflict_resolver", conflict_resolver_agent)
    workflow.add_node("portfolio_agent", portfolio_agent)
    workflow.add_node("impact_quantifier", impact_quantifier_agent)
    workflow.add_node("action_generator", action_generator_agent)

    workflow.set_entry_point("signal_radar")
    workflow.add_edge("signal_radar", "chart_intel")
    workflow.add_edge("chart_intel", "context_enrich")
    workflow.add_edge("context_enrich", "conflict_resolver")
    workflow.add_edge("conflict_resolver", "portfolio_agent")
    workflow.add_conditional_edges(
        "portfolio_agent",
        relevance_router,
        {
            "impact_quantifier": "impact_quantifier",
            "action_generator": "action_generator",
        },
    )
    workflow.add_edge("impact_quantifier", "action_generator")
    workflow.add_edge("action_generator", END)

    return workflow.compile()


intelligence_graph = build_intelligence_graph()


async def run_analysis(
    ticker: str,
    event_type: str = "GENERAL_UPDATE",
    raw_event: dict = None,
    user_portfolio: dict = None,
) -> dict:
    """Run the full 7-agent pipeline for a ticker and persist the result."""
    raw_event = raw_event or {}

    if raw_event and (raw_event.get("title") or raw_event.get("url")):
        content_key = raw_event.get("title") or raw_event.get("url")
        existing = await db.fetch_one(
            """
            SELECT id
            FROM signals
            WHERE ticker = ?
              AND raw_event LIKE ?
              AND detected_at > datetime('now', '-1 day')
            LIMIT 1
            """,
            (ticker, f"%{content_key}%"),
        )
        if existing:
            print(f"  - Skipping duplicate signal for {ticker}: {content_key[:40]}...")
            return {"status": "skipped", "reason": "duplicate"}

    initial_state = {
        "ticker": ticker,
        "event_type": event_type,
        "raw_event": raw_event,
        "user_portfolio": user_portfolio or {},
        "user_risk_profile": "MODERATE",
        "agent_trace": [],
        "errors": [],
    }

    result = await intelligence_graph.ainvoke(initial_state)

    try:
        signal_id = str(uuid.uuid4())
        await db.execute(
            """
            INSERT INTO signals (id, ticker, event_type, net_signal, confidence, raw_event)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                signal_id,
                result["ticker"],
                result["event_type"],
                result.get("net_signal"),
                result.get("confidence"),
                json.dumps(result.get("raw_event", {})),
            ),
        )

        alert = result.get("alert", {})
        if alert:
            alert_id = str(uuid.uuid4())
            reasoning = alert.get("reasoning", [])
            reasoning_str = "\n".join(reasoning) if isinstance(reasoning, list) else str(reasoning)

            await db.execute(
                """
                INSERT INTO alerts (id, user_id, signal_id, action, reasoning, estimated_pnl, confidence, agent_trace, citations, disclaimer)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    alert_id,
                    "demo_user_123",
                    signal_id,
                    alert.get("action"),
                    reasoning_str,
                    float(result.get("estimated_pnl", 0.0) or 0.0),
                    float(result.get("confidence", 0.0) or 0.0),
                    json.dumps(result.get("agent_trace")),
                    json.dumps(alert.get("sources")),
                    alert.get("disclaimer"),
                ),
            )
    except Exception as exc:
        print(f"  - DB persistence failed: {exc}")

    return result
