"""
Unit tests for infrastructure components.

Tests for Circuit Breaker, Rate Limiter, and API clients.
"""


import pytest

from app.domain.exceptions import CircuitBreakerOpenException, RateLimitExceededException
from app.infrastructure.circuit_breaker import CircuitBreaker, CircuitState
from app.infrastructure.rate_limiter import RateLimiter


class TestCircuitBreaker:
    """Tests for Circuit Breaker pattern."""

    @pytest.fixture
    def circuit_breaker(self):
        """Create a circuit breaker for testing."""
        return CircuitBreaker(failure_threshold=3, recovery_timeout=5, name="test_service")

    def test_initial_state_closed(self, circuit_breaker):
        """Test circuit breaker starts in CLOSED state."""
        assert circuit_breaker.state == CircuitState.CLOSED
        assert circuit_breaker.failure_count == 0

    def test_successful_call(self, circuit_breaker):
        """Test successful function call."""

        def success_func():
            return "success"

        result = circuit_breaker.call(success_func)
        assert result == "success"
        assert circuit_breaker.failure_count == 0

    def test_failed_call_increments_count(self, circuit_breaker):
        """Test failed call increments failure count."""

        def failing_func():
            raise Exception("API Error")

        with pytest.raises(Exception):
            circuit_breaker.call(failing_func)

        assert circuit_breaker.failure_count == 1

    def test_circuit_opens_after_threshold(self, circuit_breaker):
        """Test circuit opens after failure threshold."""

        def failing_func():
            raise Exception("API Error")

        # Fail threshold times
        for _ in range(3):
            with pytest.raises(Exception):
                circuit_breaker.call(failing_func)

        assert circuit_breaker.state == CircuitState.OPEN

        # Next call should raise CircuitBreakerOpenException
        with pytest.raises(CircuitBreakerOpenException):
            circuit_breaker.call(failing_func)

    def test_reset(self, circuit_breaker):
        """Test manual reset."""

        # Cause some failures
        def failing_func():
            raise Exception("Error")

        with pytest.raises(Exception):
            circuit_breaker.call(failing_func)

        circuit_breaker.reset()

        assert circuit_breaker.state == CircuitState.CLOSED
        assert circuit_breaker.failure_count == 0

    def test_get_status(self, circuit_breaker):
        """Test status retrieval."""
        status = circuit_breaker.get_status()

        assert status["name"] == "test_service"
        assert status["state"] == "closed"
        assert status["failure_count"] == 0


class TestRateLimiter:
    """Tests for Rate Limiter."""

    @pytest.fixture
    def rate_limiter(self):
        """Create a rate limiter for testing."""
        return RateLimiter(max_requests=3, window_seconds=1, name="test_limiter")

    def test_allows_requests_within_limit(self, rate_limiter):
        """Test requests are allowed within limit."""
        # Should allow 3 requests
        rate_limiter.acquire()
        rate_limiter.acquire()
        rate_limiter.acquire()

        # 4th request should fail
        with pytest.raises(RateLimitExceededException):
            rate_limiter.acquire()

    def test_get_current_usage(self, rate_limiter):
        """Test usage statistics."""
        rate_limiter.acquire()
        rate_limiter.acquire()

        usage = rate_limiter.get_current_usage()

        assert usage["current_requests"] == 2
        assert usage["max_requests"] == 3
        assert usage["usage_percent"] == pytest.approx(66.67, rel=0.1)

    def test_reset(self, rate_limiter):
        """Test reset clears requests."""
        rate_limiter.acquire()
        rate_limiter.acquire()

        rate_limiter.reset()

        usage = rate_limiter.get_current_usage()
        assert usage["current_requests"] == 0


class TestYahooFinanceClient:
    """Tests for Yahoo Finance client."""

    # TODO: Implement tests with mocked yfinance
    # This would require mocking yf.Ticker responses

    def test_placeholder(self):
        """Placeholder test."""
        # Will be implemented with proper mocks
        pass
