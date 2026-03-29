from typing import TypedDict, List, Optional, Dict, Any

class AgentState(TypedDict):
    # ── Input context ──────────────────────────────────────────
    ticker: str
    event_type: str            # BULK_DEAL | BREAKOUT | NEWS | FILING
    raw_event: dict            # raw payload from source
    user_portfolio: dict       # {ticker: {qty, avg_price, weight%}}
    user_risk_profile: str     # CONSERVATIVE | MODERATE | AGGRESSIVE

    # ── Signal layer ────────────────────────────────────────────
    signal: Optional[dict]             # Radar output
    chart_signals: Optional[List[dict]]# Chart Intel output

    # ── Enrichment layer ────────────────────────────────────────
    context: Optional[dict]            # fundamentals, mgmt tone, FII/DII
    filing_chunks: Optional[List[str]] # RAG-retrieved filing excerpts

    # ── Reasoning layer ─────────────────────────────────────────
    conflicts: Optional[List[dict]]    # list of conflicting signal pairs
    net_signal: Optional[str]          # BULLISH|BEARISH|MIXED|NEUTRAL
    confidence: Optional[float]        # 0.0 to 1.0

    # ── Portfolio layer ──────────────────────────────────────────
    portfolio_impact: Optional[dict]   # exposure, relevance score
    estimated_pnl: Optional[float]     # ₹ impact estimate

    # ── Output layer ────────────────────────────────────────────
    action: Optional[str]              # BUY|SELL|HOLD|REDUCE|WAIT
    action_reasoning: Optional[str]    # plain English explanation
    citations: Optional[List[str]]     # source URLs + filing refs
    alert: Optional[dict]              # final alert payload for UI
    final_response: Optional[str]      # formatted text for chat/ui

    # ── Metadata & Audit ──────────────────────────────────────────
    agent_trace: List[dict]            # every agent step logged here
    errors: List[str]                  # error accumulator — never crash
    total_latency_ms: Optional[int]
    total_llm_cost_usd: Optional[float]
