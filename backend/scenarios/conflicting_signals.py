"""
Scenario 2: Conflicting Technical Signals
============================================
A large-cap IT stock has broken out above a 52-week high on
above-average volume. However, RSI is at 78 (overbought) and
a key FII has reduced exposure.

The agent must:
  - Detect the breakout pattern
  - Quantify historical success rate for this pattern on this stock
  - Surface conflicting signals
  - Present balanced, data-backed recommendation
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.chart_agent import analyze_conflicting_signals


def run_scenario_2(ticker: str = "TCS") -> dict:
    """
    Run the conflicting signals analysis.
    
    Default: TCS (large-cap IT) — 52w breakout + RSI 78 + FII selling.
    """
    return analyze_conflicting_signals(
        ticker=ticker,
        rsi_override=78.0,
        fii_selling=True,
        fii_amount="245 cr",
    )


if __name__ == "__main__":
    import json
    result = run_scenario_2()
    print(json.dumps(result, indent=2, default=str))
