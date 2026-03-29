"""
News Fetcher
==============
Multi-source news ingestion with categorization and sentiment scoring.
Uses Google RSS (free, no API key needed).
"""
import feedparser
import requests
import logging
from typing import List

logger = logging.getLogger(__name__)

NSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://www.nseindia.com",
}


def fetch_news_headlines(ticker: str, max_results: int = 8) -> list[dict]:
    """Fetch recent news via Google RSS (free, no key)."""
    try:
        url = f"https://news.google.com/rss/search?q={ticker}+NSE+India+stock&hl=en-IN&gl=IN"
        feed = feedparser.parse(url)
        results = []
        for entry in feed.entries[:max_results]:
            results.append({
                "title": entry.get("title", ""),
                "link": entry.get("link", ""),
                "published": entry.get("published", ""),
                "source": entry.get("source", {}).get("title", "Unknown"),
            })
        return results
    except Exception as e:
        logger.warning(f"News fetch failed for {ticker}: {e}")
        return []


def fetch_bulk_deals() -> list[dict]:
    """Fetch today's bulk deals from NSE."""
    try:
        session = requests.Session()
        session.get("https://www.nseindia.com", headers=NSE_HEADERS, timeout=5)
        resp = session.get("https://www.nseindia.com/api/bulk-deals", headers=NSE_HEADERS, timeout=5)
        data = resp.json().get("data", [])
        return data if data else []
    except Exception:
        return []


def fetch_block_deals() -> list[dict]:
    """Fetch today's block deals from NSE."""
    try:
        session = requests.Session()
        session.get("https://www.nseindia.com", headers=NSE_HEADERS, timeout=5)
        resp = session.get("https://www.nseindia.com/api/block-deals", headers=NSE_HEADERS, timeout=5)
        data = resp.json().get("data", [])
        return data if data else []
    except Exception:
        return []


def fetch_bse_announcements() -> list[dict]:
    """Fetch corporate announcements from BSE XML feed."""
    try:
        url = "https://api.bseindia.com/BseIndiaAPI/api/AnnGetData/w"
        params = {
            "strCat": "-1", "strPrevDate": "", "strScrip": "",
            "strSearch": "P", "strToDate": "", "strType": "C", "subcategory": "-1",
        }
        resp = requests.get(url, params=params, headers=NSE_HEADERS, timeout=5)
        return resp.json() if resp.status_code == 200 else []
    except Exception:
        return []


def classify_news_type(headline: str) -> str:
    """Classify headline into one of the main news categories."""
    headline_lower = headline.lower()
    
    if any(w in headline_lower for w in ["rbi", "repo rate", "interest rate", "monetary policy", "rate cut", "rate hike"]):
        return "monetary_policy"
    elif any(w in headline_lower for w in ["regulation", "sebi", "regulatory", "compliance", "ban", "restriction", "price control"]):
        return "sector_regulation"
    elif any(w in headline_lower for w in ["quarterly", "earnings", "profit", "revenue", "results", "q1", "q2", "q3", "q4"]):
        return "earnings"
    elif any(w in headline_lower for w in ["fii", "dii", "foreign", "institutional"]):
        return "institutional_flow"
    elif any(w in headline_lower for w in ["bulk deal", "block deal", "insider", "promoter", "stake"]):
        return "corporate_filing"
    else:
        return "general"


def score_headline_sentiment(headline: str) -> float:
    """Simple keyword-based sentiment score [-1.0 to 1.0]."""
    positive = ["surge", "rally", "gain", "profit", "bullish", "upgrade", "growth",
                 "beat", "strong", "record", "high", "up", "buy", "positive", "outperform"]
    negative = ["crash", "fall", "drop", "loss", "bearish", "downgrade", "weak",
                 "miss", "low", "sell", "negative", "underperform", "decline", "cut"]
    
    words = headline.lower().split()
    pos_count = sum(1 for w in words if any(p in w for p in positive))
    neg_count = sum(1 for w in words if any(n in w for n in negative))
    
    total = pos_count + neg_count
    if total == 0:
        return 0.0
    return round((pos_count - neg_count) / total, 2)
