"""
Redis-based distributed rate limiting for search service.

Implements a sliding window rate limiter using Redis for distributed
coordination across multiple service instances.

This module provides a drop-in replacement for the in-memory rate limiter
when running in production with multiple instances.
"""

import time
from typing import Any, Dict, Tuple

import structlog
from fastapi import HTTPException, status

logger = structlog.get_logger(__name__)


class RedisRateLimiter:
    """
    Distributed rate limiter using Redis sorted sets.

    Uses Redis sorted sets for sliding window rate limiting:
    - Each user has a sorted set with timestamps as scores
    - Old entries are automatically expired
    - Works across multiple service instances

    Limits:
    - Anonymous: 10 requests/minute
    - Free (logged in): 30 requests/minute
    - Paid: 100 requests/minute
    """

    def __init__(self, redis_client=None):
        """
        Initialize Redis rate limiter.

        Args:
            redis_client: Redis async client instance
        """
        self.redis = redis_client
        self.key_prefix = "ratelimit:"

        # Tier limits: (requests_per_window, window_seconds)
        self.limits: Dict[str, Tuple[int, int]] = {
            "anonymous": (10, 60),
            "free": (30, 60),
            "paid": (100, 60),
        }

    def _get_key(self, user_id: str) -> str:
        """Get Redis key for user's rate limit data."""
        return f"{self.key_prefix}{user_id}"

    async def check_rate_limit(self, user_id: str, tier: str) -> None:
        """
        Check if request is within rate limit using Redis.

        Args:
            user_id: User ID or IP address for anonymous users
            tier: User tier (anonymous, free, paid)

        Raises:
            HTTPException: 429 if rate limit exceeded
        """
        if self.redis is None:
            logger.warning("Redis not configured, skipping rate limit check")
            return

        limit, window = self.limits.get(tier, self.limits["anonymous"])
        key = self._get_key(user_id)
        now = time.time()
        window_start = now - window

        try:
            # Use Redis pipeline for atomic operations
            pipe = self.redis.pipeline()

            # Remove old entries outside the window
            pipe.zremrangebyscore(key, 0, window_start)

            # Count current requests in window
            pipe.zcard(key)

            # Execute pipeline
            results = await pipe.execute()
            current_count = results[1]

            # Check if limit exceeded
            if current_count >= limit:
                # Get oldest request time to calculate retry-after
                oldest = await self.redis.zrange(key, 0, 0, withscores=True)
                if oldest:
                    oldest_time = oldest[0][1]
                    retry_after = int(window - (now - oldest_time)) + 1
                else:
                    retry_after = window

                logger.warning(
                    "Rate limit exceeded (Redis)",
                    user_id=user_id,
                    tier=tier,
                    requests=current_count,
                    limit=limit,
                    window=window,
                )

                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "error": "rate_limit_exceeded",
                        "message": f"Rate limit exceeded. {tier.title()} tier: {limit} requests per {window}s",
                        "tier": tier,
                        "limit": limit,
                        "window": window,
                        "retry_after": retry_after,
                    },
                    headers={"Retry-After": str(retry_after)},
                )

            # Add current request with expiry
            pipe2 = self.redis.pipeline()
            pipe2.zadd(key, {str(now): now})
            pipe2.expire(key, window + 1)  # Key expires shortly after window
            await pipe2.execute()

            logger.debug(
                "Rate limit check passed (Redis)",
                user_id=user_id,
                tier=tier,
                count=current_count + 1,
                limit=limit,
                remaining=limit - current_count - 1,
            )

        except HTTPException:
            raise
        except Exception as e:
            # On Redis error, log and allow request (fail open)
            logger.error(
                "Redis rate limit check failed",
                user_id=user_id,
                error=str(e),
            )

    async def get_remaining_requests(self, user_id: str, tier: str) -> int:
        """
        Get number of remaining requests for user.

        Args:
            user_id: User ID or IP address
            tier: User tier

        Returns:
            Number of remaining requests in current window
        """
        if self.redis is None:
            return -1

        limit, window = self.limits.get(tier, self.limits["anonymous"])
        key = self._get_key(user_id)
        now = time.time()
        window_start = now - window

        try:
            # Clean old entries and count
            pipe = self.redis.pipeline()
            pipe.zremrangebyscore(key, 0, window_start)
            pipe.zcard(key)
            results = await pipe.execute()

            current_count = results[1]
            return max(0, limit - current_count)

        except Exception as e:
            logger.error("Failed to get remaining requests", error=str(e))
            return -1

    async def reset_user_limits(self, user_id: str) -> None:
        """
        Reset rate limits for a specific user.

        Args:
            user_id: User ID to reset
        """
        if self.redis is None:
            return

        key = self._get_key(user_id)
        try:
            await self.redis.delete(key)
            logger.info("Rate limit reset (Redis)", user_id=user_id)
        except Exception as e:
            logger.error("Failed to reset rate limit", user_id=user_id, error=str(e))

    async def get_stats(self) -> Dict[str, Any]:
        """
        Get rate limiter statistics.

        Returns:
            Dictionary with stats about rate limiting
        """
        if self.redis is None:
            return {"error": "Redis not configured"}

        try:
            # Count all rate limit keys
            keys = await self.redis.keys(f"{self.key_prefix}*")

            return {
                "backend": "redis",
                "tracked_users": len(keys),
                "limits": self.limits,
            }
        except Exception as e:
            return {"error": str(e)}


class HybridRateLimiter:
    """
    Hybrid rate limiter that uses Redis when available, falls back to in-memory.

    This provides the best of both worlds:
    - Distributed rate limiting when Redis is configured
    - Local rate limiting as fallback for development/single instance

    Usage:
        limiter = HybridRateLimiter(redis_client=redis)
        await limiter.check_rate_limit(user_id, tier)
    """

    def __init__(self, redis_client=None):
        """
        Initialize hybrid rate limiter.

        Args:
            redis_client: Optional Redis async client instance
        """
        from .rate_limiter import TierBasedRateLimiter

        self._redis_limiter = RedisRateLimiter(redis_client) if redis_client else None
        self._memory_limiter = TierBasedRateLimiter()
        self._use_redis = redis_client is not None

        logger.info(
            "HybridRateLimiter initialized",
            backend="redis" if self._use_redis else "memory",
        )

    async def check_rate_limit(self, user_id: str, tier: str) -> None:
        """
        Check rate limit using appropriate backend.

        Args:
            user_id: User ID or IP address
            tier: User tier
        """
        if self._use_redis and self._redis_limiter:
            await self._redis_limiter.check_rate_limit(user_id, tier)
        else:
            await self._memory_limiter.check_rate_limit(user_id, tier)

    def get_remaining_requests(self, user_id: str, tier: str) -> int:
        """Get remaining requests for user."""
        if self._use_redis and self._redis_limiter:
            # Note: This would need to be async in real usage
            return -1  # Placeholder
        return self._memory_limiter.get_remaining_requests(user_id, tier)

    async def get_stats(self) -> Dict[str, Any]:
        """Get rate limiter statistics."""
        if self._use_redis and self._redis_limiter:
            return await self._redis_limiter.get_stats()
        return self._memory_limiter.get_stats()
