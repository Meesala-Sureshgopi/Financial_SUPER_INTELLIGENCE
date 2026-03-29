import aiosqlite
import logging
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent / "data" / "avalon.db"
SCHEMA_PATH = Path(__file__).parent / "schema.sql"

async def init_db():
    """Initialize the SQLite database with the schema."""
    if not DB_PATH.parent.exists():
        DB_PATH.parent.mkdir(parents=True)
    
    async with aiosqlite.connect(DB_PATH) as db:
        with open(SCHEMA_PATH, "r") as f:
            schema = f.read()
        await db.executescript(schema)
        await db.commit()
    logger.info(f"Database initialized at {DB_PATH}")

class Database:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path

    async def execute(self, query, params=()):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(query, params)
            await db.commit()
            return cursor

    async def fetch_all(self, query, params=()):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def fetch_one(self, query, params=()):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(query, params) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def get_user_portfolio(self, user_id: str = "demo_user_123") -> Dict[str, Any]:
        """Fetch all holdings for a specific user to be used in agent analysis."""
        query = "SELECT ticker, qty, avg_price FROM portfolio_holdings WHERE user_id = ?"
        rows = await self.fetch_all(query, (user_id,))
        # Convert to the dictionary format expected by the 7-agent pipeline
        return {
            row["ticker"]: {"qty": row["qty"], "avg_price": row["avg_price"]}
            for row in rows
        }

    async def get_user_portfolio_detailed(self, user_id: str = "demo_user_123") -> Dict[str, Any]:
        """Return a frontend-friendly portfolio payload with live values and aggregate totals."""
        from tools.market_data import get_live_price

        query = "SELECT ticker, qty, avg_price, sector FROM portfolio_holdings WHERE user_id = ?"
        rows = await self.fetch_all(query, (user_id,))

        holdings: Dict[str, Any] = {}
        total_value = 0.0
        total_cost = 0.0

        for row in rows:
            price_data = get_live_price(row["ticker"])
            current_price = float(price_data.get("price") or 0.0)
            qty = int(row["qty"] or 0)
            avg_price = float(row["avg_price"] or 0.0)
            market_value = round(current_price * qty, 2)
            cost_basis = round(avg_price * qty, 2)
            pnl = round(market_value - cost_basis, 2)
            pnl_pct = round((pnl / cost_basis) * 100, 2) if cost_basis else 0.0

            holdings[row["ticker"]] = {
                "qty": qty,
                "avg_price": avg_price,
                "current_price": current_price,
                "market_value": market_value,
                "pnl": pnl,
                "pnl_pct": pnl_pct,
                "sector": row.get("sector") or "Unknown",
            }
            total_value += market_value
            total_cost += cost_basis

        total_pnl = round(total_value - total_cost, 2)

        return {
            "user_id": user_id,
            "holdings": holdings,
            "total_value": round(total_value, 2),
            "total_cost": round(total_cost, 2),
            "total_pnl": total_pnl,
        }

# Singleton instance
db = Database()
