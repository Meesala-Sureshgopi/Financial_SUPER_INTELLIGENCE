import httpx
import logging
from typing import List, Optional, Dict, Any
import asyncio

logger = logging.getLogger(__name__)

NSE_BASE = "https://www.nseindia.com/api"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept":     "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer":    "https://www.nseindia.com/market-data/bulk-deals",
}

class NSEClient:
    def __init__(self):
        # We need a client that preserves cookies correctly
        self._client = httpx.AsyncClient(headers=HEADERS, timeout=20, follow_redirects=True)
        self._initialized = False

    async def _init_session(self):
        """Establish session by visiting homepage first (standard NSE requirement)."""
        if not self._initialized:
            try:
                # First hit main page to get cookies
                await self._client.get("https://www.nseindia.com/", timeout=10)
                # Small delay to ensure cookies are set
                await asyncio.sleep(1)
                self._initialized = True
                logger.info("✅ NSE Session Initialized Successfully.")
            except Exception as e:
                logger.error(f"Failed to initialize NSE session: {e}")

    async def get_bulk_deals(self) -> List[Dict[str, Any]]:
        """Fetch bulk deals from NSE API."""
        await self._init_session()
        try:
            # Using the new snapshot endpoint found in browser investigation
            r = await self._client.get(f"{NSE_BASE}/snapshot-capital-market-largedeal")
            if r.status_code == 200:
                data = r.json()
                # Bulk deals are inside the snapshot object
                return data.get("BULK_DEALS_DATA", [])
            logger.warning(f"NSE bulk-deals API returned status {r.status_code}")
        except Exception as e:
            logger.error(f"NSE bulk-deals fetch error: {e}")
        return []

    async def get_insider_trades(self, symbol: str) -> List[Dict[str, Any]]:
        """Fetch insider trades (PIT) for a symbol."""
        await self._init_session()
        try:
            r = await self._client.get(
                f"{NSE_BASE}/corporates-pit",
                params={"symbol": symbol, "category": "bulk_corp"}
            )
            if r.status_code == 200:
                data = r.json()
                return data.get("data", [])
        except Exception as e:
            logger.error(f"NSE insider trades fetch error for {symbol}: {e}")
        return []

    async def get_corporate_announcements(self, symbol: str) -> List[Dict[str, Any]]:
        """Fetch corporate announcements for a symbol."""
        await self._init_session()
        try:
            r = await self._client.get(
                f"{NSE_BASE}/corporate-announcements",
                params={"index": "equities", "symbol": symbol}
            )
            if r.status_code == 200:
                return r.json()
        except Exception as e:
            logger.error(f"NSE announcements fetch error for {symbol}: {e}")
        return []

    async def get_quote_equity(self, symbol: str) -> Dict[str, Any]:
        """Fetch real-time quote for equity symbol."""
        await self._init_session()
        try:
            r = await self._client.get(
                f"{NSE_BASE}/quote-equity",
                params={"symbol": symbol}
            )
            if r.status_code == 200:
                return r.json()
        except Exception as e:
            logger.error(f"NSE quote fetch error for {symbol}: {e}")
        return {}

# Singleton instance
nse_client = NSEClient()
