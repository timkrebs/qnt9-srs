"""
Rate limiting module for auth service.

Provides in-memory rate limiting to protect authentication endpoints
against brute-force attacks. Uses a sliding window algorithm for accurate
request counting.

Note: For production with multiple instances, replace with Redis-based
rate limiting for distributed coordination.
"""

import time
from collections import defaultdict
from dataclasses import dataclass, field
from threading import Lock
from typing import Dict, Optional, Tuple

from fastapi import HTTPException, Request, status

from .logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class RateLimitConfig:
    """Configuration for a rate limit rule."""

    max_requests: int  # Maximum number of requests allowed
    window_seconds: int  # Time window in seconds
    block_duration_seconds: int = (
        0  # How long to block after exceeding limit (0 = no block)
    )


@dataclass
class ClientState:
    """State tracking for a single client."""

    requests: list = field(default_factory=list)  # Timestamps of requests
    blocked_until: float = 0.0  # Unix timestamp when block expires


class RateLimiter:
    """
    In-memory rate limiter with sliding window algorithm.

    Tracks request timestamps per client IP and enforces rate limits.
    Thread-safe for concurrent access.

    Attributes:
        config: Rate limit configuration
        _clients: Dictionary mapping client IPs to their state
        _lock: Thread lock for concurrent access
    """

    def __init__(self, config: RateLimitConfig) -> None:
        """
        Initialize rate limiter with configuration.

        Args:
            config: Rate limit configuration
        """
        self.config = config
        self._clients: Dict[str, ClientState] = defaultdict(ClientState)
        self._lock = Lock()
        self._last_cleanup = time.time()
        self._cleanup_interval = 60.0  # Cleanup every 60 seconds

    def _cleanup_old_entries(self, now: float) -> None:
        """Remove expired entries to prevent memory leaks."""
        if now - self._last_cleanup < self._cleanup_interval:
            return

        self._last_cleanup = now
        cutoff = now - self.config.window_seconds - self.config.block_duration_seconds

        # Remove clients with no recent activity
        expired_clients = [
            ip
            for ip, state in self._clients.items()
            if (not state.requests or state.requests[-1] < cutoff)
            and state.blocked_until < now
        ]

        for ip in expired_clients:
            del self._clients[ip]

        if expired_clients:
            logger.debug(
                f"Cleaned up {len(expired_clients)} expired rate limit entries"
            )

    def _get_client_ip(self, request: Request) -> str:
        """
        Extract client IP from request.

        Handles X-Forwarded-For header for proxied requests.

        Args:
            request: FastAPI request object

        Returns:
            Client IP address
        """
        # Check for forwarded header (reverse proxy)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # Take the first IP (original client)
            return forwarded.split(",")[0].strip()

        # Fall back to direct client IP
        if request.client:
            return request.client.host

        return "unknown"

    def check_rate_limit(self, request: Request) -> Tuple[bool, Optional[int]]:
        """
        Check if request is within rate limit.

        Args:
            request: FastAPI request object

        Returns:
            Tuple of (is_allowed, retry_after_seconds)
            retry_after_seconds is None if allowed, otherwise seconds to wait
        """
        client_ip = self._get_client_ip(request)
        now = time.time()

        with self._lock:
            # Periodic cleanup
            self._cleanup_old_entries(now)

            state = self._clients[client_ip]

            # Check if client is blocked
            if state.blocked_until > now:
                retry_after = int(state.blocked_until - now) + 1
                logger.warning(
                    "Rate limited client still blocked",
                    extra={
                        "extra_fields": {
                            "client_ip": client_ip,
                            "retry_after_seconds": retry_after,
                        }
                    },
                )
                return False, retry_after

            # Remove requests outside the current window
            window_start = now - self.config.window_seconds
            state.requests = [ts for ts in state.requests if ts > window_start]

            # Check if limit exceeded
            if len(state.requests) >= self.config.max_requests:
                # Apply block if configured
                if self.config.block_duration_seconds > 0:
                    state.blocked_until = now + self.config.block_duration_seconds
                    retry_after = self.config.block_duration_seconds
                else:
                    # Calculate when oldest request will expire
                    retry_after = int(state.requests[0] - window_start) + 1

                logger.warning(
                    "Rate limit exceeded",
                    extra={
                        "extra_fields": {
                            "client_ip": client_ip,
                            "requests_in_window": len(state.requests),
                            "max_requests": self.config.max_requests,
                            "retry_after_seconds": retry_after,
                        }
                    },
                )
                return False, retry_after

            # Record this request
            state.requests.append(now)

            logger.debug(
                "Rate limit check passed",
                extra={
                    "extra_fields": {
                        "client_ip": client_ip,
                        "requests_in_window": len(state.requests),
                        "remaining": self.config.max_requests - len(state.requests),
                    }
                },
            )
            return True, None

    def get_remaining(self, request: Request) -> int:
        """
        Get remaining requests for client in current window.

        Args:
            request: FastAPI request object

        Returns:
            Number of remaining requests allowed
        """
        client_ip = self._get_client_ip(request)
        now = time.time()

        with self._lock:
            state = self._clients.get(client_ip)
            if not state:
                return self.config.max_requests

            if state.blocked_until > now:
                return 0

            window_start = now - self.config.window_seconds
            active_requests = len([ts for ts in state.requests if ts > window_start])
            return max(0, self.config.max_requests - active_requests)


# Pre-configured rate limiters for different endpoints
# Auth endpoints: 5 attempts per minute, 5 minute block on exceed
auth_rate_limiter = RateLimiter(
    RateLimitConfig(
        max_requests=5,
        window_seconds=60,
        block_duration_seconds=300,  # 5 minute block after exceeding
    )
)

# Password reset: 3 attempts per hour (prevent email spam)
password_reset_rate_limiter = RateLimiter(
    RateLimitConfig(
        max_requests=3,
        window_seconds=3600,
        block_duration_seconds=0,  # No block, just enforce limit
    )
)

# General API: 100 requests per minute
general_rate_limiter = RateLimiter(
    RateLimitConfig(
        max_requests=100,
        window_seconds=60,
        block_duration_seconds=0,
    )
)


def check_auth_rate_limit(request: Request) -> None:
    """
    FastAPI dependency to check auth rate limit.

    Raises HTTPException 429 if rate limit exceeded.

    Args:
        request: FastAPI request object

    Raises:
        HTTPException: 429 Too Many Requests if limit exceeded
    """
    is_allowed, retry_after = auth_rate_limiter.check_rate_limit(request)

    if not is_allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many authentication attempts. Please try again later.",
            headers={"Retry-After": str(retry_after)},
        )


def check_password_reset_rate_limit(request: Request) -> None:
    """
    FastAPI dependency to check password reset rate limit.

    Args:
        request: FastAPI request object

    Raises:
        HTTPException: 429 Too Many Requests if limit exceeded
    """
    is_allowed, retry_after = password_reset_rate_limiter.check_rate_limit(request)

    if not is_allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many password reset requests. Please try again later.",
            headers={"Retry-After": str(retry_after)},
        )
