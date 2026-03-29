import json
import logging
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

sys.path.append(str(Path(__file__).parent.parent))

from api.events import alert_queue
from db.session import db, init_db
from graph.orchestrator import run_analysis
from scheduler.jobs import run_live_signal_refresh, start_scheduler
from tools.llm_provider import call_gemini_only
import re
from tools.market_data import (
    get_historical_data,
    get_live_price as fetch_live_price_data,
    get_stock_info,
    normalize_symbol,
    SYMBOL_ALIASES,
)
from tools.news_fetcher import fetch_news_headlines, score_headline_sentiment

logger = logging.getLogger(__name__)
TICKERS_FILE = Path(__file__).parent.parent / "data" / "tickers.json"


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    start_scheduler()
    yield


app = FastAPI(title="AVALON COPILOT - Multi-Agent Intelligence", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalysisRequest(BaseModel):
    ticker: str
    user_id: Optional[str] = "demo_user_123"


class QueryRequest(BaseModel):
    query: str
    user_id: Optional[str] = "demo_user_123"


class PortfolioHoldingRequest(BaseModel):
    user_id: Optional[str] = "demo_user_123"
    ticker: str
    qty: int
    avg_price: Optional[float] = None


def load_tickers():
    if not TICKERS_FILE.exists():
        return []
    with open(TICKERS_FILE, "r", encoding="utf-8") as handle:
        return json.load(handle)


def lookup_company_name(symbol: str) -> str:
    try:
        match = next((item for item in load_tickers() if item["symbol"].upper() == symbol.upper()), None)
        if match:
            return match["name"]
    except Exception as exc:
        logger.warning(f"Company lookup failed for {symbol}: {exc}")
    return symbol


def resolve_query_company(query: str) -> tuple[Optional[str], Optional[str]]:
    query_clean = query.upper().strip()
    query_lower = query.lower()

    # 1. Check SYMBOL_ALIASES first (priority for common names like HCL, HUL)
    for alias in sorted(SYMBOL_ALIASES.keys(), key=len, reverse=True):
        if re.search(rf"\b{re.escape(alias.upper())}\b", query_clean):
            symbol = SYMBOL_ALIASES[alias]
            name = lookup_company_name(symbol)
            return normalize_symbol(symbol), name

    # 2. Check Official Symbols and Company Names
    for item in load_tickers():
        symbol = item["symbol"].upper()
        name = item["name"]
        name_lower = name.lower()
        
        if re.search(rf"\b{re.escape(symbol)}\b", query_clean):
            return normalize_symbol(symbol), name
            
        if name_lower in query_lower:
            return normalize_symbol(symbol), name

    return None, None


def format_estimated_pnl(pnl: Optional[float]) -> str:
    if pnl is None:
        return "Watchlist Alert"

    numeric_pnl = float(pnl)
    if abs(numeric_pnl) < 0.005:
        return "Watchlist Alert"

    prefix = "₹" if numeric_pnl >= 0 else "-₹"
    return f"{prefix}{abs(round(numeric_pnl, 2)):,}"


async def get_latest_analysis_snapshot(ticker: str, user_id: str = "demo_user_123") -> Optional[dict]:
    query = """
    SELECT a.*, s.ticker, s.event_type, s.net_signal
    FROM alerts a
    JOIN signals s ON a.signal_id = s.id
    WHERE s.ticker = ? AND a.user_id = ?
    ORDER BY a.created_at DESC
    LIMIT 1
    """
    return await db.fetch_one(query, (ticker, user_id))


def summarize_chart_context(hist) -> list[str]:
    if hist is None or hist.empty:
        return ["Chart context: unavailable"]

    recent = hist.tail(20)
    latest = recent.iloc[-1]
    first = recent.iloc[0]
    latest_close = round(float(latest["Close"]), 2)
    first_close = round(float(first["Close"]), 2)
    period_change = round(latest_close - first_close, 2)
    period_change_pct = round((period_change / first_close) * 100, 2) if first_close else 0.0
    period_high = round(float(recent["High"].max()), 2)
    period_low = round(float(recent["Low"].min()), 2)

    return [
        f"20-session close: {latest_close}",
        f"20-session change: {period_change} ({period_change_pct}%)",
        f"20-session high: {period_high}",
        f"20-session low: {period_low}",
    ]


def summarize_technical_context(hist) -> list[str]:
    if hist is None or hist.empty or len(hist.index) < 20:
        return ["Technical indicators: unavailable"]

    recent = hist.copy()
    close = recent["Close"]
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss.replace(0, 1e-9)
    rsi = 100 - (100 / (1 + rs))
    sma20 = close.rolling(window=20).mean()
    sma50 = close.rolling(window=50).mean()

    latest_close = round(float(close.iloc[-1]), 2)
    latest_rsi = round(float(rsi.iloc[-1]), 2) if not rsi.empty else 0.0
    latest_sma20 = round(float(sma20.iloc[-1]), 2) if not sma20.empty else latest_close
    latest_sma50 = round(float(sma50.iloc[-1]), 2) if len(recent.index) >= 50 and not sma50.empty else latest_sma20

    if latest_rsi >= 70:
        rsi_signal = "Overbought"
    elif latest_rsi <= 30:
        rsi_signal = "Oversold"
    else:
        rsi_signal = "Neutral"

    trend = "Uptrend" if latest_sma20 >= latest_sma50 else "Downtrend"

    return [
        f"Latest close: {latest_close}",
        f"RSI 14: {latest_rsi} ({rsi_signal})",
        f"SMA 20: {latest_sma20}",
        f"SMA 50: {latest_sma50}",
        f"Technical trend: {trend}",
    ]


def summarize_news_context(news_items: list[dict]) -> list[str]:
    if not news_items:
        return ["Recent web/news context: unavailable"]

    summaries = []
    for item in news_items[:4]:
        title = item.get("title", "Untitled")
        source = item.get("source", "Unknown")
        published = item.get("published", "")
        sentiment = score_headline_sentiment(title)
        sentiment_label = "positive" if sentiment > 0.2 else "negative" if sentiment < -0.2 else "neutral"
        summaries.append(f"{title} | Source: {source} | Sentiment: {sentiment_label} | Published: {published}")
    return summaries


@app.get("/")
async def root():
    return {"status": "AVALON COPILOT ACTIVE", "engine": "7-Agent LangGraph"}


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "backend", "timestamp": datetime.now().isoformat()}


@app.post("/api/analyze")
async def manual_trigger(req: AnalysisRequest):
    ticker = normalize_symbol(req.ticker.upper())
    company_name = lookup_company_name(ticker)
    user_id = req.user_id

    query = """
    SELECT a.*, s.ticker, s.event_type
    FROM alerts a
    JOIN signals s ON a.signal_id = s.id
    WHERE s.ticker = ? AND a.user_id = ? AND a.created_at > datetime('now', '-15 minutes')
    ORDER BY a.created_at DESC LIMIT 1
    """
    cached = await db.fetch_one(query, (ticker, user_id))

    if cached:
        pnl = cached["estimated_pnl"]
        return {
            "status": "cached",
            "ticker": ticker,
            "company_name": company_name,
            "action": cached["action"],
            "confidence": cached["confidence"],
            "alert": {
                "ticker": ticker,
                "company_name": company_name,
                "action": cached["action"],
                "reasoning": cached["reasoning"].split("\n") if cached["reasoning"] else [],
                "estimated_pnl": format_estimated_pnl(pnl),
                "sources": json.loads(cached["citations"]) if cached["citations"] else [],
                "confidence": cached["confidence"],
                "created_at": cached["created_at"],
            },
        }

    portfolio = await db.get_user_portfolio(user_id)
    logger.info(f"Verified Portfolio Data for {user_id}: {list(portfolio.keys())}")

    result = await run_analysis(
        ticker=ticker,
        event_type="MANUAL_SCAN",
        user_portfolio=portfolio,
    )

    result["ticker"] = ticker
    result["company_name"] = company_name

    if result.get("alert"):
        result["alert"]["ticker"] = ticker
        result["alert"]["company_name"] = company_name
        result["alert"]["created_at"] = datetime.now().isoformat()
        await alert_queue.put(result["alert"])

    return result


@app.post("/api/query")
async def copilot_query(req: QueryRequest):
    query = req.query.strip()
    if not query:
        return {"response": "Please enter a question for the copilot.", "audit_trail": []}

    ticker, company_name = resolve_query_company(query)
    audit_trail = [{"step": "Input received", "action": "Preparing Gemini copilot context"}]

    portfolio = await db.get_user_portfolio_detailed(req.user_id)
    holdings = portfolio.get("holdings", {}) if isinstance(portfolio, dict) else {}

    recent_alerts = await get_alerts_history()
    recent_summary = [
        f"{alert['ticker']} {alert['action']} ({round(float(alert.get('confidence') or 0) * 100)}%)"
        for alert in recent_alerts[:5]
    ]

    stock_context = []
    if ticker:
        audit_trail.append({"step": "Company resolved", "action": f"Matched query to {ticker}"})
        live_price_data = fetch_live_price_data(ticker)
        stock_info = get_stock_info(ticker)
        hist = get_historical_data(ticker, period="3mo")
        chart_context = summarize_chart_context(hist)
        technical_context = summarize_technical_context(hist)
        web_news = fetch_news_headlines(company_name or ticker, max_results=4)
        news_context = summarize_news_context(web_news)
        latest_analysis = await get_latest_analysis_snapshot(ticker, req.user_id)

        should_refresh_analysis = latest_analysis is None
        if latest_analysis and latest_analysis.get("created_at"):
            try:
                created_at = datetime.fromisoformat(str(latest_analysis["created_at"]).replace("Z", "+00:00"))
                should_refresh_analysis = (datetime.now(created_at.tzinfo) - created_at).total_seconds() > 1800
            except Exception:
                should_refresh_analysis = False

        if should_refresh_analysis:
            audit_trail.append({"step": "Analysis refresh", "action": f"Refreshing analyzed snapshot for {ticker}"})
            fresh_result = await manual_trigger(AnalysisRequest(ticker=ticker, user_id=req.user_id))
            latest_analysis = {
                "action": fresh_result.get("action") or fresh_result.get("alert", {}).get("action"),
                "confidence": fresh_result.get("confidence") or fresh_result.get("alert", {}).get("confidence"),
                "reasoning": "\n".join(fresh_result.get("alert", {}).get("reasoning", [])),
                "estimated_pnl": fresh_result.get("alert", {}).get("estimated_pnl"),
                "created_at": fresh_result.get("alert", {}).get("created_at"),
                "event_type": fresh_result.get("status", "CHAT_QUERY"),
                "net_signal": fresh_result.get("action") or fresh_result.get("alert", {}).get("action"),
            }

        stock_context = [
            f"Ticker: {ticker}",
            f"Company: {company_name or ticker}",
            f"Live price: {round(float(live_price_data.get('price') or 0.0), 2)}",
            f"Change: {round(float(live_price_data.get('change') or 0.0), 2)}",
            f"Change pct: {round(float(live_price_data.get('change_pct') or 0.0), 2)}",
            f"Sector: {stock_info.get('sector', 'Unknown')}",
            f"Market cap: {stock_info.get('market_cap', 'Unknown')}",
        ]
        stock_context.extend(chart_context)
        stock_context.extend(technical_context)
        stock_context.extend(["Recent web/news results:"] + news_context)
        if latest_analysis:
            reasoning_lines = latest_analysis["reasoning"].split("\n") if latest_analysis.get("reasoning") else []
            portfolio_relevance = latest_analysis.get("estimated_pnl")
            if isinstance(portfolio_relevance, str):
                portfolio_relevance_text = portfolio_relevance
            else:
                portfolio_relevance_text = format_estimated_pnl(portfolio_relevance)
            stock_context.extend(
                [
                    f"Latest analyzed action: {latest_analysis.get('action')}",
                    f"Latest net signal: {latest_analysis.get('net_signal')}",
                    f"Latest event type: {latest_analysis.get('event_type')}",
                    f"Latest confidence: {round(float(latest_analysis.get('confidence') or 0) * 100)}%",
                    f"Latest portfolio relevance: {portfolio_relevance_text}",
                    f"Latest analysis timestamp: {latest_analysis.get('created_at')}",
                    "Latest reasoning highlights: "
                    + (" | ".join(reasoning_lines[:3]) if reasoning_lines else "No reasoning saved."),
                ]
            )
            audit_trail.append({"step": "Latest analysis loaded", "action": f"Attached saved analysis context for {ticker}"})
        else:
            stock_context.append("Latest analyzed result: none saved yet for this stock.")
            audit_trail.append({"step": "Latest analysis lookup", "action": f"No saved analysis found for {ticker}"})
    else:
        audit_trail.append({"step": "Company resolution", "action": "No exact company match, answering from broader market context"})

    portfolio_context = []
    for holding_ticker, holding in list(holdings.items())[:5]:
        portfolio_context.append(
            f"{holding_ticker}: qty {holding.get('qty')}, avg {holding.get('avg_price')}, current {holding.get('current_price')}, market value {holding.get('market_value')}, pnl {holding.get('pnl')}"
        )

    system_prompt = """
You are FinSI Financial Super Intelligence, an Indian market investment copilot.
Answer clearly and concisely for a retail investor.
Use only the provided context.
If context is weak or missing, say that directly instead of making up data.
Keep answers practical and decision-oriented.
Prefer the latest analyzed result when one is available for the matched stock.
Do not say you lack chart context if RSI, moving averages, trend, price change, or recent news are present in the provided context.
When recent web/news results are present, use them as supporting context and mention the source names briefly.
"""

    prompt_parts = [
        f"User question:\n{query}",
        "Matched stock context:\n" + ("\n".join(stock_context) if stock_context else "No exact stock matched."),
        "Portfolio context:\n" + ("\n".join(portfolio_context) if portfolio_context else "No holdings available."),
        "Recent autonomous signals:\n" + ("\n".join(recent_summary) if recent_summary else "No recent signals available."),
    ]

    audit_trail.append({"step": "Gemini synthesis", "action": "Generating response with Gemini 3.1 Flash-Lite only"})
    response = call_gemini_only(
        prompt="\n\n".join(prompt_parts),
        system_prompt=system_prompt,
        task="primary",
        max_tokens=700,
        temperature=0.25,
    )

    return {
        "response": response,
        "ticker": ticker,
        "company_name": company_name,
        "audit_trail": audit_trail,
    }


@app.get("/api/alerts/stream")
async def stream_alerts():
    async def event_generator():
        while True:
            alert = await alert_queue.get()
            yield f"data: {json.dumps(alert)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/api/alerts/history")
async def get_alerts_history():
    query = """
    SELECT a.*, s.ticker, s.event_type
    FROM alerts a
    JOIN signals s ON a.signal_id = s.id
    ORDER BY a.created_at DESC
    LIMIT 20
    """
    rows = await db.fetch_all(query)

    alerts = []
    seen_tickers = set()
    for row in rows:
        ticker = row["ticker"]
        if ticker in seen_tickers:
            continue
        seen_tickers.add(ticker)

        alerts.append(
            {
                "ticker": ticker,
                "company_name": lookup_company_name(ticker),
                "action": row["action"],
                "verdict": row["action"],
                "reasoning": row["reasoning"].split("\n") if row["reasoning"] else [],
                "estimated_pnl": format_estimated_pnl(row["estimated_pnl"]),
                "sources": json.loads(row["citations"]) if row["citations"] else [],
                "confidence": row["confidence"],
                "timestamp": row["created_at"],
            }
        )
        if len(alerts) >= 10:
            break
    return alerts


@app.post("/api/alerts/live-refresh")
async def refresh_live_alerts():
    await run_live_signal_refresh()
    return await get_alerts_history()


@app.get("/api/tickers/search")
async def search_tickers(q: str = ""):
    if not q or len(q) < 3:
        return []

    try:
        all_tickers = load_tickers()
        q_upper = q.upper()
        matches = [
            ticker
            for ticker in all_tickers
            if q_upper in ticker["symbol"].upper() or q_upper in ticker["name"].upper()
        ]
        return matches[:8]
    except Exception as exc:
        logger.error(f"Ticker search error: {exc}")
        return []


@app.get("/api/portfolio")
async def get_portfolio(user_id: str = "demo_user_123"):
    return await db.get_user_portfolio_detailed(user_id)


@app.post("/api/portfolio/holdings")
async def add_portfolio_holding(req: PortfolioHoldingRequest):
    ticker = normalize_symbol(req.ticker.upper())
    live_price_data = fetch_live_price_data(ticker)
    price = req.avg_price if req.avg_price is not None else float(live_price_data.get("price") or 0.0)
    stock_info = get_stock_info(ticker)
    sector = stock_info.get("sector", "Unknown")

    await db.execute(
        """
        REPLACE INTO portfolio_holdings (user_id, ticker, qty, avg_price, sector)
        VALUES (?, ?, ?, ?, ?)
        """,
        (req.user_id, ticker, req.qty, price, sector),
    )

    return {
        "status": "ok",
        "message": f"{ticker} added to demo portfolio",
        "ticker": ticker,
        "qty": req.qty,
        "avg_price": price,
        "sector": sector,
    }


@app.post("/api/portfolio/holdings/remove")
async def remove_portfolio_holding(req: PortfolioHoldingRequest):
    ticker = normalize_symbol(req.ticker.upper())
    existing = await db.fetch_one(
        "SELECT qty FROM portfolio_holdings WHERE user_id = ? AND ticker = ?",
        (req.user_id, ticker),
    )

    if not existing:
        return {
            "status": "missing",
            "message": f"{ticker} is not currently in the portfolio",
            "ticker": ticker,
            "remaining_qty": 0,
        }

    remaining_qty = max(int(existing["qty"]) - max(req.qty, 0), 0)

    if remaining_qty > 0:
        await db.execute(
            "UPDATE portfolio_holdings SET qty = ? WHERE user_id = ? AND ticker = ?",
            (remaining_qty, req.user_id, ticker),
        )
    else:
        await db.execute(
            "DELETE FROM portfolio_holdings WHERE user_id = ? AND ticker = ?",
            (req.user_id, ticker),
        )

    return {
        "status": "ok",
        "message": f"{ticker} quantity updated",
        "ticker": ticker,
        "remaining_qty": remaining_qty,
    }


@app.get("/api/chart/{ticker}")
async def get_chart_data(ticker: str, range: str = "1mo"):
    symbol = normalize_symbol(ticker.upper())
    range_map = {
        "1mo": ("1mo", 30),
        "45d": ("3mo", 45),
        "3mo": ("3mo", 90),
        "6mo": ("6mo", 180),
        "1y": ("1y", 260),
    }
    period, points = range_map.get(range, ("1mo", 30))

    try:
        hist = get_historical_data(symbol, period=period)
        if hist is None or hist.empty:
            return []

        hist = hist.tail(points)

        return [
            {
                "x": dt.timestamp() * 1000,
                "y": [
                    round(row["Open"], 2),
                    round(row["High"], 2),
                    round(row["Low"], 2),
                    round(row["Close"], 2),
                ],
                "v": int(row["Volume"]),
            }
            for dt, row in hist.iterrows()
        ]
    except Exception as exc:
        logger.error(f"Chart fetch failed for {ticker}: {exc}")
        return []


@app.get("/api/price/{ticker}")
async def get_live_price(ticker: str):
    symbol = normalize_symbol(ticker.upper())
    try:
        live_price_data = fetch_live_price_data(symbol)
        return {
            "ticker": symbol,
            "price": round(float(live_price_data.get("price") or 0.0), 2),
            "change": round(float(live_price_data.get("change") or 0.0), 2),
            "change_pct": round(float(live_price_data.get("change_pct") or 0.0), 2),
        }
    except Exception as exc:
        logger.error(f"Price fetch failed for {ticker}: {exc}")
        return {"ticker": symbol, "price": 0.0}


@app.get("/api/stock/{ticker}")
async def get_stock_details(ticker: str):
    symbol = normalize_symbol(ticker.upper())
    info = get_stock_info(symbol)
    if "company_name" not in info:
        info["company_name"] = lookup_company_name(symbol)
    return info


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
