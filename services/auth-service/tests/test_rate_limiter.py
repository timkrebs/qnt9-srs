"""
Comprehensive tests for rate_limiter.py module.

Tests rate limiting functionality including configuration, blocking, and cleanup.
"""

import time
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException, Request

from app.rate_limiter import (
    ClientState,
    RateLimitConfig,
    RateLimiter,
    auth_rate_limiter,
    check_auth_rate_limit,
    check_password_reset_rate_limit,
    general_rate_limiter,
    password_reset_rate_limiter,
)


class TestRateLimitConfig:
    """Test RateLimitConfig dataclass."""

    def test_config_default_block_duration(self):
        """Test config with default block duration."""
        config = RateLimitConfig(max_requests=5, window_seconds=60)
        assert config.max_requests == 5
        assert config.window_seconds == 60
        assert config.block_duration_seconds == 0

    def test_config_with_block_duration(self):
        """Test config with custom block duration."""
        config = RateLimitConfig(
            max_requests=3,
            window_seconds=120,
            block_duration_seconds=300,
        )
        assert config.max_requests == 3
        assert config.window_seconds == 120
        assert config.block_duration_seconds == 300


class TestClientState:
    """Test ClientState dataclass."""

    def test_client_state_defaults(self):
        """Test client state default values."""
        state = ClientState()
        assert state.requests == []
        assert state.blocked_until == 0.0

    def test_client_state_with_requests(self):
        """Test client state with requests."""
        now = time.time()
        state = ClientState(requests=[now - 10, now - 5, now])
        assert len(state.requests) == 3

    def test_client_state_with_block(self):
        """Test client state with block."""
        future = time.time() + 300
        state = ClientState(blocked_until=future)
        assert state.blocked_until == future


class TestRateLimiter:
    """Test RateLimiter class."""

    @pytest.fixture
    def limiter(self):
        """Create a fresh rate limiter for testing."""
        return RateLimiter(RateLimitConfig(
            max_requests=3,
            window_seconds=60,
            block_duration_seconds=0,
        ))

    @pytest.fixture
    def blocking_limiter(self):
        """Create a rate limiter with blocking enabled."""
        return RateLimiter(RateLimitConfig(
            max_requests=2,
            window_seconds=60,
            block_duration_seconds=120,
        ))

    @pytest.fixture
    def mock_request(self):
        """Create a mock FastAPI request."""
        request = MagicMock(spec=Request)
        request.headers = {}
        request.client = MagicMock()
        request.client.host = "192.168.1.100"
        return request

    def test_limiter_allows_first_request(self, limiter, mock_request):
        """Test that first request is allowed."""
        is_allowed, retry_after = limiter.check_rate_limit(mock_request)
        assert is_allowed is True
        assert retry_after is None

    def test_limiter_allows_up_to_limit(self, limiter, mock_request):
        """Test requests are allowed up to the limit."""
        for i in range(3):
            is_allowed, retry_after = limiter.check_rate_limit(mock_request)
            assert is_allowed is True

    def test_limiter_blocks_after_limit(self, limiter, mock_request):
        """Test requests are blocked after exceeding limit."""
        # Make 3 requests (the limit)
        for _ in range(3):
            limiter.check_rate_limit(mock_request)

        # 4th request should be blocked
        is_allowed, retry_after = limiter.check_rate_limit(mock_request)
        assert is_allowed is False
        assert retry_after is not None
        assert retry_after > 0

    def test_limiter_applies_block_duration(self, blocking_limiter, mock_request):
        """Test that block duration is applied."""
        # Exceed limit
        for _ in range(2):
            blocking_limiter.check_rate_limit(mock_request)

        # Next request should be blocked
        is_allowed, retry_after = blocking_limiter.check_rate_limit(mock_request)
        assert is_allowed is False
        assert retry_after == 120  # Block duration

    def test_limiter_extracts_forwarded_ip(self, limiter):
        """Test IP extraction from X-Forwarded-For header."""
        request = MagicMock(spec=Request)
        request.headers = {"X-Forwarded-For": "10.0.0.1, 192.168.1.1"}
        request.client = MagicMock()
        request.client.host = "127.0.0.1"

        ip = limiter._get_client_ip(request)
        assert ip == "10.0.0.1"

    def test_limiter_extracts_direct_ip(self, limiter, mock_request):
        """Test IP extraction from direct client."""
        ip = limiter._get_client_ip(mock_request)
        assert ip == "192.168.1.100"

    def test_limiter_handles_no_client(self, limiter):
        """Test IP extraction with no client."""
        request = MagicMock(spec=Request)
        request.headers = {}
        request.client = None

        ip = limiter._get_client_ip(request)
        assert ip == "unknown"

    def test_limiter_different_clients_independent(self, limiter):
        """Test that different IPs have independent limits."""
        request1 = MagicMock(spec=Request)
        request1.headers = {}
        request1.client = MagicMock()
        request1.client.host = "192.168.1.1"

        request2 = MagicMock(spec=Request)
        request2.headers = {}
        request2.client = MagicMock()
        request2.client.host = "192.168.1.2"

        # Client 1 makes requests
        for _ in range(3):
            limiter.check_rate_limit(request1)

        # Client 1 is now blocked
        is_allowed1, _ = limiter.check_rate_limit(request1)
        assert is_allowed1 is False

        # Client 2 should still be allowed
        is_allowed2, _ = limiter.check_rate_limit(request2)
        assert is_allowed2 is True

    def test_get_remaining_full(self, limiter, mock_request):
        """Test get_remaining with no requests made."""
        remaining = limiter.get_remaining(mock_request)
        assert remaining == 3

    def test_get_remaining_partial(self, limiter, mock_request):
        """Test get_remaining after some requests."""
        limiter.check_rate_limit(mock_request)
        limiter.check_rate_limit(mock_request)

        remaining = limiter.get_remaining(mock_request)
        assert remaining == 1

    def test_get_remaining_blocked(self, blocking_limiter, mock_request):
        """Test get_remaining when blocked returns 0."""
        # Exceed limit and trigger block
        for _ in range(3):
            blocking_limiter.check_rate_limit(mock_request)

        remaining = blocking_limiter.get_remaining(mock_request)
        assert remaining == 0


class TestPreConfiguredLimiters:
    """Test pre-configured rate limiters."""

    def test_auth_limiter_config(self):
        """Test auth rate limiter configuration."""
        assert auth_rate_limiter.config.max_requests == 5
        assert auth_rate_limiter.config.window_seconds == 60
        assert auth_rate_limiter.config.block_duration_seconds == 300

    def test_password_reset_limiter_config(self):
        """Test password reset rate limiter configuration."""
        assert password_reset_rate_limiter.config.max_requests == 3
        assert password_reset_rate_limiter.config.window_seconds == 3600
        assert password_reset_rate_limiter.config.block_duration_seconds == 0

    def test_general_limiter_config(self):
        """Test general rate limiter configuration."""
        assert general_rate_limiter.config.max_requests == 100
        assert general_rate_limiter.config.window_seconds == 60
        assert general_rate_limiter.config.block_duration_seconds == 0


class TestRateLimitDependencies:
    """Test FastAPI rate limit dependencies."""

    @pytest.fixture
    def mock_request(self):
        """Create a mock FastAPI request."""
        request = MagicMock(spec=Request)
        request.headers = {}
        request.client = MagicMock()
        request.client.host = "10.0.0.99"
        return request

    @pytest.fixture(autouse=True)
    def reset_limiters(self):
        """Reset limiters before each test."""
        auth_rate_limiter._clients.clear()
        password_reset_rate_limiter._clients.clear()
        yield
        auth_rate_limiter._clients.clear()
        password_reset_rate_limiter._clients.clear()

    def test_check_auth_rate_limit_allows(self, mock_request):
        """Test auth rate limit allows valid requests."""
        # Should not raise
        check_auth_rate_limit(mock_request)

    def test_check_auth_rate_limit_blocks(self, mock_request):
        """Test auth rate limit raises HTTPException when exceeded."""
        # Exceed limit
        for _ in range(5):
            check_auth_rate_limit(mock_request)

        # Should raise HTTPException
        with pytest.raises(HTTPException) as exc_info:
            check_auth_rate_limit(mock_request)

        assert exc_info.value.status_code == 429
        assert "Too many authentication attempts" in exc_info.value.detail

    def test_check_password_reset_rate_limit_allows(self, mock_request):
        """Test password reset rate limit allows valid requests."""
        # Should not raise
        check_password_reset_rate_limit(mock_request)

    def test_check_password_reset_rate_limit_blocks(self, mock_request):
        """Test password reset rate limit raises HTTPException when exceeded."""
        # Exceed limit
        for _ in range(3):
            check_password_reset_rate_limit(mock_request)

        # Should raise HTTPException
        with pytest.raises(HTTPException) as exc_info:
            check_password_reset_rate_limit(mock_request)

        assert exc_info.value.status_code == 429
        assert "Too many password reset" in exc_info.value.detail
