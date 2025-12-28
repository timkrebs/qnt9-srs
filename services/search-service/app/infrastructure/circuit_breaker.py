"""
Circuit breaker implementation for fault tolerance.

Prevents cascading failures by temporarily blocking requests to failing services.
"""

import logging
from datetime import datetime
from enum import Enum
from typing import Callable, Optional

from ..domain.exceptions import CircuitBreakerOpenException

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Blocking requests after failures
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """
    Circuit breaker pattern implementation.

    Protects external service calls from cascading failures:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Too many failures, block all requests
    - HALF_OPEN: Testing recovery, allow limited requests
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        half_open_max_calls: int = 3,
        name: str = "default",
    ):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery
            half_open_max_calls: Max calls allowed in half-open state
            name: Circuit breaker name for logging
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.opened_at: Optional[datetime] = None

    def call(self, func: Callable, *args, **kwargs):
        """
        Execute function through circuit breaker.

        Args:
            func: Function to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Result of func execution

        Raises:
            CircuitBreakerOpenException: If circuit is open
            Exception: Any exception from func execution
        """
        if self.state == CircuitState.OPEN:
            if self._should_attempt_recovery():
                logger.info(f"Circuit breaker '{self.name}' entering HALF_OPEN state")
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
            else:
                retry_after = self._get_retry_after_seconds()
                logger.warning(
                    f"Circuit breaker '{self.name}' is OPEN, " f"retry after {retry_after}s"
                )
                raise CircuitBreakerOpenException(
                    service=self.name,
                    failure_count=self.failure_count,
                    retry_after=retry_after,
                )

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception:
            self._on_failure()
            raise

    def _on_success(self):
        """Handle successful call."""
        self.failure_count = 0

        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            logger.info(
                f"Circuit breaker '{self.name}' HALF_OPEN success "
                f"({self.success_count}/{self.half_open_max_calls})"
            )

            if self.success_count >= self.half_open_max_calls:
                logger.info(f"Circuit breaker '{self.name}' closing after recovery")
                self.state = CircuitState.CLOSED
                self.opened_at = None

    def _on_failure(self):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        logger.warning(
            f"Circuit breaker '{self.name}' failure "
            f"({self.failure_count}/{self.failure_threshold})"
        )

        if self.state == CircuitState.HALF_OPEN:
            # Failed during recovery - back to OPEN
            logger.warning(f"Circuit breaker '{self.name}' failed during recovery, reopening")
            self.state = CircuitState.OPEN
            self.opened_at = datetime.now()
        elif self.failure_count >= self.failure_threshold:
            # Too many failures - OPEN the circuit
            logger.error(
                f"Circuit breaker '{self.name}' OPENING after " f"{self.failure_count} failures"
            )
            self.state = CircuitState.OPEN
            self.opened_at = datetime.now()

    def _should_attempt_recovery(self) -> bool:
        """Check if enough time has passed to attempt recovery."""
        if not self.opened_at:
            return False

        elapsed = (datetime.now() - self.opened_at).total_seconds()
        return elapsed >= self.recovery_timeout

    def _get_retry_after_seconds(self) -> int:
        """Calculate remaining time until recovery attempt."""
        if not self.opened_at:
            return self.recovery_timeout

        elapsed = (datetime.now() - self.opened_at).total_seconds()
        remaining = max(0, int(self.recovery_timeout - elapsed))
        return remaining

    def reset(self):
        """Manually reset circuit breaker to CLOSED state."""
        logger.info(f"Circuit breaker '{self.name}' manually reset")
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.opened_at = None

    def get_status(self) -> dict:
        """Get current circuit breaker status."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "failure_threshold": self.failure_threshold,
            "opened_at": self.opened_at.isoformat() if self.opened_at else None,
            "retry_after_seconds": (
                self._get_retry_after_seconds() if self.state == CircuitState.OPEN else None
            ),
        }
