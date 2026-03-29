import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).parent.parent / "backend"))

from data.nse_client import nse_client

async def test_nse():
    print("Testing NSE Connection (Snapshot API)...")
    deals = await nse_client.get_bulk_deals()
    
    if deals:
        print(f"SUCCESS: Fetched {len(deals)} items from NSE Snapshot.")
        print("-" * 30)
        for deal in deals[:3]:
            ticker = deal.get("symbol") or deal.get("symbolName")
            action = deal.get("buySell") or deal.get("nature")
            qty = deal.get("quantity") or deal.get("qty")
            print(f"[{ticker}] {action}: {qty} shares")
    else:
        print("FAILED: No deals found or 404/403 occurred.")

if __name__ == "__main__":
    asyncio.run(test_nse())
