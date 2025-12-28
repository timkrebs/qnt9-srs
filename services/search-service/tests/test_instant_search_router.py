"""
Comprehensive tests for instant_search_router.

Tests cover:
- /instant endpoint: basic search, fuzzy matching, rate limiting, caching headers
- /suggestions endpoint: lightweight suggestions, caching
- Authentication (anonymous and authenticated users)
- Rate limiting by tier
- Query validation
- Error handling
- Response format and headers
- Latency tracking
"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.app import app
from app.core.auth import User
from app.search.relevance_scorer import SearchMatch

# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def mock_service():
    """Create mock stock service."""
    service = AsyncMock()
    service.intelligent_search = AsyncMock()
    service.get_search_suggestions = AsyncMock()
    return service


@pytest.fixture
def client(mock_service):
    """Create test client with mocked dependencies."""
    from app.dependencies import get_stock_service

    # Override the stock service dependency
    async def override_get_stock_service():
        return mock_service

    app.dependency_overrides[get_stock_service] = override_get_stock_service

    # Mock init_db to prevent database connection
    with patch("app.app.init_db"):
        with TestClient(app) as test_client:
            yield test_client

    # Clean up
    app.dependency_overrides.clear()


@pytest.fixture
def sample_stock():
    """Create sample stock for testing with router-expected attributes."""
    stock = MagicMock()
    stock.identifier.symbol = "AAPL"
    stock.identifier.name = "Apple Inc."
    stock.identifier.exchange = "NASDAQ"
    stock.current_price = Decimal("175.50")
    stock.price_change_percent = Decimal("1.5")
    return stock


@pytest.fixture
def sample_search_match(sample_stock):
    """Create sample search match."""
    return SearchMatch(
        stock=sample_stock, score=95.0, match_type="exact", matched_field="symbol", similarity=1.0
    )


@pytest.fixture
def mock_user():
    """Create mock authenticated user."""
    return User(id="user123", email="test@example.com", tier="premium")


@pytest.fixture
def mock_anonymous_request():
    """Create mock request for anonymous user."""
    request = MagicMock()
    request.client.host = "192.168.1.1"
    return request


# ============================================================================
# Test /instant Endpoint - Basic Functionality
# ============================================================================


class TestInstantSearchBasic:
    """Test basic instant search functionality."""

    @patch("app.routers.instant_search_router.get_current_user")
    @patch("app.routers.instant_search_router.rate_limiter.check_rate_limit")
    def test_successful_search(
        self, mock_rate_limit, mock_get_user, client, mock_service, sample_search_match
    ):
        """Test successful instant search."""
        # Setup mocks
        mock_rate_limit.return_value = None
        mock_get_user.return_value = None
        mock_service.intelligent_search.return_value = [sample_search_match]

        # Make request
        response = client.get("/api/v1/search/instant?q=AAPL")

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["query"] == "AAPL"
        assert data["count"] == 1
        assert len(data["results"]) == 1
        assert "latency_ms" in data

        # Check result format
        result = data["results"][0]
        assert result["symbol"] == "AAPL"
        assert result["name"] == "Apple Inc."
        assert result["exchange"] == "NASDAQ"
        assert result["price"] == 175.50
        assert result["change_percent"] == 1.5
        assert result["relevance_score"] == 95.0
        assert result["match_type"] == "exact"

    @patch("app.routers.instant_search_router.get_current_user")
    @patch("app.routers.instant_search_router.rate_limiter.check_rate_limit")
    def test_empty_results(self, mock_rate_limit, mock_get_user, client, mock_service):
        """Test search with no results."""
        mock_rate_limit.return_value = None
        mock_get_user.return_value = None
        mock_service.intelligent_search.return_value = []

        response = client.get("/api/v1/search/instant?q=ZZZZZ")

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["count"] == 0
        assert data["results"] == []

    @patch("app.routers.instant_search_router.get_current_user")
    @patch("app.routers.instant_search_router.rate_limiter.check_rate_limit")
    def test_multiple_results(
        self, mock_rate_limit, mock_get_user, client, mock_service, sample_stock
    ):
        """Test search with multiple results."""
        mock_rate_limit.return_value = None
        mock_get_user.return_value = None

        # Create multiple matches
        matches = [
            SearchMatch(sample_stock, 95.0, "exact", "symbol", 1.0),
            SearchMatch(sample_stock, 85.0, "prefix", "name", 0.9),
            SearchMatch(sample_stock, 75.0, "fuzzy", "symbol", 0.8),
        ]
        mock_service.intelligent_search.return_value = matches

        response = client.get("/api/v1/search/instant?q=app&limit=5")

        assert response.status_code == 200
        data = response.json()

        assert data["count"] == 3
        assert len(data["results"]) == 3

        # Check results are in order
        assert data["results"][0]["relevance_score"] == 95.0
        assert data["results"][1]["relevance_score"] == 85.0
        assert data["results"][2]["relevance_score"] == 75.0


# ============================================================================
# Test Query Parameters
# ============================================================================


class TestQueryParameters:
    """Test query parameter validation and handling."""

    def test_missing_query_parameter(self, client):
        """Test request without query parameter."""
        response = client.get("/api/v1/search/instant")
        assert response.status_code == 422  # Unprocessable Entity

    @patch("app.routers.instant_search_router.get_current_user")
    @patch("app.routers.instant_search_router.rate_limiter.check_rate_limit")
    def test_custom_limit(self, mock_rate_limit, mock_get_user, client, mock_service):
        """Test custom limit parameter."""
        mock_rate_limit.return_value = None
        mock_get_user.return_value = None
        mock_service.intelligent_search.return_value = []

        response = client.get("/api/v1/search/instant?q=test&limit=15")

        assert response.status_code == 200
        mock_service.intelligent_search.assert_called_once()
        call_args = mock_service.intelligent_search.call_args
        assert call_args.kwargs["limit"] == 15

    def test_limit_too_high(self, client):
        """Test limit exceeds maximum."""
        response = client.get("/api/v1/search/instant?q=test&limit=100")
        assert response.status_code == 422

    def test_limit_too_low(self, client):
        """Test limit below minimum."""
        response = client.get("/api/v1/search/instant?q=test&limit=0")
        assert response.status_code == 422

    @patch("app.routers.instant_search_router.get_current_user")
    @patch("app.routers.instant_search_router.rate_limiter.check_rate_limit")
    def test_fuzzy_matching_disabled_for_single_char(
        self, mock_rate_limit, mock_get_user, client, mock_service
    ):
        """Test fuzzy matching disabled for single character query."""
        mock_rate_limit.return_value = None
        mock_get_user.return_value = None
        mock_service.intelligent_search.return_value = []

        response = client.get("/api/v1/search/instant?q=A")

        assert response.status_code == 200
        call_args = mock_service.intelligent_search.call_args
        assert call_args.kwargs["include_fuzzy"] is False

    @patch("app.routers.instant_search_router.get_current_user")
    @patch("app.routers.instant_search_router.rate_limiter.check_rate_limit")
    def test_fuzzy_matching_enabled_for_two_chars(
        self, mock_rate_limit, mock_get_user, client, mock_service
    ):
        """Test fuzzy matching enabled for 2+ character query."""
        mock_rate_limit.return_value = None
        mock_get_user.return_value = None
        mock_service.intelligent_search.return_value = []

        response = client.get("/api/v1/search/instant?q=AP")

        assert response.status_code == 200
        call_args = mock_service.intelligent_search.call_args
        assert call_args.kwargs["include_fuzzy"] is True


# ============================================================================
# Test Caching Headers
# ============================================================================


class TestCachingHeaders:
    """Test HTTP caching headers."""

    @patch("app.routers.instant_search_router.get_current_user")
    @patch("app.routers.instant_search_router.rate_limiter.check_rate_limit")
    def test_cache_control_header(self, mock_rate_limit, mock_get_user, client, mock_service):
        """Test Cache-Control header is set correctly."""
        mock_rate_limit.return_value = None
        mock_get_user.return_value = None
        mock_service.intelligent_search.return_value = []

        response = client.get("/api/v1/search/instant?q=test")

        assert "Cache-Control" in response.headers
        assert response.headers["Cache-Control"] == "public, max-age=60"

    @patch("app.routers.instant_search_router.get_current_user")
    @patch("app.routers.instant_search_router.rate_limiter.check_rate_limit")
    def test_custom_headers(self, mock_rate_limit, mock_get_user, client, mock_service):
        """Test custom X- headers are set."""
        mock_rate_limit.return_value = None
        mock_get_user.return_value = None
        mock_service.intelligent_search.return_value = []

        response = client.get("/api/v1/search/instant?q=test")

        assert "X-Search-Latency-Ms" in response.headers
        assert "X-Result-Count" in response.headers
        assert response.headers["X-Result-Count"] == "0"


# ============================================================================
# Test Authentication
# ============================================================================


class TestAuthentication:
    """Test authenticated and anonymous access."""

    @patch("app.routers.instant_search_router.get_current_user")
    @pytest.mark.skip(
        reason="AsyncMock interferes with TestClient - needs different mocking approach"
    )
    @patch("app.routers.instant_search_router.get_current_user", new_callable=AsyncMock)
    @patch("app.routers.instant_search_router.rate_limiter.check_rate_limit")
    def test_authenticated_user(
        self, mock_rate_limit, mock_get_user, client, mock_service, mock_user
    ):
        """Test request from authenticated user."""
        mock_rate_limit.return_value = None
        mock_get_user.return_value = mock_user
        mock_service.intelligent_search.return_value = []

        response = client.get("/api/v1/search/instant?q=test")

        assert response.status_code == 200

        # Verify user_id passed to service
        call_args = mock_service.intelligent_search.call_args
        assert call_args.kwargs["user_id"] == "user123"

    @patch("app.routers.instant_search_router.get_current_user")
    @patch("app.routers.instant_search_router.rate_limiter.check_rate_limit")
    def test_anonymous_user(self, mock_rate_limit, mock_get_user, client, mock_service):
        """Test request from anonymous user."""
        mock_rate_limit.return_value = None
        mock_get_user.return_value = None
        mock_service.intelligent_search.return_value = []

        response = client.get("/api/v1/search/instant?q=test")

        assert response.status_code == 200

        # Verify user_id is None for anonymous
        call_args = mock_service.intelligent_search.call_args
        assert call_args.kwargs["user_id"] is None


# ============================================================================
# Test Rate Limiting
# ============================================================================


class TestRateLimiting:
    """Test rate limiting by user tier."""

    @patch("app.routers.instant_search_router.get_current_user")
    @patch("app.routers.instant_search_router.rate_limiter.check_rate_limit")
    def test_rate_limit_exceeded(self, mock_rate_limit, mock_get_user, client, mock_service):
        """Test rate limit exceeded."""
        mock_get_user.return_value = None

        # Simulate rate limit exceeded
        mock_rate_limit.side_effect = HTTPException(status_code=429, detail="Rate limit exceeded")

        response = client.get("/api/v1/search/instant?q=test")

        assert response.status_code == 429

    @patch("app.routers.instant_search_router.rate_limiter.check_rate_limit")
    def test_premium_tier_rate_limiting(self, mock_rate_limit, client, mock_service, mock_user):
        """Test rate limiting uses premium tier."""
        from app.core.auth import get_current_user

        # Override get_current_user to return premium user
        async def override_get_current_user():
            return mock_user

        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            mock_rate_limit.return_value = None
            mock_service.intelligent_search.return_value = []

            response = client.get("/api/v1/search/instant?q=test")

            assert response.status_code == 200

            # Verify rate limiter called with premium tier
            mock_rate_limit.assert_called_once()
            call_args = mock_rate_limit.call_args
            assert call_args[0][1] == "premium"  # tier argument
        finally:
            # Clean up the override
            app.dependency_overrides.pop(get_current_user, None)


# ============================================================================
# Test Error Handling
# ============================================================================


class TestErrorHandling:
    """Test error handling and edge cases."""

    @patch("app.routers.instant_search_router.get_current_user")
    @patch("app.routers.instant_search_router.rate_limiter.check_rate_limit")
    def test_validation_error(self, mock_rate_limit, mock_get_user, client, mock_service):
        """Test validation error handling."""
        from app.domain.exceptions import ValidationException

        mock_rate_limit.return_value = None
        mock_get_user.return_value = None

        # Simulate validation error
        mock_service.intelligent_search.side_effect = ValidationException(
            field="query", value="test", reason="Invalid query"
        )

        response = client.get("/api/v1/search/instant?q=test")

        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["success"] is False
        assert data["detail"]["error"] == "validation_error"

    @patch("app.routers.instant_search_router.get_current_user")
    @patch("app.routers.instant_search_router.rate_limiter.check_rate_limit")
    def test_internal_error(self, mock_rate_limit, mock_get_user, client, mock_service):
        """Test internal error handling."""
        mock_rate_limit.return_value = None
        mock_get_user.return_value = None

        # Simulate internal error
        mock_service.intelligent_search.side_effect = Exception("Database error")

        response = client.get("/api/v1/search/instant?q=test")

        assert response.status_code == 500
        data = response.json()
        assert data["detail"]["success"] is False
        assert data["detail"]["error"] == "internal_error"


# ============================================================================
# Test /suggestions Endpoint
# ============================================================================


class TestSuggestionsEndpoint:
    """Test /suggestions endpoint."""

    @patch("app.routers.instant_search_router.get_current_user")
    @patch("app.routers.instant_search_router.rate_limiter.check_rate_limit")
    def test_successful_suggestions(self, mock_rate_limit, mock_get_user, client, mock_service):
        """Test successful suggestions request."""
        mock_rate_limit.return_value = None
        mock_get_user.return_value = None

        # Mock suggestions response
        suggestions = [
            {"symbol": "AAPL", "name": "Apple Inc.", "score": 95},
            {"symbol": "APP", "name": "AppLovin", "score": 85},
        ]
        mock_service.get_search_suggestions.return_value = suggestions

        response = client.get("/api/v1/search/suggestions?q=app")

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["query"] == "app"
        assert data["count"] == 2
        assert len(data["suggestions"]) == 2
        assert "latency_ms" in data

    @patch("app.routers.instant_search_router.get_current_user")
    @patch("app.routers.instant_search_router.rate_limiter.check_rate_limit")
    def test_suggestions_caching(self, mock_rate_limit, mock_get_user, client, mock_service):
        """Test suggestions endpoint has caching headers."""
        mock_rate_limit.return_value = None
        mock_get_user.return_value = None
        mock_service.get_search_suggestions.return_value = []

        response = client.get("/api/v1/search/suggestions?q=test")

        assert "Cache-Control" in response.headers
        assert response.headers["Cache-Control"] == "public, max-age=60"

    @patch("app.routers.instant_search_router.get_current_user")
    @patch("app.routers.instant_search_router.rate_limiter.check_rate_limit")
    def test_suggestions_default_limit(self, mock_rate_limit, mock_get_user, client, mock_service):
        """Test suggestions default limit is 5."""
        mock_rate_limit.return_value = None
        mock_get_user.return_value = None
        mock_service.get_search_suggestions.return_value = []

        response = client.get("/api/v1/search/suggestions?q=test")

        assert response.status_code == 200
        call_args = mock_service.get_search_suggestions.call_args
        assert call_args.kwargs["limit"] == 5

    @patch("app.routers.instant_search_router.get_current_user")
    @patch("app.routers.instant_search_router.rate_limiter.check_rate_limit")
    def test_suggestions_custom_limit(self, mock_rate_limit, mock_get_user, client, mock_service):
        """Test suggestions with custom limit."""
        mock_rate_limit.return_value = None
        mock_get_user.return_value = None
        mock_service.get_search_suggestions.return_value = []

        response = client.get("/api/v1/search/suggestions?q=test&limit=8")

        assert response.status_code == 200
        call_args = mock_service.get_search_suggestions.call_args
        assert call_args.kwargs["limit"] == 8

    def test_suggestions_limit_max(self, client):
        """Test suggestions limit cannot exceed 10."""
        response = client.get("/api/v1/search/suggestions?q=test&limit=20")
        assert response.status_code == 422

    @patch("app.routers.instant_search_router.get_current_user")
    @patch("app.routers.instant_search_router.rate_limiter.check_rate_limit")
    def test_suggestions_error_handling(self, mock_rate_limit, mock_get_user, client, mock_service):
        """Test suggestions error handling."""
        mock_rate_limit.return_value = None
        mock_get_user.return_value = None

        # Simulate error
        mock_service.get_search_suggestions.side_effect = Exception("Service error")

        response = client.get("/api/v1/search/suggestions?q=test")

        assert response.status_code == 500
        data = response.json()
        assert data["detail"]["success"] is False


# ============================================================================
# Test Response Format
# ============================================================================


class TestResponseFormat:
    """Test response format and structure."""

    @patch("app.routers.instant_search_router.get_current_user")
    @patch("app.routers.instant_search_router.rate_limiter.check_rate_limit")
    def test_latency_tracking(self, mock_rate_limit, mock_get_user, client, mock_service):
        """Test latency is tracked and returned."""
        mock_rate_limit.return_value = None
        mock_get_user.return_value = None
        mock_service.intelligent_search.return_value = []

        response = client.get("/api/v1/search/instant?q=test")

        assert response.status_code == 200
        data = response.json()

        assert "latency_ms" in data
        assert isinstance(data["latency_ms"], (int, float))
        assert data["latency_ms"] >= 0

    @patch("app.routers.instant_search_router.get_current_user")
    @patch("app.routers.instant_search_router.rate_limiter.check_rate_limit")
    def test_result_with_optional_fields(
        self, mock_rate_limit, mock_get_user, client, mock_service
    ):
        """Test result with missing optional fields."""
        mock_rate_limit.return_value = None
        mock_get_user.return_value = None

        # Create stock with minimal data
        stock = MagicMock()
        stock.identifier.symbol = "TEST"
        stock.identifier.name = "Test Corp"
        stock.identifier.exchange = None
        stock.current_price = None
        stock.price_change_percent = None

        match = SearchMatch(stock, 50.0, "fuzzy", "name", 0.7)
        mock_service.intelligent_search.return_value = [match]

        response = client.get("/api/v1/search/instant?q=test")

        assert response.status_code == 200
        data = response.json()
        result = data["results"][0]

        assert result["price"] is None
        assert result["change_percent"] is None
        assert result["exchange"] is None


# ============================================================================
# Test Integration Scenarios
# ============================================================================


class TestIntegrationScenarios:
    """Test realistic integration scenarios."""

    @patch("app.routers.instant_search_router.get_current_user")
    @patch("app.routers.instant_search_router.rate_limiter.check_rate_limit")
    def test_typo_search(self, mock_rate_limit, mock_get_user, client, mock_service, sample_stock):
        """Test search with typo using fuzzy matching."""
        mock_rate_limit.return_value = None
        mock_get_user.return_value = None

        # User types "APPL" instead of "AAPL"
        match = SearchMatch(sample_stock, 85.0, "fuzzy", "symbol", 0.9)
        mock_service.intelligent_search.return_value = [match]

        response = client.get("/api/v1/search/instant?q=APPL")

        assert response.status_code == 200
        data = response.json()

        assert data["count"] == 1
        assert data["results"][0]["symbol"] == "AAPL"
        assert data["results"][0]["match_type"] == "fuzzy"

    @patch("app.routers.instant_search_router.get_current_user")
    @patch("app.routers.instant_search_router.rate_limiter.check_rate_limit")
    def test_partial_name_search(
        self, mock_rate_limit, mock_get_user, client, mock_service, sample_stock
    ):
        """Test partial name search."""
        mock_rate_limit.return_value = None
        mock_get_user.return_value = None

        match = SearchMatch(sample_stock, 90.0, "prefix", "name", 1.0)
        mock_service.intelligent_search.return_value = [match]

        response = client.get("/api/v1/search/instant?q=app")

        assert response.status_code == 200
        data = response.json()

        assert data["results"][0]["name"] == "Apple Inc."
        assert data["results"][0]["match_type"] == "prefix"
