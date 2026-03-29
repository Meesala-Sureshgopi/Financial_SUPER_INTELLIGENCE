import asyncio
import aiosqlite
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "backend" / "data" / "avalon.db"

async def seed():
    print(f"Seeding portfolio data into {DB_PATH}...")
    async with aiosqlite.connect(DB_PATH) as db:
        # 1. Create demo user
        await db.execute(
            "INSERT OR IGNORE INTO users (id, name, risk_profile) VALUES (?, ?, ?)",
            ("demo_user_123", "Demo User", "MODERATE")
        )
        
        # 2. Add holdings
        holdings = [
            ("demo_user_123", "HINDUNILVR", 280, 2400.0, "FMCG"),
            ("demo_user_123", "INFY", 150, 3100.0, "IT"),
            ("demo_user_123", "SUNPHARMA", 500, 1150.0, "PHARMA")
        ]
        
        for h in holdings:
            await db.execute(
                "INSERT OR REPLACE INTO portfolio_holdings (user_id, ticker, qty, avg_price, sector) VALUES (?, ?, ?, ?, ?)",
                h
            )
        
        await db.commit()
    print("SUCCESS: Seed complete.")

if __name__ == "__main__":
    asyncio.run(seed())
