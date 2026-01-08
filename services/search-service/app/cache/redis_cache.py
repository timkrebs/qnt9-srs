"""
Distributed cache implementation using Redis.

Provides production-ready caching with Redis backend that works
across multiple service instances.
"""

import pickle
from typing import Any, Optional

import redis.asyncio as redis
from redis.asyncio import Redis
from redis.exceptions import RedisError

from .logging_config import get_logger

logger = get_logger(__name__)


class RedisCache:
    """
    Distributed cache using Redis.

    Supports:
    - Automatic serialization/deserialization
    - TTL-based expiration
    - Connection pooling
    - Error handling with fallback
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        prefix: str = "cache:",
        default_ttl: int = 300,
        max_connections: int = 50,
        socket_timeout: int = 5,
        socket_connect_timeout: int = 5,
    ):
        """
        Initialize Redis cache.

        Args:
            redis_url: Redis connection URL
            prefix: Key prefix for namespacing
            default_ttl: Default TTL in seconds
            max_connections: Maximum connections in pool
            socket_timeout: Socket read/write timeout
            socket_connect_timeout: Socket connection timeout
        """
        self.prefix = prefix
        self.default_ttl = default_ttl
        self.redis_url = redis_url
        self.client: Optional[Redis] = None
        self.max_connections = max_connections
        self.socket_timeout = socket_timeout
        self.socket_connect_timeout = socket_connect_timeout

        self.hits = 0
        self.misses = 0
        self.errors = 0

    async def connect(self) -> None:
        """Establish Redis connection with connection pooling."""
        if self.client is not None:
            return

        try:
            self.client = await redis.from_url(
                self.redis_url,
                max_connections=self.max_connections,
                socket_timeout=self.socket_timeout,
                socket_connect_timeout=self.socket_connect_timeout,
                decode_responses=False,
                encoding="utf-8",
            )

            await self.client.ping()

            logger.info(
                "Redis cache connected",
                extra={
                    "extra_fields": {
                        "redis_url": self.redis_url.split("@")[-1],
                        "max_connections": self.max_connections,
                    }
                },
            )
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.client = None
            raise

    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self.client:
            await self.client.close()
            self.client = None
            logger.info("Redis cache disconnected")

    def _make_key(self, key: str) -> str:
        """Generate namespaced cache key."""
        return f"{self.prefix}{key}"

    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/error
        """
        if not self.client:
            logger.warning("Redis not connected, cache miss")
            self.misses += 1
            return None

        try:
            cache_key = self._make_key(key)
            data = await self.client.get(cache_key)

            if data is None:
                self.misses += 1
                logger.debug(f"Cache MISS: {key}")
                return None

            value = pickle.loads(data)
            self.hits += 1
            logger.debug(f"Cache HIT: {key}")
            return value

        except RedisError as e:
            logger.error(f"Redis error on get: {e}")
            self.errors += 1
            self.misses += 1
            return None
        except Exception as e:
            logger.error(f"Error deserializing cache value: {e}")
            self.errors += 1
            self.misses += 1
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> bool:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache (must be picklable)
            ttl: Time-to-live in seconds (uses default if None)

        Returns:
            True if successful, False otherwise
        """
        if not self.client:
            logger.warning("Redis not connected, cache set skipped")
            return False

        try:
            cache_key = self._make_key(key)
            serialized = pickle.dumps(value)

            ttl_seconds = ttl if ttl is not None else self.default_ttl

            await self.client.setex(cache_key, ttl_seconds, serialized)

            logger.debug(f"Cache SET: {key} (TTL: {ttl_seconds}s)")
            return True

        except RedisError as e:
            logger.error(f"Redis error on set: {e}")
            self.errors += 1
            return False
        except Exception as e:
            logger.error(f"Error serializing cache value: {e}")
            self.errors += 1
            return False

    async def delete(self, key: str) -> bool:
        """
        Delete key from cache.

        Args:
            key: Cache key to delete

        Returns:
            True if deleted, False otherwise
        """
        if not self.client:
            return False

        try:
            cache_key = self._make_key(key)
            result = await self.client.delete(cache_key)
            logger.debug(f"Cache DELETE: {key}")
            return result > 0

        except RedisError as e:
            logger.error(f"Redis error on delete: {e}")
            self.errors += 1
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        if not self.client:
            return False

        try:
            cache_key = self._make_key(key)
            return await self.client.exists(cache_key) > 0
        except RedisError:
            return False

    async def clear_pattern(self, pattern: str) -> int:
        """
        Clear all keys matching pattern.

        Args:
            pattern: Pattern to match (e.g., "user:*")

        Returns:
            Number of keys deleted
        """
        if not self.client:
            return 0

        try:
            cache_pattern = self._make_key(pattern)
            keys = []
            async for key in self.client.scan_iter(match=cache_pattern):
                keys.append(key)

            if keys:
                deleted = await self.client.delete(*keys)
                logger.info(f"Cleared {deleted} cache keys matching pattern: {pattern}")
                return deleted

            return 0

        except RedisError as e:
            logger.error(f"Redis error on clear_pattern: {e}")
            self.errors += 1
            return 0

    async def get_stats(self) -> dict:
        """Get cache statistics."""
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0

        stats = {
            "hits": self.hits,
            "misses": self.misses,
            "errors": self.errors,
            "total_requests": total,
            "hit_rate_percent": round(hit_rate, 2),
        }

        if self.client:
            try:
                info = await self.client.info("stats")
                stats["redis_total_commands"] = info.get("total_commands_processed", 0)
                stats["redis_connected_clients"] = info.get("connected_clients", 0)
            except RedisError:
                pass

        return stats


_cache_instance: Optional[RedisCache] = None


async def get_redis_cache() -> RedisCache:
    """
    Get global Redis cache instance.

    Returns:
        Initialized RedisCache instance
    """
    global _cache_instance

    if _cache_instance is None:
        from .config import settings

        redis_url = getattr(settings, "REDIS_URL", "redis://localhost:6379/0")
        cache_prefix = getattr(settings, "CACHE_PREFIX", "finio:cache:")
        default_ttl = getattr(settings, "CACHE_DEFAULT_TTL", 300)

        _cache_instance = RedisCache(
            redis_url=redis_url,
            prefix=cache_prefix,
            default_ttl=default_ttl,
        )

        await _cache_instance.connect()

    return _cache_instance
