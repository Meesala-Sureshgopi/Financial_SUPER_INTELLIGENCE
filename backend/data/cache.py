import json
import logging
import asyncio
import os
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

# Cache TTL in seconds
CACHE_TTL = {
    "price":        60,     # 1 min
    "bulk_deals":   300,    # 5 min
    "news":         900,    # 15 min
    "fundamentals": 86400, # 24 hrs
    "fii_flow":     3600,  # 1 hr
    "backtest":     604800, # 7 days
}

class Cache:
    def __init__(self):
        self._redis = None
        self._memory = {}
        self._use_redis = False
        
        # Try to connect to Redis if REDIS_URL is set
        redis_url = os.getenv("REDIS_URL")
        if redis_url:
            try:
                import redis.asyncio as redis
                self._redis = redis.from_url(redis_url, decode_responses=True)
                self._use_redis = True
                logger.info(f"Connected to Redis at {redis_url}")
            except Exception as e:
                logger.warning(f"Failed to connect to Redis: {e}. Falling back to in-memory cache.")

    async def get(self, key: str) -> Optional[Any]:
        if self._use_redis:
            try:
                data = await self._redis.get(key)
                return json.loads(data) if data else None
            except Exception as e:
                logger.warning(f"Redis get error: {e}")
        
        # Memory fallback
        entry = self._memory.get(key)
        if entry:
            val, expiry = entry
            if asyncio.get_event_loop().time() < expiry:
                return val
            else:
                del self._memory[key]
        return None

    async def set(self, key: str, value: Any, ttl: int):
        if self._use_redis:
            try:
                await self._redis.setex(key, ttl, json.dumps(value))
                return
            except Exception as e:
                logger.warning(f"Redis set error: {e}")
        
        # Memory fallback
        expiry = asyncio.get_event_loop().time() + ttl
        self._memory[key] = (value, expiry)

    async def cached_get(self, key: str, ttl_type: str, fetch_fn: Callable):
        """Fetch from cache, or call fetch_fn and cache result."""
        cached = await self.get(key)
        if cached is not None:
            return cached
            
        data = await fetch_fn()
        if data is not None:
            ttl = CACHE_TTL.get(ttl_type, 300)
            await self.set(key, data, ttl)
        return data

# Singleton instance
cache = Cache()
