"""
Circuit breaker implementation for fault tolerance.

Prevents cascading failures by temporarily blocking requests to failing services.
Includes Prometheus metrics for observability.
"""

import logging
from datetime import datetime
from enum import Enum
from typing import Callable, Optional

from prometheus_client import Counter, Gauge

from ..domain.exceptions import CircuitBreakerOpenException

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Blocking requests after failures
    HALF_OPEN = "half_open"  # Testing if service recovered


# Prometheus metrics for circuit breaker monitoring
circuit_breaker_state = Gauge(
    "circuit_breaker_state",
    "Current state of circuit breaker (0=closed, 1=open, 2=half_open)",
    ["name"],
)

circuit_breaker_failures = Counter(
    "circuit_breaker_failures_total",
    "Total number of failures tracked by circuit breaker",
    ["name"],
)

circuit_breaker_successes = Counter(
    "circuit_breaker_successes_total",
    "Total number of successful calls through circuit breaker",
    ["name"],
)

circuit_breaker_state_changes = Counter(
    "circuit_breaker_state_changes_total",
    "Total number of state changes",
    ["name", "from_state", "to_state"],
)


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

        # Initialize metrics
        self._update_state_metric()

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
                old_state = self.state
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
                self._update_state_metric()
                circuit_breaker_state_changes.labels(
                    name=self.name, from_state=old_state.value, to_state=self.state.value
                ).inc()
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
        circuit_breaker_successes.labels(name=self.name).inc()

        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            logger.info(
                f"Circuit breaker '{self.name}' HALF_OPEN success "
                f"({self.success_count}/{self.half_open_max_calls})"
            )

            if self.success_count >= self.half_open_max_calls:
                logger.info(f"Circuit breaker '{self.name}' closing after recovery")
                old_state = self.state
                self.state = CircuitState.CLOSED
                self.opened_at = None
                self._update_state_metric()
                circuit_breaker_state_changes.labels(
                    name=self.name, from_state=old_state.value, to_state=self.state.value
                ).inc()

    def _on_failure(self):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        circuit_breaker_failures.labels(name=self.name).inc()

        logger.warning(
            f"Circuit breaker '{self.name}' failure "
            f"({self.failure_count}/{self.failure_threshold})"
        )

        if self.state == CircuitState.HALF_OPEN:
            # Failed during recovery - back to OPEN
            logger.warning(f"Circuit breaker '{self.name}' failed during recovery, reopening")
            old_state = self.state
            self.state = CircuitState.OPEN
            self.opened_at = datetime.now()
            self._update_state_metric()
            circuit_breaker_state_changes.labels(
                name=self.name, from_state=old_state.value, to_state=self.state.value
            ).inc()
        elif self.failure_count >= self.failure_threshold:
            # Too many failures - OPEN the circuit
            logger.error(
                f"Circuit breaker '{self.name}' OPENING after " f"{self.failure_count} failures"
            )
            old_state = self.state
            self.state = CircuitState.OPEN
            self.opened_at = datetime.now()
            self._update_state_metric()
            circuit_breaker_state_changes.labels(
                name=self.name, from_state=old_state.value, to_state=self.state.value
            ).inc()

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
        old_state = self.state
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.opened_at = None
        self._update_state_metric()
        if old_state != CircuitState.CLOSED:
            circuit_breaker_state_changes.labels(
                name=self.name, from_state=old_state.value, to_state=self.state.value
            ).inc()

    def _update_state_metric(self):
        """Update Prometheus metric for current state."""
        state_value = {
            CircuitState.CLOSED: 0,
            CircuitState.OPEN: 1,
            CircuitState.HALF_OPEN: 2,
        }
        circuit_breaker_state.labels(name=self.name).set(state_value[self.state])

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
