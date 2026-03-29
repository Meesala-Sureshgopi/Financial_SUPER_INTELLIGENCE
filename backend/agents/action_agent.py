"""
Action Agent
==============
Closes the insight-to-action gap. Manages price alerts,
watchlist additions, and generates concrete follow-up recommendations.

Responsibilities:
  - Set / check / clear price alerts
  - Generate 2-3 actionable follow-ups per signal
  - Maintain full audit trail
  - Push real-time notifications via WebSocket
"""
import json
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import ALERTS_FILE, DATA_DIR


def _load_alerts() -> list:
    if not ALERTS_FILE.exists():
        return []
    with open(ALERTS_FILE, "r") as f:
        return json.load(f)


def _save_alerts(alerts: list) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(ALERTS_FILE, "w") as f:
        json.dump(alerts, f, indent=2)


def set_alert(ticker: str, target_price: float, direction: str = "below") -> dict:
    """Create a new price alert."""
    alerts = _load_alerts()
    alert = {
        "id": f"alert_{len(alerts)+1}",
        "ticker": ticker.upper(),
        "target": target_price,
        "direction": direction,
        "created": datetime.now().isoformat(),
        "triggered": False,
    }
    alerts.append(alert)
    _save_alerts(alerts)
    return {"status": "alert_set", "alert": alert}


def check_alerts() -> list[dict]:
    """Check all active alerts against current prices."""
    from tools.market_data import get_live_price
    alerts = _load_alerts()
    triggered = []

    for alert in alerts:
        if alert.get("triggered"):
            continue
        try:
            price_data = get_live_price(alert["ticker"])
            if "error" in price_data:
                continue
            cur = price_data["price"]
            hit = (
                (alert["direction"] == "below" and cur <= alert["target"])
                or (alert["direction"] == "above" and cur >= alert["target"])
            )
            if hit:
                alert["triggered"] = True
                alert["triggered_at"] = datetime.now().isoformat()
                alert["triggered_price"] = cur
                triggered.append(alert)
        except Exception:
            continue

    _save_alerts(alerts)
    return triggered


def get_active_alerts() -> list[dict]:
    """Return all non-triggered alerts."""
    return [a for a in _load_alerts() if not a.get("triggered")]


def clear_alerts() -> dict:
    """Remove all alerts."""
    _save_alerts([])
    return {"status": "all_alerts_cleared"}


def generate_actions(signals: list[dict]) -> list[dict]:
    """
    Generate 2-3 concrete follow-up actions for the top signals.
    Rule-based for speed, not LLM-generated.
    """
    actions = []
    for sig in signals[:5]:
        ticker = sig["ticker"]
        price = sig.get("price", 0)
        rsi_sig = sig.get("rsi_signal", "NEUTRAL")
        vol_sig = sig.get("vol_signal", "NORMAL")

        action_set = {"ticker": ticker, "actions": []}

        # Action 1: Alert based on signal
        if rsi_sig == "OVERSOLD":
            action_set["actions"].append({
                "type": "set_alert",
                "label": f"Alert on {ticker} recovery (+3%)",
                "description": f"Set alert when {ticker} crosses Rs.{round(price * 1.03, 2)}",
                "params": {"ticker": ticker, "target": round(price * 1.03, 2), "direction": "above"},
            })
        elif rsi_sig == "OVERBOUGHT":
            action_set["actions"].append({
                "type": "set_alert",
                "label": f"Alert on {ticker} correction (-3%)",
                "description": f"Set alert when {ticker} drops to Rs.{round(price * 0.97, 2)}",
                "params": {"ticker": ticker, "target": round(price * 0.97, 2), "direction": "below"},
            })

        # Action 2: Volume spike alert
        if vol_sig in ("SPIKE", "ELEVATED"):
            action_set["actions"].append({
                "type": "monitor",
                "label": f"Volume alert active for {ticker}",
                "description": f"Unusual volume detected — monitor for breakout confirmation",
            })

        # Action 3: Deep analysis
        action_set["actions"].append({
            "type": "deep_analysis",
            "label": f"Run full analysis on {ticker}",
            "description": f"Run detailed technical + fundamental analysis on {ticker}",
        })

        actions.append(action_set)

    return actions
