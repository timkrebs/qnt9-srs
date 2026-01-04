"""
Distributed rate limiter using Redis.

Implements sliding window rate limiting with Redis for multi-instance support.
"""

import logging
import time
from typing import Optional

from redis.asyncio import Redis

from ..domain.exceptions import RateLimitExceededException

logger = logging.getLogger(__name__)


class DistributedRateLimiter:
    """
    Redis-based distributed rate limiter using sliding window algorithm.

    Supports horizontal scaling by storing request timestamps in Redis.
    Multiple service instances can share the same rate limits.
    """

    def __init__(
        self,
        redis_client: Redis,
        max_requests: int,
        window_seconds: int,
        name: str = "default",
        key_prefix: str = "rate_limit",
    ):
        """
        Initialize distributed rate limiter.

        Args:
            redis_client: Async Redis client
            max_requests: Maximum requests allowed per window
            window_seconds: Time window duration in seconds
            name: Rate limiter name for logging
            key_prefix: Redis key prefix for namespacing
        """
        self.redis_client = redis_client
        self.name = name
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.key_prefix = key_prefix

    def _get_redis_key(self, identifier: str) -> str:
        """
        Generate Redis key for rate limit tracking.

        Args:
            identifier: Unique identifier (user_id, IP, API key, etc.)

        Returns:
            Redis key string
        """
        return f"{self.key_prefix}:{self.name}:{identifier}"

    async def acquire(self, identifier: str) -> None:
        """
        Acquire permission to make a request.

        Uses Redis sorted sets with timestamps as scores for efficient
        sliding window implementation.

        Args:
            identifier: Unique identifier for rate limiting (user_id, IP, etc.)

        Raises:
            RateLimitExceededException: If rate limit would be exceeded
        """
        now = time.time()
        window_start = now - self.window_seconds
        redis_key = self._get_redis_key(identifier)

        try:
            pipe = self.redis_client.pipeline()

            pipe.zremrangebyscore(redis_key, 0, window_start)

            pipe.zcard(redis_key)

            pipe.zadd(redis_key, {str(now): now})

            pipe.expire(redis_key, self.window_seconds + 10)

            results = await pipe.execute()

            current_count = results[1]

            if current_count >= self.max_requests:
                oldest_timestamp = await self.redis_client.zrange(
                    redis_key, 0, 0, withscores=True
                )

                if oldest_timestamp:
                    oldest_time = oldest_timestamp[0][1]
                    retry_after = int(self.window_seconds - (now - oldest_time)) + 1
                else:
                    retry_after = self.window_seconds

                logger.warning(
                    "Rate limit exceeded for '%s' (identifier: %s): %d/%d requests in %ds",
                    self.name,
                    identifier,
                    current_count,
                    self.max_requests,
                    self.window_seconds,
                )

                await self.redis_client.zrem(redis_key, str(now))

                raise RateLimitExceededException(
                    limit=self.max_requests,
                    window_seconds=self.window_seconds,
                    retry_after=retry_after,
                )

            logger.debug(
                "Rate limiter '%s' (identifier: %s): %d/%d requests in window",
                self.name,
                identifier,
                current_count + 1,
                self.max_requests,
            )

        except RateLimitExceededException:
            raise
        except Exception as e:
            logger.error("Error in distributed rate limiter '%s': %s", self.name, e)
            logger.warning("Falling back to allow request due to rate limiter error")

    async def get_current_usage(self, identifier: str) -> dict:
        """
        Get current rate limit usage statistics for identifier.

        Args:
            identifier: Unique identifier

        Returns:
            Dictionary with usage statistics
        """
        try:
            now = time.time()
            window_start = now - self.window_seconds
            redis_key = self._get_redis_key(identifier)

            await self.redis_client.zremrangebyscore(redis_key, 0, window_start)

            current_requests = await self.redis_client.zcard(redis_key)

            return {
                "name": self.name,
                "identifier": identifier,
                "current_requests": current_requests,
                "max_requests": self.max_requests,
                "window_seconds": self.window_seconds,
                "usage_percent": round((current_requests / self.max_requests) * 100, 2),
            }

        except Exception as e:
            logger.error("Error getting usage stats for '%s': %s", self.name, e)
            return {
                "name": self.name,
                "identifier": identifier,
                "error": str(e),
            }

    async def reset(self, identifier: str) -> None:
        """
        Reset rate limiter for specific identifier.

        Args:
            identifier: Unique identifier to reset
        """
        try:
            redis_key = self._get_redis_key(identifier)
            await self.redis_client.delete(redis_key)
            logger.info(
                "Rate limiter '%s' reset for identifier: %s", self.name, identifier
            )

        except Exception as e:
            logger.error(
                "Error resetting rate limiter '%s' for %s: %s", self.name, identifier, e
            )

    async def reset_all(self) -> None:
        """
        Reset all rate limits for this limiter.

        WARNING: This deletes all rate limit data for this named limiter.
        """
        try:
            pattern = f"{self.key_prefix}:{self.name}:*"
            cursor = 0
            deleted_count = 0

            while True:
                cursor, keys = await self.redis_client.scan(
                    cursor, match=pattern, count=100
                )

                if keys:
                    await self.redis_client.delete(*keys)
                    deleted_count += len(keys)

                if cursor == 0:
                    break

            logger.info(
                "Rate limiter '%s' reset all: deleted %d keys", self.name, deleted_count
            )

        except Exception as e:
            logger.error("Error resetting all for rate limiter '%s': %s", self.name, e)


class HybridRateLimiter:
    """
    Hybrid rate limiter with distributed Redis backend and local fallback.

    Attempts to use Redis for distributed rate limiting, but falls back
    to local in-memory limiting if Redis is unavailable.
    """

    def __init__(
        self,
        redis_client: Optional[Redis],
        max_requests: int,
        window_seconds: int,
        name: str = "default",
    ):
        """
        Initialize hybrid rate limiter.

        Args:
            redis_client: Async Redis client (None for local-only mode)
            max_requests: Maximum requests allowed per window
            window_seconds: Time window duration in seconds
            name: Rate limiter name
        """
        self.name = name
        self.max_requests = max_requests
        self.window_seconds = window_seconds

        if redis_client:
            self.distributed_limiter = DistributedRateLimiter(
                redis_client, max_requests, window_seconds, name
            )
            self.mode = "distributed"
            logger.info("HybridRateLimiter '%s' initialized in distributed mode", name)
        else:
            from .rate_limiter import RateLimiter

            self.local_limiter = RateLimiter(max_requests, window_seconds, name)
            self.mode = "local"
            logger.warning(
                "HybridRateLimiter '%s' initialized in local-only mode", name
            )

    async def acquire(self, identifier: str = "global") -> None:
        """
        Acquire permission to make a request.

        Args:
            identifier: Unique identifier for distributed mode

        Raises:
            RateLimitExceededException: If rate limit exceeded
        """
        if self.mode == "distributed":
            await self.distributed_limiter.acquire(identifier)
        else:
            self.local_limiter.acquire()

    async def get_current_usage(self, identifier: str = "global") -> dict:
        """
        Get current rate limit usage.

        Args:
            identifier: Unique identifier for distributed mode

        Returns:
            Usage statistics dictionary
        """
        if self.mode == "distributed":
            return await self.distributed_limiter.get_current_usage(identifier)
        else:
            stats = self.local_limiter.get_current_usage()
            stats["mode"] = "local"
            return stats
