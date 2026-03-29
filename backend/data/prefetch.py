"""
Data Prefetch Script
======================
Pre-fetches and caches historical market data for the default watchlist.
Run this once before starting the server for faster signal computation.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import DEFAULT_WATCHLIST
from tools.market_data import get_historical_data
from tools.signal_engine import save_cache


def prefetch_all():
    """Fetch 1-year historical data for all watchlist stocks."""
    print(f"Pre-fetching data for {len(DEFAULT_WATCHLIST)} stocks...")
    cache = {}

    for i, ticker in enumerate(DEFAULT_WATCHLIST):
        print(f"  [{i+1}/{len(DEFAULT_WATCHLIST)}] {ticker}...", end=" ")
        df = get_historical_data(ticker, period="1y")
        if df is not None and not df.empty:
            cache[ticker] = df
            print(f"OK ({len(df)} rows)")
        else:
            print("SKIP (no data)")

    save_cache(cache)
    print(f"\nCached {len(cache)} stocks to disk.")
    return cache


if __name__ == "__main__":
    prefetch_all()
