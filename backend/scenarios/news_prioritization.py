"""
Scenario 3: Portfolio-Aware News Prioritization
==================================================
A user holds 8 stocks. Two major news events break simultaneously:
  1. RBI repo rate cut (-25bps)
  2. Pharma sector price control extension

The agent must:
  - Identify which event is more financially material to THIS portfolio
  - Quantify estimated P&L impact on relevant holdings
  - Generate a prioritized alert with context
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.news_agent import prioritize_news_events
from agents.portfolio_agent import load_portfolio


def run_scenario_3() -> dict:
    """
    Run the portfolio-aware news prioritization scenario.
    
    Events:
      1. RBI Repo Rate Cut (-25bps)
      2. Pharma Price Control Extension
    """
    portfolio = load_portfolio()

    events = [
        {
            "title": "RBI Repo Rate Cut (-25bps)",
            "type": "rbi_rate_cut",
            "magnitude": 1.5,  # Amplifier for 25bps cut on banking
        },
        {
            "title": "Pharma Price Control Extension — DPCO List Expanded",
            "type": "sector_regulation",
            "magnitude": -1.2,  # Negative impact on pharma
        },
    ]

    return prioritize_news_events(portfolio, events)


if __name__ == "__main__":
    import json
    result = run_scenario_3()
    print(json.dumps(result, indent=2, default=str))
