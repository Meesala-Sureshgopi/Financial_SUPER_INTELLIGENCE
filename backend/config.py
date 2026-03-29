"""
Centralized configuration for API keys, model routing, and app constants.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")


def _parse_priority(raw_priority: str) -> list[str]:
    providers = [item.strip().lower() for item in raw_priority.split(",") if item.strip()]
    valid = {"gemini", "groq", "huggingface"}
    return [item for item in providers if item in valid]


# API keys
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
HF_TOKEN = os.getenv("HUGGINGFACE_API_TOKEN", "")


# LLM model registry
LLM_MODELS = {
    "gemini": {
        "primary": os.getenv("GEMINI_MODEL_PRIMARY", "gemini-3.1-flash-lite-preview"),
        "coder": os.getenv("GEMINI_MODEL_CODER", "gemini-3.1-flash-lite-preview"),
        "fast": os.getenv("GEMINI_MODEL_FAST", "gemini-3.1-flash-lite-preview"),
    },
    "groq": {
        "primary": os.getenv("GROQ_MODEL_PRIMARY", "llama-3.3-70b-versatile"),
        "coder": os.getenv("GROQ_MODEL_CODER", "qwen-2.5-coder-32b"),
        "fast": os.getenv("GROQ_MODEL_FAST", "llama-3.1-8b-instant"),
    },
    "huggingface": {
        "primary": os.getenv("HF_MODEL_PRIMARY", "Qwen/Qwen2.5-72B-Instruct"),
        "small": os.getenv("HF_MODEL_SMALL", "Qwen/Qwen2.5-7B-Instruct"),
        "coder": os.getenv("HF_MODEL_CODER", "Qwen/Qwen2.5-Coder-32B-Instruct"),
    },
}


# Priority order for fallback
LLM_PRIORITY = _parse_priority(os.getenv("LLM_PRIORITY", "gemini,groq,huggingface")) or [
    "gemini",
    "groq",
    "huggingface",
]


# Default Watchlist (Nifty 50)
DEFAULT_WATCHLIST = [
    "RELIANCE",
    "TCS",
    "HDFCBANK",
    "INFY",
    "ICICIBANK",
    "HINDUNILVR",
    "ITC",
    "SBI",
    "BHARTIARTL",
    "L&T",
    "BAJFINANCE",
    "KOTAKBANK",
    "AXISBANK",
    "ADANIENT",
    "ASIANPAINT",
    "MARUTI",
    "TITAN",
    "SUNPHARMA",
    "ULTRACEMCO",
    "WIPRO",
    "JSWSTEEL",
    "POWERGRID",
    "NTPC",
    "M&M",
    "ADANIPORTS",
    "HCLTECH",
    "ONGC",
    "TATASTEEL",
    "COALINDIA",
    "BAJAJFINSV",
    "TECHM",
    "GRASIM",
    "SBILIFE",
    "HINDALCO",
    "NESTLEIND",
    "BRITANNIA",
    "CIPLA",
    "TATAELXSI",
    "TATAMOTORS",
    "EICHERMOT",
    "DRREDDY",
    "BPCL",
    "APOLLOHOSP",
    "DIVISLAB",
    "HEROMOTOCO",
    "UPL",
    "BAJAJ-AUTO",
    "LT",
    "HDFCLIFE",
    "INDUSINDBK",
]


# Sector mapping
SECTOR_MAP = {
    "TCS": "IT",
    "INFY": "IT",
    "WIPRO": "IT",
    "HCLTECH": "IT",
    "TECHM": "IT",
    "TATAELXSI": "IT",
    "HDFCBANK": "Banking",
    "ICICIBANK": "Banking",
    "SBIN": "Banking",
    "AXISBANK": "Banking",
    "KOTAKBANK": "Banking",
    "INDUSINDBK": "Banking",
    "RELIANCE": "Energy",
    "ONGC": "Energy",
    "BPCL": "Energy",
    "COALINDIA": "Energy",
    "POWERGRID": "Energy",
    "NTPC": "Energy",
    "SUNPHARMA": "Pharma",
    "CIPLA": "Pharma",
    "DRREDDY": "Pharma",
    "DIVISLAB": "Pharma",
    "APOLLOHOSP": "Pharma",
    "TATAMOTORS": "Auto",
    "MARUTI": "Auto",
    "M&M": "Auto",
    "EICHERMOT": "Auto",
    "HEROMOTOCO": "Auto",
    "BAJAJ-AUTO": "Auto",
    "HINDUNILVR": "FMCG",
    "ITC": "FMCG",
    "NESTLEIND": "FMCG",
    "BRITANNIA": "FMCG",
    "UPL": "FMCG",
    "TITAN": "Consumer",
    "ASIANPAINT": "Consumer",
    "BAJFINANCE": "Finance",
    "BAJAJFINSV": "Finance",
    "HDFCLIFE": "Finance",
    "SBILIFE": "Finance",
    "LT": "Infrastructure",
    "L&T": "Infrastructure",
    "GRASIM": "Infrastructure",
    "ULTRACEMCO": "Infrastructure",
    "BHARTIARTL": "Telecom",
    "JSWSTEEL": "Metals",
    "TATASTEEL": "Metals",
    "HINDALCO": "Metals",
    "ADANIENT": "Diversified",
    "ADANIPORTS": "Logistics",
}


# Impact multipliers (historical sector response)
IMPACT_MULTIPLIERS = {
    "rbi_rate_cut": {
        "Banking": 1.8,
        "Auto": 1.2,
        "Realty": 2.1,
        "IT": 0.3,
        "Finance": 1.5,
        "FMCG": 0.4,
        "Energy": 0.6,
        "Infrastructure": 1.0,
    },
    "sector_regulation": {
        "Pharma": 2.5,
        "Finance": 1.9,
        "Telecom": 1.6,
        "IT": 1.2,
        "Banking": 1.4,
        "Energy": 1.3,
    },
    "earnings_surprise": {
        "IT": 1.8,
        "Banking": 1.5,
        "Pharma": 1.6,
        "FMCG": 1.2,
        "Auto": 1.4,
    },
}


# Paths
DATA_DIR = Path(__file__).parent / "data"
PORTFOLIO_FILE = DATA_DIR / "portfolio.json"
ALERTS_FILE = DATA_DIR / "alerts.json"
CACHE_FILE = DATA_DIR / "market_cache.pkl"
