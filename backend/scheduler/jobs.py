import asyncio
import json
import logging
import os
from pathlib import Path

import yfinance as yf
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from api.events import alert_queue
from data.nse_client import nse_client
from db.session import db
from graph.orchestrator import run_analysis

logger = logging.getLogger("copilot.scheduler")
scheduler = AsyncIOScheduler()
TICKERS_FILE = Path(__file__).parent.parent / "data" / "tickers.json"
ENABLE_AUTONOMOUS_MONITORING = os.getenv("ENABLE_AUTONOMOUS_MONITORING", "false").lower() == "true"
ENABLE_UNIVERSAL_SCAN = os.getenv("ENABLE_UNIVERSAL_SCAN", "false").lower() == "true"


class UniversalMonitor:
    """Rotate across the stock universe in smaller batches."""

    def __init__(self):
        try:
            if TICKERS_FILE.exists():
                with open(TICKERS_FILE, "r", encoding="utf-8") as handle:
                    data = json.load(handle)
                    self.tickers = [ticker["symbol"] for ticker in data]
            else:
                self.tickers = ["RELIANCE", "TCS", "HDFCBANK", "INFY", "HINDUNILVR"]
        except Exception as exc:
            logger.error(f"Failed to load tickers.json: {exc}")
            self.tickers = ["RELIANCE", "TCS", "INFY"]

        self.cursor = 0
        self.batch_size = 15

    def get_next_batch(self):
        if not self.tickers:
            return []

        start = self.cursor
        end = min(start + self.batch_size, len(self.tickers))
        batch = self.tickers[start:end]
        self.cursor = 0 if end >= len(self.tickers) else end
        return batch


monitor = UniversalMonitor()


async def poll_nse_bulk_deals():
    """Poll latest bulk and block deals from the official NSE snapshot."""
    logger.info("Polling NSE snapshot for bulk deals...")
    try:
        deals = await nse_client.get_bulk_deals()
        portfolio = await db.get_user_portfolio()

        for deal in deals[:5]:
            ticker = deal.get("symbol") or deal.get("symbolName")
            if not ticker:
                continue

            logger.info(f"Live signal detected: {ticker} (NSE Bulk Deal)")
            result = await run_analysis(
                ticker=ticker,
                event_type="BULK_DEAL",
                raw_event=deal,
                user_portfolio=portfolio,
            )
            if result.get("alert") and result.get("status") != "skipped":
                await alert_queue.put(result["alert"])
    except Exception as exc:
        logger.error(f"Polling NSE Bulk Deals failed: {exc}")


async def poll_universal_market():
    """Poll broader market news in rotating batches."""
    batch = monitor.get_next_batch()
    logger.info(
        f"Universal scan: processing {len(batch)} tickers "
        f"(cursor {monitor.cursor}/{len(monitor.tickers)})"
    )

    portfolio = await db.get_user_portfolio()

    for symbol in batch:
        try:
            stock = yf.Ticker(f"{symbol}.NS")
            news = stock.news
            if news:
                latest = news[0]
                result = await run_analysis(
                    ticker=symbol,
                    event_type="NEWS_GENERAL",
                    raw_event={
                        "title": latest.get("title"),
                        "url": latest.get("link"),
                        "source": latest.get("publisher"),
                    },
                    user_portfolio=portfolio,
                )
                if result.get("alert") and result.get("status") != "skipped":
                    await alert_queue.put(result["alert"])

            await asyncio.sleep(0.5)
        except Exception as exc:
            logger.debug(f"News poll for {symbol} failed: {exc}")


async def run_live_signal_refresh():
    """Fetch a fresh batch of live signals on demand."""
    await poll_nse_bulk_deals()
    if ENABLE_UNIVERSAL_SCAN:
        await poll_universal_market()


def start_scheduler():
    """Initialize autonomous background jobs only when explicitly enabled."""
    if not ENABLE_AUTONOMOUS_MONITORING:
        logger.info("Autonomous monitoring disabled. Live signal fetch is available on manual refresh only.")
        return

    scheduler.add_job(poll_nse_bulk_deals, "interval", minutes=15, id="bulk_deals_poll", replace_existing=True)
    if ENABLE_UNIVERSAL_SCAN:
        scheduler.add_job(
            poll_universal_market,
            "interval",
            minutes=15,
            id="universal_market_poll",
            replace_existing=True,
        )

    if not scheduler.running:
        scheduler.start()

    logger.info(
        "Autonomous monitoring active: bulk deals every 15 minutes"
        + (" with universal market scan enabled." if ENABLE_UNIVERSAL_SCAN else ".")
    )
