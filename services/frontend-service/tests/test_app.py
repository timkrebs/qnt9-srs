"""
Frontend Service Tests - Main Application Tests.

Tests for FastAPI endpoints including homepage, search, suggestions,
health check, and template rendering.
"""

from typing import Any, Dict
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.app import app


@pytest.mark.asyncio
async def test_homepage() -> None:
    """
    Test homepage renders correctly.

    Verifies that the homepage loads successfully and contains
    expected content elements.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "QNT9" in response.text
        assert "Stock Search" in response.text


@pytest.mark.asyncio
async def test_health_check_healthy() -> None:
    """
    Test health check when search service is available.

    Verifies that the health endpoint reports healthy status
    when all dependencies are available.
    """
    with patch(
        "app.api_client.search_client.health_check",
        new_callable=AsyncMock,
    ) as mock_health:
        mock_health.return_value = True

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["service"] == "frontend-service"
            assert data["dependencies"]["search_service"] == "healthy"


@pytest.mark.asyncio
async def test_health_check_unhealthy() -> None:
    """
    Test health check when search service is unavailable.

    Verifies that the health endpoint reports degraded status
    when dependencies are unavailable.
    """
    with patch(
        "app.api_client.search_client.health_check",
        new_callable=AsyncMock,
    ) as mock_health:
        mock_health.return_value = False

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "degraded"
            assert data["dependencies"]["search_service"] == "unhealthy"


@pytest.mark.asyncio
async def test_search_stock_success() -> None:
    """
    Test successful stock search.

    Verifies that a successful search returns a properly rendered
    stock card with all expected information.
    """
    mock_result: Dict[str, Any] = {
        "success": True,
        "data": {
            "isin": "DE0005140008",
            "wkn": "514000",
            "name": "Deutsche Bank AG",
            "symbol": "DBK.DE",
            "current_price": 12.50,
            "currency": "EUR",
            "exchange": "XETRA",
            "country": "Germany",
        },
        "response_time_ms": 150,
        "query_type": "isin",
    }

    with patch(
        "app.api_client.search_client.search",
        new_callable=AsyncMock,
    ) as mock_search:
        mock_search.return_value = mock_result

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/search?query=DE0005140008")

            assert response.status_code == 200
            assert "Deutsche Bank" in response.text
            assert "DE0005140008" in response.text


@pytest.mark.asyncio
async def test_search_stock_not_found() -> None:
    """
    Test stock search when stock is not found.

    Verifies that failed searches return an appropriate error message
    to the user.
    """
    mock_result: Dict[str, Any] = {
        "success": False,
        "message": "Stock not found",
        "detail": "Invalid ISIN",
    }

    with patch(
        "app.api_client.search_client.search",
        new_callable=AsyncMock,
    ) as mock_search:
        mock_search.return_value = mock_result

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/search?query=INVALID123")

            assert response.status_code == 200
            assert "Stock Not Found" in response.text or "Error" in response.text


@pytest.mark.asyncio
async def test_search_validation_error() -> None:
    """
    Test search with invalid query (too short).

    Verifies that the API validates input and returns
    appropriate error codes for invalid requests.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/search?query=")

        assert response.status_code == 422


@pytest.mark.asyncio
async def test_suggestions_endpoint() -> None:
    """
    Test autocomplete suggestions endpoint.

    Verifies that the suggestions endpoint returns properly
    formatted HTML with suggestion data.
    """
    mock_suggestions = [
        {"query": "DE0005140008", "result_found": True, "search_count": 5},
        {"query": "DBK.DE", "result_found": True, "search_count": 3},
    ]

    with patch(
        "app.api_client.search_client.get_suggestions",
        new_callable=AsyncMock,
    ) as mock_suggestions_call:
        mock_suggestions_call.return_value = mock_suggestions

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/suggestions?query=DE")

            assert response.status_code == 200
            assert (
                "DE0005140008" in response.text or "suggestion" in response.text.lower()
            )


@pytest.mark.asyncio
async def test_suggestions_empty() -> None:
    """
    Test suggestions endpoint with no results.

    Verifies that the endpoint handles empty suggestion lists
    gracefully.
    """
    with patch(
        "app.api_client.search_client.get_suggestions",
        new_callable=AsyncMock,
    ) as mock_suggestions_call:
        mock_suggestions_call.return_value = []

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/suggestions?query=ZZZZZ")

            assert response.status_code == 200


@pytest.mark.asyncio
async def test_about_page() -> None:
    """
    Test about page renders correctly.

    Verifies that the about page loads successfully and contains
    expected content.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/about")

        assert response.status_code == 200
        assert "About" in response.text
        assert "QNT9" in response.text


@pytest.mark.asyncio
async def test_static_files() -> None:
    """
    Test static files are accessible.

    Verifies that CSS and JavaScript static files can be
    served correctly.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Test CSS
        response = await client.get("/static/css/styles.css")
        assert response.status_code == 200
        assert "text/css" in response.headers["content-type"]

        # Test JS
        response = await client.get("/static/js/main.js")
        assert response.status_code == 200
        assert "javascript" in response.headers["content-type"]


@pytest.mark.asyncio
async def test_search_without_query() -> None:
    """
    Test search endpoint without query parameter.

    Verifies that the API requires the query parameter
    and returns validation error when missing.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/search")

        assert response.status_code == 422


@pytest.mark.asyncio
async def test_htmx_headers() -> None:
    """
    Test that responses work with HTMX headers.

    Verifies that the application correctly handles HTMX requests
    and returns HTML partials instead of full pages.
    """
    mock_result: Dict[str, Any] = {
        "success": True,
        "data": {"symbol": "TEST", "name": "Test Stock"},
    }

    with patch(
        "app.api_client.search_client.search",
        new_callable=AsyncMock,
    ) as mock_search:
        mock_search.return_value = mock_result

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Simulate HTMX request
            headers = {"HX-Request": "true", "HX-Target": "search-results"}
            response = await client.get("/search?query=TEST", headers=headers)

            assert response.status_code == 200
            # Response should be HTML partial, not full page
            assert "<!DOCTYPE html>" not in response.text


@pytest.mark.asyncio
async def test_timestamp_to_date_filter() -> None:
    """
    Test timestamp_to_date Jinja2 filter.

    Verifies that Unix timestamps are correctly converted to readable dates.
    """
    from app.app import timestamp_to_date

    # Valid timestamp (November 3, 2025)
    result = timestamp_to_date(1730636400)
    assert result != ""
    assert "Nov" in result or "2025" in result

    # Empty/zero timestamp
    result = timestamp_to_date(0)
    assert result == ""

    # None/invalid timestamp
    result = timestamp_to_date(None)
    assert result == ""


@pytest.mark.asyncio
async def test_timestamp_to_date_filter_invalid() -> None:
    """
    Test timestamp_to_date filter with invalid values.

    Verifies graceful handling of invalid timestamps.
    """
    from app.app import timestamp_to_date

    # Very large invalid timestamp (causes OSError on some systems)
    result = timestamp_to_date(9999999999999)
    # Some systems may handle this, just verify it returns a string
    assert isinstance(result, str)

    # None timestamp
    result = timestamp_to_date(None)
    assert result == ""


@pytest.mark.asyncio
async def test_search_with_details_in_error() -> None:
    """
    Test search error response with details.

    Verifies that error details are properly rendered in the error template.
    """
    mock_result: Dict[str, Any] = {
        "success": False,
        "message": "Stock not found",
        "detail": "The ISIN you entered does not exist in our database",
    }

    with patch(
        "app.api_client.search_client.search",
        new_callable=AsyncMock,
    ) as mock_search:
        mock_search.return_value = mock_result

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/search?query=INVALID123")

            assert response.status_code == 200
            assert "Stock Not Found" in response.text
            assert "does not exist" in response.text


@pytest.mark.asyncio
async def test_suggestions_with_results() -> None:
    """
    Test suggestions endpoint with multiple results.

    Verifies that suggestions are properly formatted and rendered.
    """
    mock_suggestions = [
        {"query": "APPLE INC", "result_found": True},
        {"query": "AMAZON.COM", "result_found": True},
        {"query": "MICROSOFT CORP", "result_found": False},
    ]

    with patch(
        "app.api_client.search_client.get_suggestions",
        new_callable=AsyncMock,
    ) as mock_get_suggestions:
        mock_get_suggestions.return_value = mock_suggestions

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/suggestions?query=A")

            assert response.status_code == 200
            assert "APPLE INC" in response.text
            assert "AMAZON.COM" in response.text
            assert "MICROSOFT CORP" in response.text
            assert (
                "Recent search" in response.text
            )  # Should appear for result_found=True


@pytest.mark.asyncio
async def test_get_search_suggestions_helper() -> None:
    """
    Test _get_search_suggestions helper function.

    Verifies that default suggestions are returned for error messages.
    """
    from app.app import _get_search_suggestions

    suggestions = _get_search_suggestions()

    assert isinstance(suggestions, list)
    assert len(suggestions) > 0
    assert any("ISIN" in s or "WKN" in s or "Symbol" in s for s in suggestions)
