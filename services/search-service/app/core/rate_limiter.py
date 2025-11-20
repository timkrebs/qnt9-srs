"""
Tier-based rate limiting for search service.

Implements in-memory rate limiting with different limits per user tier.
For production, consider using Redis for distributed rate limiting.
"""

import time
from collections import defaultdict
from typing import Any, Dict, List, Tuple

import structlog
from fastapi import HTTPException, status

logger = structlog.get_logger(__name__)


class TierBasedRateLimiter:
    """
    Rate limiter with tier-based limits.

    Limits:
    - Anonymous: 10 requests/minute
    - Free (logged in): 30 requests/minute
    - Paid: 100 requests/minute

    Uses sliding window algorithm to track requests.
    Stores request timestamps in memory per user/IP.

    Note: For production with multiple instances, use Redis-based
    distributed rate limiting instead of in-memory storage.
    """

    def __init__(self):
        """Initialize rate limiter with empty request tracking."""
        self.requests: Dict[str, List[float]] = defaultdict(list)

        # Tier limits: (requests_per_window, window_seconds)
        self.limits: Dict[str, Tuple[int, int]] = {
            "anonymous": (10, 60),
            "free": (30, 60),
            "paid": (100, 60),
        }

    async def check_rate_limit(self, user_id: str, tier: str) -> None:
        """
        Check if request is within rate limit.

        Args:
            user_id: User ID or IP address for anonymous users
            tier: User tier (anonymous, free, paid)

        Raises:
            HTTPException: 429 if rate limit exceeded

        Example:
            rate_limiter = TierBasedRateLimiter()

            # For authenticated user
            await rate_limiter.check_rate_limit(user.id, user.tier)

            # For anonymous user
            await rate_limiter.check_rate_limit(request.client.host, "anonymous")
        """
        limit, window = self.limits.get(tier, self.limits["anonymous"])

        now = time.time()
        user_requests = self.requests[user_id]

        # Remove old requests outside the time window
        cutoff_time = now - window
        user_requests[:] = [
            req_time for req_time in user_requests if req_time > cutoff_time
        ]

        # Check if limit exceeded
        if len(user_requests) >= limit:
            # Calculate retry-after time
            oldest_request = user_requests[0]
            retry_after = int(window - (now - oldest_request)) + 1

            logger.warning(
                "Rate limit exceeded",
                user_id=user_id,
                tier=tier,
                requests=len(user_requests),
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

        # Add current request timestamp
        user_requests.append(now)

        logger.debug(
            "Rate limit check passed",
            user_id=user_id,
            tier=tier,
            count=len(user_requests),
            limit=limit,
            remaining=limit - len(user_requests),
        )

    def get_remaining_requests(self, user_id: str, tier: str) -> int:
        """
        Get number of remaining requests for user.

        Args:
            user_id: User ID or IP address
            tier: User tier

        Returns:
            Number of remaining requests in current window
        """
        limit, window = self.limits.get(tier, self.limits["anonymous"])

        now = time.time()
        user_requests = self.requests[user_id]

        # Remove old requests
        cutoff_time = now - window
        user_requests[:] = [
            req_time for req_time in user_requests if req_time > cutoff_time
        ]

        remaining = max(0, limit - len(user_requests))
        return remaining

    def reset_user_limits(self, user_id: str) -> None:
        """
        Reset rate limits for a specific user.

        Useful for testing or manual intervention.

        Args:
            user_id: User ID to reset
        """
        if user_id in self.requests:
            del self.requests[user_id]
            logger.info("Rate limit reset", user_id=user_id)

    def get_stats(self) -> Dict[str, Any]:
        """
        Get rate limiter statistics.

        Returns:
            Dictionary with stats about tracked users and requests
        """
        now = time.time()
        active_users = 0
        total_requests = 0

        for user_id, requests in self.requests.items():
            # Count only requests in last 5 minutes as "active"
            recent_requests = [req for req in requests if now - req < 300]
            if recent_requests:
                active_users += 1
                total_requests += len(recent_requests)

        return {
            "tracked_users": len(self.requests),
            "active_users_5min": active_users,
            "total_requests_5min": total_requests,
            "limits": self.limits,
        }


# Global rate limiter instance
# In production, consider using Redis-based distributed rate limiting
rate_limiter = TierBasedRateLimiter()
