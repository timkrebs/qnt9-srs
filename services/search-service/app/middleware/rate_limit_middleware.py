"""
Rate limiting middleware for distributed rate limiting.

Provides request-level rate limiting using Redis-backed distributed
rate limiter with tier-based limits.
"""

import logging
from typing import Callable, Dict

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from ..core.auth import get_current_user
from ..infrastructure.distributed_rate_limiter import HybridRateLimiter

logger = logging.getLogger(__name__)


# Rate limits by tier (requests per minute)
RATE_LIMITS: Dict[str, int] = {
    "anonymous": 10,
    "free": 30,
    "paid": 100,
    "enterprise": 1000,
}


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Distributed rate limiting middleware.

    Applies tier-based rate limits to all API requests using
    Redis-backed distributed rate limiter for multi-instance deployments.
    """

    def __init__(self, app, redis_manager):
        """
        Initialize middleware.

        Args:
            app: FastAPI application
            redis_manager: RedisConnectionManager instance
        """
        super().__init__(app)
        self.redis_manager = redis_manager
        self.rate_limiter = None

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with rate limiting.

        Args:
            request: Incoming request
            call_next: Next middleware/handler

        Returns:
            Response or rate limit error
        """
        # Skip rate limiting for health/metrics endpoints
        if request.url.path in ["/health", "/metrics", "/"]:
            return await call_next(request)

        # Initialize rate limiter on first request
        if self.rate_limiter is None:
            redis_client = await self.redis_manager.get_client()
            self.rate_limiter = HybridRateLimiter(redis_client)

        # Get user tier
        tier = "anonymous"
        user_id = None

        try:
            # Extract token from Authorization header
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                from fastapi.security import HTTPAuthorizationCredentials

                credentials = HTTPAuthorizationCredentials(
                    scheme="Bearer",
                    credentials=auth_header[7:],  # Remove "Bearer " prefix
                )
                user = await get_current_user(credentials)
                if user:
                    tier = user.tier
                    user_id = user.id
        except Exception as e:
            logger.warning(f"Failed to get user tier: {e}")
            tier = "anonymous"

        # Get rate limit for tier
        limit = RATE_LIMITS.get(tier, RATE_LIMITS["anonymous"])

        # Create identifier (tier + IP for anonymous, tier + user_id for authenticated)
        if tier == "anonymous" or user_id is None:
            client_ip = request.client.host if request.client else "unknown"
            identifier = f"{tier}:{client_ip}"
        else:
            identifier = f"{tier}:{user_id}"

        # Check rate limit
        allowed = await self.rate_limiter.check_rate_limit(
            identifier=identifier,
            limit=limit,
            window_seconds=60,
        )

        if not allowed:
            # Track rate limit hit
            from ..core.metrics_enhanced import get_metrics_tracker

            tracker = get_metrics_tracker()
            tracker.track_rate_limit_hit(tier, request.url.path)

            logger.warning(
                f"Rate limit exceeded for {identifier} on {request.url.path}"
            )

            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "rate_limit_exceeded",
                    "message": f"Rate limit of {limit} requests per minute exceeded",
                    "tier": tier,
                    "limit": limit,
                },
                headers={
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "Retry-After": "60",
                },
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(limit - 1)

        return response


def configure_rate_limiting(app, redis_manager) -> None:
    """
    Configure rate limiting middleware for application.

    Args:
        app: FastAPI application
        redis_manager: RedisConnectionManager instance
    """
    app.add_middleware(RateLimitMiddleware, redis_manager=redis_manager)
    logger.info("Distributed rate limiting configured")
