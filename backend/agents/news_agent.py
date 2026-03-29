"""
News Intelligence Agent
========================
Multi-source news analysis with portfolio impact quantification.
Handles Hackathon Scenario 3: Portfolio-Aware News Prioritization.

Responsibilities:
  - Ingest real-time news from multiple sources
  - Classify news type (monetary policy, sector regulation, company-specific)
  - Calculate portfolio exposure to each news category
  - Estimate P&L impact per holding using sector multipliers
  - Rank events by portfolio materiality
  - Generate prioritized alert with quantified impact
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.llm_provider import call_llm
from tools.news_fetcher import fetch_news_headlines, classify_news_type, score_headline_sentiment
from config import IMPACT_MULTIPLIERS, SECTOR_MAP


NEWS_SYSTEM_PROMPT = """You are a financial news analyst for Indian markets. 
You quantify the impact of news events on specific stock portfolios.
Always:
- Estimate P&L impact in INR for each affected holding
- Prioritize by portfolio materiality, not headline size
- Distinguish between short-term volatility and structural impact
- Cite specific data points and percentages
- Include confidence levels for your estimates"""


def calculate_pnl_impact(event_type: str, portfolio: dict, magnitude: float = 1.0) -> list[dict]:
    """
    Calculate estimated P&L impact of a news event on portfolio holdings.
    Uses historical sector response multipliers.
    """
    impacts = []
    multipliers = IMPACT_MULTIPLIERS.get(event_type, {})
    holdings = portfolio.get("holdings", {})
    total_value = portfolio.get("total_value_inr", 500000)

    for ticker, holding in holdings.items():
        sector = SECTOR_MAP.get(ticker, "Other")
        multiplier = multipliers.get(sector, 0.5)
        
        holding_value = total_value * holding.get("value_pct", 0)
        estimated_impact_pct = multiplier * magnitude
        estimated_impact_inr = round(holding_value * estimated_impact_pct / 100, 0)

        impacts.append({
            "ticker": ticker,
            "sector": sector,
            "holding_value": round(holding_value, 0),
            "multiplier": multiplier,
            "impact_pct": round(estimated_impact_pct, 2),
            "impact_inr": estimated_impact_inr,
        })

    # Sort by absolute impact
    impacts.sort(key=lambda x: abs(x["impact_inr"]), reverse=True)
    return impacts


def prioritize_news_events(portfolio: dict, events: list[dict]) -> dict:
    """
    Analyze multiple simultaneous news events and prioritize by portfolio impact.
    Used for Hackathon Scenario 3.
    """
    audit_trail = []
    audit_trail.append({"step": 1, "action": "Ingesting news events"})

    ranked_events = []
    for event in events:
        event_type = event.get("type", "general")
        title = event.get("title", "")
        magnitude = event.get("magnitude", 1.0)  # e.g., 0.25 for 25bps rate cut

        audit_trail.append({"step": len(audit_trail) + 1, "action": f"Calculating impact for: {title}"})

        # Calculate P&L impact
        impacts = calculate_pnl_impact(event_type, portfolio, magnitude)
        total_impact = sum(i["impact_inr"] for i in impacts)
        total_impact_pct = round(total_impact / portfolio.get("total_value_inr", 500000) * 100, 2)

        # Affected holdings
        affected = [i for i in impacts if abs(i["impact_inr"]) > 500]

        ranked_events.append({
            "event": title,
            "event_type": event_type,
            "magnitude": magnitude,
            "portfolio_impact": {
                "estimated_total_inr": round(total_impact, 0),
                "percentage_impact": f"{'+' if total_impact > 0 else ''}{total_impact_pct}%",
                "confidence": 0.82 if event_type in IMPACT_MULTIPLIERS else 0.65,
            },
            "affected_holdings": [
                {"ticker": i["ticker"], "impact": f"{'+'if i['impact_inr']>0 else ''}Rs.{int(i['impact_inr'])}"}
                for i in affected
            ],
            "rationale": "",
        })

    # Sort by absolute portfolio impact
    ranked_events.sort(key=lambda x: abs(x["portfolio_impact"]["estimated_total_inr"]), reverse=True)

    # Add rank
    for i, event in enumerate(ranked_events):
        event["rank"] = i + 1

    # LLM reasoning for top events
    audit_trail.append({"step": len(audit_trail) + 1, "action": "Running LLM analysis for rationale"})

    events_text = ""
    for ev in ranked_events:
        events_text += f"\n{ev['rank']}. {ev['event']}"
        events_text += f"\n   Impact: {ev['portfolio_impact']['percentage_impact']} (Rs.{ev['portfolio_impact']['estimated_total_inr']})"
        events_text += f"\n   Affected: {', '.join(h['ticker'] + ': ' + h['impact'] for h in ev['affected_holdings'][:3])}\n"

    portfolio_desc = f"Portfolio: {', '.join(portfolio.get('holdings', {}).keys())} (Total: Rs.{portfolio.get('total_value_inr', 500000):,})"

    rationale = call_llm(
        prompt=f"""{portfolio_desc}

Two major news events broke simultaneously:
{events_text}

For each event:
1. Explain WHY it impacts this specific portfolio (which sectors, what percentage exposure)
2. Which event should the investor focus on FIRST and why?
3. What specific action should they take for each event?

Be specific with amounts and percentages.""",
        system_prompt=NEWS_SYSTEM_PROMPT,
        task="primary",
        max_tokens=600,
        temperature=0.2,
    )

    audit_trail.append({"step": len(audit_trail) + 1, "action": "Generating prioritized alert"})

    return {
        "alert_type": "NEWS_PRIORITIZATION",
        "priority_ranking": ranked_events,
        "llm_rationale": rationale,
        "recommended_action": f"Focus on Event #{ranked_events[0]['rank']} — highest portfolio impact",
        "audit_trail": audit_trail,
    }


def get_stock_news_summary(ticker: str) -> dict:
    """Get news summary for a single stock with sentiment analysis."""
    news = fetch_news_headlines(ticker)
    if not news:
        return {"ticker": ticker, "news": [], "sentiment": 0, "summary": "No recent news"}

    sentiments = [score_headline_sentiment(n["title"]) for n in news]
    avg_sentiment = round(sum(sentiments) / len(sentiments), 2) if sentiments else 0
    categories = [classify_news_type(n["title"]) for n in news]

    for n, s, c in zip(news, sentiments, categories):
        n["sentiment"] = s
        n["category"] = c

    return {
        "ticker": ticker,
        "news": news,
        "avg_sentiment": avg_sentiment,
        "sentiment_label": "POSITIVE" if avg_sentiment > 0.2 else "NEGATIVE" if avg_sentiment < -0.2 else "NEUTRAL",
        "news_count": len(news),
    }
