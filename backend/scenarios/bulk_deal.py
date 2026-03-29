"""
Scenario 1: Bulk Deal Filing Analysis
=======================================
A promoter of a mid-cap FMCG company has just sold 4.2% of their stake
via a bulk deal at a 6% discount to market price.

The agent must:
  - Retrieve the filing
  - Assess distress vs routine
  - Cross-reference management commentary and earnings
  - Generate a risk-adjusted alert citing the filing
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.filing_agent import analyze_bulk_deal


def run_scenario_1(ticker: str = "BRITANNIA") -> dict:
    """
    Run the full 8-step bulk deal analysis scenario.
    
    Default: Britannia (mid-cap FMCG) — promoter sells 4.2% at 6% discount.
    """
    return analyze_bulk_deal(
        ticker=ticker,
        seller_type="promoter",
        volume_pct=4.2,
        discount_pct=6.0,
    )


if __name__ == "__main__":
    import json
    result = run_scenario_1()
    print(json.dumps(result, indent=2, default=str))
