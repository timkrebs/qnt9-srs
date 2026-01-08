"""
Distributed rate limiter using Redis.

Provides production-ready rate limiting that works across
multiple service instances using Redis for state management.
"""

from datetime import datetime, timedelta
from typing import Tuple

import redis.asyncio as redis
from redis.asyncio import Redis
from redis.exceptions import RedisError

from .logging_config import get_logger

logger = get_logger(__name__)


class RedisRateLimiter:
    """
    Distributed rate limiter using Redis with sliding window algorithm.

    Uses Redis sorted sets to implement accurate sliding window rate limiting
    that works correctly across multiple service instances.
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        prefix: str = "ratelimit:",
        window_seconds: int = 60,
        max_requests: int = 60,
    ):
        """
        Initialize Redis rate limiter.

        Args:
            redis_url: Redis connection URL
            prefix: Key prefix for rate limit data
            window_seconds: Time window in seconds
            max_requests: Maximum requests allowed in window
        """
        self.redis_url = redis_url
        self.prefix = prefix
        self.window_seconds = window_seconds
        self.max_requests = max_requests
        self.client: Redis = None

    async def connect(self) -> None:
        """Establish Redis connection."""
        if self.client is not None:
            return

        try:
            self.client = await redis.from_url(
                self.redis_url,
                max_connections=50,
                socket_timeout=5,
                socket_connect_timeout=5,
                decode_responses=True,
            )

            await self.client.ping()

            logger.info(
                "Redis rate limiter connected",
                extra={
                    "extra_fields": {
                        "redis_url": self.redis_url.split("@")[-1],
                        "window_seconds": self.window_seconds,
                        "max_requests": self.max_requests,
                    }
                },
            )
        except Exception as e:
            logger.error(f"Failed to connect to Redis for rate limiting: {e}")
            self.client = None
            raise

    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self.client:
            await self.client.close()
            self.client = None
            logger.info("Redis rate limiter disconnected")

    def _make_key(self, identifier: str) -> str:
        """Generate namespaced rate limit key."""
        return f"{self.prefix}{identifier}"

    async def is_allowed(
        self,
        identifier: str,
        max_requests: int = None,
        window_seconds: int = None,
    ) -> Tuple[bool, int, int]:
        """
        Check if request is allowed under rate limit.

        Uses sliding window algorithm with Redis sorted set:
        1. Remove expired entries (older than window)
        2. Count current entries in window
        3. Add new entry if under limit
        4. Set expiration on key

        Args:
            identifier: Unique identifier (e.g., user_id, IP address)
            max_requests: Override default max requests
            window_seconds: Override default window

        Returns:
            Tuple of (is_allowed, remaining, reset_time)
            - is_allowed: True if request is allowed
            - remaining: Number of requests remaining
            - reset_time: Unix timestamp when window resets
        """
        if not self.client:
            logger.warning("Redis not connected, allowing request (no rate limit)")
            return True, max_requests or self.max_requests, 0

        max_reqs = max_requests if max_requests is not None else self.max_requests
        window = window_seconds if window_seconds is not None else self.window_seconds

        key = self._make_key(identifier)
        now = datetime.utcnow()
        window_start = now - timedelta(seconds=window)

        try:
            pipe = self.client.pipeline()

            pipe.zremrangebyscore(key, 0, window_start.timestamp())

            pipe.zcard(key)

            score = now.timestamp()
            pipe.zadd(key, {str(score): score})

            pipe.expire(key, window + 10)

            results = await pipe.execute()

            current_count = results[1]

            if current_count < max_reqs:
                remaining = max_reqs - current_count - 1
                reset_time = int((now + timedelta(seconds=window)).timestamp())
                return True, remaining, reset_time
            else:
                await self.client.zrem(key, str(score))

                remaining = 0
                reset_time = int((now + timedelta(seconds=window)).timestamp())

                logger.warning(
                    f"Rate limit exceeded for {identifier}",
                    extra={
                        "extra_fields": {
                            "identifier": identifier,
                            "current_count": current_count,
                            "max_requests": max_reqs,
                        }
                    },
                )

                return False, remaining, reset_time

        except RedisError as e:
            logger.error(f"Redis error in rate limiter: {e}")
            return True, max_reqs, 0
        except Exception as e:
            logger.error(f"Unexpected error in rate limiter: {e}")
            return True, max_reqs, 0

    async def reset(self, identifier: str) -> bool:
        """
        Reset rate limit for identifier.

        Args:
            identifier: Identifier to reset

        Returns:
            True if reset successful
        """
        if not self.client:
            return False

        try:
            key = self._make_key(identifier)
            await self.client.delete(key)
            logger.info(f"Rate limit reset for {identifier}")
            return True
        except RedisError as e:
            logger.error(f"Redis error on reset: {e}")
            return False

    async def get_current_count(self, identifier: str) -> int:
        """
        Get current request count in window.

        Args:
            identifier: Identifier to check

        Returns:
            Current request count
        """
        if not self.client:
            return 0

        try:
            key = self._make_key(identifier)
            now = datetime.utcnow()
            window_start = now - timedelta(seconds=self.window_seconds)

            await self.client.zremrangebyscore(key, 0, window_start.timestamp())

            return await self.client.zcard(key)

        except RedisError as e:
            logger.error(f"Redis error getting count: {e}")
            return 0


_rate_limiter_instance: RedisRateLimiter = None


async def get_redis_rate_limiter() -> RedisRateLimiter:
    """
    Get global Redis rate limiter instance.

    Returns:
        Initialized RedisRateLimiter instance
    """
    global _rate_limiter_instance

    if _rate_limiter_instance is None:
        from .config import settings

        redis_url = getattr(settings, "REDIS_URL", "redis://localhost:6379/0")
        rate_limit_prefix = getattr(settings, "RATE_LIMIT_PREFIX", "finio:ratelimit:")
        rate_limit_window = getattr(settings, "RATE_LIMIT_WINDOW_SECONDS", 60)
        rate_limit_max = getattr(settings, "RATE_LIMIT_MAX_REQUESTS", 60)

        _rate_limiter_instance = RedisRateLimiter(
            redis_url=redis_url,
            prefix=rate_limit_prefix,
            window_seconds=rate_limit_window,
            max_requests=rate_limit_max,
        )

        await _rate_limiter_instance.connect()

    return _rate_limiter_instance
