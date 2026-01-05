"""
Rate limiter for API request throttling.

Prevents exceeding external API rate limits using sliding window algorithm.
"""

import logging
import time
from collections import deque
from typing import Deque

from ..domain.exceptions import RateLimitExceededException

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Sliding window rate limiter.

    Tracks request timestamps and enforces rate limits per time window.
    """

    def __init__(self, max_requests: int, window_seconds: int, name: str = "default"):
        """
        Initialize rate limiter.

        Args:
            max_requests: Maximum requests allowed per window
            window_seconds: Time window duration in seconds
            name: Rate limiter name for logging
        """
        self.name = name
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Deque[float] = deque()

    def acquire(self) -> None:
        """
        Acquire permission to make a request.

        Raises:
            RateLimitExceededException: If rate limit would be exceeded
        """
        now = time.time()
        self._clean_old_requests(now)

        if len(self.requests) >= self.max_requests:
            oldest_request = self.requests[0]
            retry_after = int(self.window_seconds - (now - oldest_request)) + 1

            logger.warning(
                f"Rate limit exceeded for '{self.name}': "
                f"{len(self.requests)}/{self.max_requests} requests in {self.window_seconds}s"
            )

            raise RateLimitExceededException(
                limit=self.max_requests,
                window_seconds=self.window_seconds,
                retry_after=retry_after,
            )

        self.requests.append(now)
        logger.debug(
            f"Rate limiter '{self.name}': {len(self.requests)}/{self.max_requests} "
            f"requests in window"
        )

    async def wait_and_acquire(self) -> None:
        """
        Wait for available capacity and acquire permission to make a request.
        
        This method waits instead of throwing RateLimitExceededException,
        making it suitable for scenarios where we want to queue requests.
        """
        import asyncio
        
        while True:
            now = time.time()
            self._clean_old_requests(now)
            
            if len(self.requests) < self.max_requests:
                # We have capacity, acquire and return
                self.requests.append(now)
                logger.debug(
                    f"Rate limiter '{self.name}': {len(self.requests)}/{self.max_requests} "
                    f"requests in window (waited)"
                )
                return
            
            # Calculate how long to wait until oldest request expires
            oldest_request = self.requests[0]
            wait_time = self.window_seconds - (now - oldest_request) + 0.05  # Small buffer
            
            if wait_time > 0:
                logger.debug(
                    f"Rate limiter '{self.name}': waiting {wait_time:.2f}s for capacity"
                )
                await asyncio.sleep(wait_time)

    def _clean_old_requests(self, now: float) -> None:
        """Remove requests outside the current window."""
        window_start = now - self.window_seconds

        while self.requests and self.requests[0] < window_start:
            self.requests.popleft()

    def get_current_usage(self) -> dict:
        """Get current rate limit usage statistics."""
        now = time.time()
        self._clean_old_requests(now)

        return {
            "name": self.name,
            "current_requests": len(self.requests),
            "max_requests": self.max_requests,
            "window_seconds": self.window_seconds,
            "usage_percent": round((len(self.requests) / self.max_requests) * 100, 2),
        }

    def reset(self) -> None:
        """Reset rate limiter (clear all tracked requests)."""
        logger.info(f"Rate limiter '{self.name}' reset")
        self.requests.clear()
