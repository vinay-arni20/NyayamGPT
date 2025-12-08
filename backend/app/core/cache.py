"""
NyayamGPT - Cache Service
=========================
Redis-based caching service for storing query results, sessions, and rate limiting.
Includes mode-aware caching with different TTLs per mode.
"""

import json
import hashlib
from datetime import datetime
from typing import Any, Callable, Literal, Optional, TypeVar

import redis.asyncio as redis

from app.core.config import settings
from app.core.logging import logger


# Mode type alias
ModeType = Literal["normal", "lawyer", "qa", "web", "deep"]

# Mode-specific cache TTLs (in seconds) - Extended for quota optimization
MODE_CACHE_TTL: dict[ModeType, int] = {
    "normal": 21600,     # 6 hours (was 1h)
    "lawyer": 28800,     # 8 hours (was 2h, more detailed)
    "qa": 10800,         # 3 hours (was 30min, quick answers cache longer)
    "web": 3600,         # 1 hour (was 15min, web results less volatile than thought)
    "deep": 43200,       # 12 hours (was 4h, expensive to generate)
}

# Cache key prefixes
CACHE_PREFIX = {
    "query": "nyayam:query",
    "session": "nyayam:session",
    "user": "nyayam:user",
    "rate_limit": "nyayam:rate",
    "metrics": "nyayam:metrics",
}


class CacheService:
    """
    Advanced caching service with mode-aware TTLs and metrics.
    """
    
    def __init__(self):
        self.redis: Optional[redis.Redis] = None
        self._connected = False
        
    async def connect(self) -> bool:
        """Initialize Redis connection."""
        try:
            self.redis = redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_timeout=5.0,
                socket_connect_timeout=5.0,
            )
            # Test connection
            await self.redis.ping()
            self._connected = True
            logger.info("Redis connection established", url=settings.redis_url)
            return True
        except Exception as e:
            logger.warning("Redis connection failed, caching disabled", error=str(e))
            self._connected = False
            return False
    
    @property
    def is_connected(self) -> bool:
        """Check if Redis is connected."""
        return self._connected and self.redis is not None
        
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if not self.is_connected:
            return None
            
        try:
            value = await self.redis.get(key)
            if value:
                # Track cache hit
                await self._increment_metric("cache_hits")
                return json.loads(value)
            else:
                # Track cache miss
                await self._increment_metric("cache_misses")
            return None
        except Exception as e:
            logger.error("Cache get failed", error=str(e), key=key)
            return None
            
    async def set(
        self, 
        key: str, 
        value: Any, 
        expire: Optional[int] = None,
        mode: Optional[ModeType] = None
    ) -> bool:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache (must be JSON serializable)
            expire: TTL in seconds (optional, uses mode TTL if not provided)
            mode: Chat mode for mode-specific TTL
            
        Returns:
            True if cached successfully
        """
        if not self.is_connected:
            return False
            
        try:
            # Determine TTL
            if expire is None:
                expire = MODE_CACHE_TTL.get(mode or "normal", 3600)
            
            await self.redis.set(key, json.dumps(value), ex=expire)
            await self._increment_metric("cache_writes")
            return True
        except Exception as e:
            logger.error("Cache set failed", error=str(e), key=key)
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete a key from cache."""
        if not self.is_connected:
            return False
            
        try:
            await self.redis.delete(key)
            return True
        except Exception as e:
            logger.error("Cache delete failed", error=str(e), key=key)
            return False
    
    async def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching a pattern."""
        if not self.is_connected:
            return 0
            
        try:
            keys = []
            async for key in self.redis.scan_iter(match=pattern):
                keys.append(key)
            
            if keys:
                await self.redis.delete(*keys)
            return len(keys)
        except Exception as e:
            logger.error("Cache delete pattern failed", error=str(e), pattern=pattern)
            return 0
    
    async def get_or_set(
        self,
        key: str,
        factory: Callable[[], Any],
        expire: Optional[int] = None,
        mode: Optional[ModeType] = None
    ) -> Any:
        """
        Get value from cache or compute and cache it.
        
        Args:
            key: Cache key
            factory: Function to compute value if not cached
            expire: TTL in seconds
            mode: Chat mode for mode-specific TTL
            
        Returns:
            Cached or computed value
        """
        # Try cache first
        value = await self.get(key)
        if value is not None:
            return value
        
        # Compute value
        value = await factory() if callable(factory) else factory
        
        # Cache result
        await self.set(key, value, expire=expire, mode=mode)
        
        return value
    
    # Rate limiting methods
    async def check_rate_limit(
        self, 
        key: str, 
        limit: int, 
        window: int = 60
    ) -> tuple[bool, int]:
        """
        Check if rate limit is exceeded.
        
        Args:
            key: Rate limit key (e.g., user ID or IP)
            limit: Maximum requests allowed
            window: Time window in seconds
            
        Returns:
            (is_allowed, remaining_requests)
        """
        if not self.is_connected:
            return True, limit
            
        try:
            full_key = f"{CACHE_PREFIX['rate_limit']}:{key}"
            current = await self.redis.get(full_key)
            
            if current is None:
                await self.redis.set(full_key, 1, ex=window)
                return True, limit - 1
            
            count = int(current)
            if count >= limit:
                return False, 0
            
            await self.redis.incr(full_key)
            return True, limit - count - 1
            
        except Exception as e:
            logger.error("Rate limit check failed", error=str(e))
            return True, limit
    
    # Session caching methods
    async def cache_session_messages(
        self,
        session_id: str,
        user_id: str,
        messages: list[dict]
    ) -> bool:
        """Cache session messages for quick retrieval."""
        key = f"{CACHE_PREFIX['session']}:{user_id}:{session_id}"
        return await self.set(key, messages, expire=86400)  # 24 hours
    
    async def get_session_messages(
        self,
        session_id: str,
        user_id: str
    ) -> Optional[list[dict]]:
        """Get cached session messages."""
        key = f"{CACHE_PREFIX['session']}:{user_id}:{session_id}"
        return await self.get(key)
    
    async def invalidate_session_cache(
        self,
        session_id: str,
        user_id: str
    ) -> bool:
        """Invalidate session cache."""
        key = f"{CACHE_PREFIX['session']}:{user_id}:{session_id}"
        return await self.delete(key)
    
    # Query caching methods
    async def cache_query_result(
        self,
        query: str,
        mode: ModeType,
        result: dict,
        session_id: Optional[str] = None
    ) -> bool:
        """
        Cache a query result.
        
        Args:
            query: User query
            mode: Chat mode
            result: Response to cache
            session_id: Optional session ID for context-aware caching
        """
        key = self.generate_query_key(query, mode, session_id)
        return await self.set(key, result, mode=mode)
    
    async def get_cached_query(
        self,
        query: str,
        mode: ModeType,
        session_id: Optional[str] = None
    ) -> Optional[dict]:
        """Get cached query result."""
        key = self.generate_query_key(query, mode, session_id)
        return await self.get(key)
    
    # Metrics methods
    async def _increment_metric(self, metric: str) -> None:
        """Increment a cache metric counter."""
        if not self.is_connected:
            return
            
        try:
            key = f"{CACHE_PREFIX['metrics']}:{metric}"
            await self.redis.incr(key)
        except Exception:
            pass  # Metrics are non-critical
    
    async def get_metrics(self) -> dict[str, int]:
        """Get cache metrics."""
        if not self.is_connected:
            return {}
            
        try:
            metrics = {}
            for metric in ["cache_hits", "cache_misses", "cache_writes"]:
                key = f"{CACHE_PREFIX['metrics']}:{metric}"
                value = await self.redis.get(key)
                metrics[metric] = int(value) if value else 0
            
            # Calculate hit rate
            total = metrics.get("cache_hits", 0) + metrics.get("cache_misses", 0)
            metrics["hit_rate"] = (
                round(metrics.get("cache_hits", 0) / total * 100, 2) 
                if total > 0 else 0
            )
            
            return metrics
        except Exception as e:
            logger.error("Failed to get metrics", error=str(e))
            return {}
    
    async def close(self) -> None:
        """Close Redis connection."""
        if self.redis:
            await self.redis.close()
            self._connected = False
            logger.info("Redis connection closed")

    @staticmethod
    def generate_key(prefix: str, *args) -> str:
        """Generate a cache key from arguments."""
        content = "-".join(str(arg) for arg in args)
        hash_val = hashlib.md5(content.encode()).hexdigest()
        return f"{prefix}:{hash_val}"
    
    @staticmethod
    def generate_query_key(
        query: str, 
        mode: ModeType,
        session_id: Optional[str] = None
    ) -> str:
        """Generate a cache key for a query."""
        # Normalize query
        normalized = query.lower().strip()
        
        # Include session for context-aware caching
        if session_id:
            content = f"{normalized}:{mode}:{session_id}"
        else:
            content = f"{normalized}:{mode}"
        
        hash_val = hashlib.md5(content.encode()).hexdigest()
        return f"{CACHE_PREFIX['query']}:{mode}:{hash_val}"


# Singleton instance
_cache_service: Optional[CacheService] = None


async def get_cache_service() -> CacheService:
    """Get cache service singleton and ensure connection."""
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService()
        await _cache_service.connect()
    return _cache_service


async def close_cache_service() -> None:
    """Close cache service connection."""
    global _cache_service
    if _cache_service:
        await _cache_service.close()
        _cache_service = None
