"""
Agent Logger — Rich Terminal Output
======================================
Beautiful, colorized terminal logging showing which agent is triggered,
what data is flowing, and timing for each step.
"""
import logging
import time
import sys
from functools import wraps

# ── Color Codes ───────────────────────────────────────────────────────
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"

# Agent-specific colors
COLORS = {
    "ORCHESTRATOR": "\033[38;5;46m",   # Bright Green
    "FILING":       "\033[38;5;214m",  # Orange
    "CHART":        "\033[38;5;39m",   # Blue
    "NEWS":         "\033[38;5;205m",  # Pink
    "PORTFOLIO":    "\033[38;5;226m",  # Yellow
    "ACTION":       "\033[38;5;196m",  # Red
    "LLM":          "\033[38;5;141m",  # Purple
    "MARKET":       "\033[38;5;81m",   # Cyan
    "SIGNAL":       "\033[38;5;118m",  # Lime
    "SYSTEM":       "\033[38;5;252m",  # Light Gray
}

ICONS = {
    "ORCHESTRATOR": "🧠",
    "FILING":       "📜",
    "CHART":        "📊",
    "NEWS":         "📰",
    "PORTFOLIO":    "💼",
    "ACTION":       "⚡",
    "LLM":          "🤖",
    "MARKET":       "📈",
    "SIGNAL":       "📡",
    "SYSTEM":       "⚙️",
}


class AgentFormatter(logging.Formatter):
    """Custom formatter with colors and agent icons."""
    
    def format(self, record):
        # Determine agent from logger name
        name = record.name.split(".")[-1].upper() if "." in record.name else "SYSTEM"
        color = COLORS.get(name, COLORS["SYSTEM"])
        icon = ICONS.get(name, "⚙️")
        
        timestamp = time.strftime("%H:%M:%S")
        level_colors = {
            "DEBUG": "\033[38;5;245m",
            "INFO": "\033[38;5;252m",
            "WARNING": "\033[38;5;214m",
            "ERROR": "\033[38;5;196m",
        }
        level_color = level_colors.get(record.levelname, "")
        
        formatted = (
            f"{DIM}{timestamp}{RESET} "
            f"{color}{BOLD}{icon} [{name:12s}]{RESET} "
            f"{level_color}{record.getMessage()}{RESET}"
        )
        return formatted


def setup_logging():
    """Configure rich terminal logging for all agents."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(AgentFormatter())
    handler.setLevel(logging.INFO)
    
    # Set up root logger
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    
    # Remove existing handlers to avoid duplicates
    root.handlers = []
    root.addHandler(handler)
    
    # Suppress noisy libraries
    for lib in ["urllib3", "httpx", "httpcore", "yfinance", "peewee"]:
        logging.getLogger(lib).setLevel(logging.WARNING)
    
    # Create agent-specific loggers
    loggers = {}
    for agent in COLORS:
        name = f"copilot.{agent.lower()}"
        _log = logging.getLogger(name)
        loggers[agent] = _log
    
    return loggers


def log_agent_start(agent_name: str, action: str, details: str = ""):
    """Log when an agent starts processing."""
    logger = logging.getLogger(f"copilot.{agent_name.lower()}")
    msg = f"▶ STARTED: {action}"
    if details:
        msg += f" | {details}"
    logger.info(msg)


def log_agent_end(agent_name: str, action: str, result: str = ""):
    """Log when an agent finishes."""
    logger = logging.getLogger(f"copilot.{agent_name.lower()}")
    msg = f"✅ DONE: {action}"
    if result:
        msg += f" → {result}"
    logger.info(msg)


def log_agent_error(agent_name: str, action: str, error: str):
    """Log agent errors."""
    logger = logging.getLogger(f"copilot.{agent_name.lower()}")
    logger.error(f"❌ FAILED: {action} — {error}")


def timed_agent(agent_name: str, action: str):
    """Decorator that logs agent execution time."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = logging.getLogger(f"copilot.{agent_name.lower()}")
            logger.info(f"▶ STARTED: {action}")
            start = time.time()
            try:
                result = func(*args, **kwargs)
                elapsed = time.time() - start
                logger.info(f"✅ DONE: {action} ({elapsed:.2f}s)")
                return result
            except Exception as e:
                elapsed = time.time() - start
                logger.error(f"❌ FAILED: {action} ({elapsed:.2f}s) — {e}")
                raise
        return wrapper
    return decorator
