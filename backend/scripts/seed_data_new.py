import asyncio
import sqlite3
import json
import uuid
import sys
import os
from pathlib import Path

# Add backend to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from data.rag_pipeline import ingest_filing

DB_PATH = Path(__file__).parent.parent / "data" / "avalon.db"

# ════════════════════ SCENARIO DATA ════════════════════

SCENARIOS = {
    "HINDUNILVR": {
        "filing": """Hindustan Unilever Limited (HUL) - Bulk Deal Disclosure. 
        Promoter/Chairman has disposed of 4.2% stake in the open market via a bulk deal on NSE. 
        Execution price: ₹2,450 per share (6% discount to previous close of ₹2,606). 
        Reason for sale: Personal liquidity and diversification. 
        Historical context: This is the first promoter sale in 5 years. 
        Management commentary from Q3: 'Demand environment remains challenging in rural sectors.'""",
        "url": "https://www.nseindia.com/filings/hul_bulk_mar2026.pdf",
        "holding": {"qty": 280, "avg_price": 2400.0, "sector": "FMCG"}
    },
    "INFY": {
        "filing": """Infosys Limited (INFY) - Quarterly Shareholding Pattern. 
        Foreign Institutional Investors (FII) have reduced their absolute stake by 1.2% this quarter. 
        Large block deals observed by top European pension funds. 
        Earnings Guidance: 4-7% CC revenue growth maintained for FY26. 
        RSI at 78 denotes overbought territory after 52-week breakout at ₹3,842.""",
        "url": "https://www.nseindia.com/filings/infy_shp_q4.pdf",
        "holding": {"qty": 150, "avg_price": 3100.0, "sector": "IT"}
    },
    "SUNPHARMA": {
        "filing": """Sun Pharmaceutical Industries - Regulatory Impact Update. 
        New NPPA pricing caps on 24 formulation categories are expected to impact Sun Pharma's domestic margins by 180-220 bps. 
        Pharma sector witnessing higher competition in US generics. 
        RBI repo rate cut of 25bps is mildly positive for the company's floating rate debt servicing.""",
        "url": "https://www.nseindia.com/filings/sun_reg_update.pdf",
        "holding": {"qty": 500, "avg_price": 1150.0, "sector": "PHARMA"}
    }
}

async def seed_database():
    print("--- Seeding Avalon Copilot Database ---")
    
    # 1. Initialize SQLite
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create tables if not exist (using current schema)
    with open(Path(__file__).parent.parent / "db" / "schema.sql", 'r') as f:
        cursor.executescript(f.read())
        
    # 2. Create Default User
    user_id = "demo_user_123"
    cursor.execute("REPLACE INTO users (id, name, risk_profile) VALUES (?, ?, ?)", 
                   (user_id, "Retail Investor", "MODERATE"))
    
    # 3. Seed Portfolio & RAG
    print("  - Ingesting filings into ChromaDB (RAG)...")
    for ticker, data in SCENARIOS.items():
        # SQLite Holding
        cursor.execute("""
            REPLACE INTO portfolio_holdings (user_id, ticker, qty, avg_price, sector) 
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, ticker, data["holding"]["qty"], data["holding"]["avg_price"], data["holding"]["sector"]))
        
        # ChromaDB Filing
        await ingest_filing(ticker, data["filing"], data["url"])
        print(f"    [OK] {ticker} context ingested.")
        
    # 4. Seed Backtest Patterns
    cursor.execute("REPLACE INTO pattern_backtest (ticker, pattern, success_rate, sample_size) VALUES (?, ?, ?, ?)",
                   ("INFY", "52W_BREAKOUT", 0.63, 24))
    
    conn.commit()
    conn.close()
    print("\n[COMPLETE] SEEDING DONE. System ready for Track 6 Scenarios.")

if __name__ == "__main__":
    asyncio.run(seed_database())
