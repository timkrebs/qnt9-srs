"""
Frontend Service Tests - Main Application Tests
Tests for FastAPI endpoints and template rendering
"""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.app import app


@pytest.mark.asyncio
async def test_homepage():
    """Test homepage renders correctly"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "QNT9" in response.text
        assert "Stock Search" in response.text


@pytest.mark.asyncio
async def test_health_check_healthy():
    """Test health check when search service is available"""
    with patch("app.api_client.search_client.health_check", new_callable=AsyncMock) as mock_health:
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
async def test_health_check_unhealthy():
    """Test health check when search service is unavailable"""
    with patch("app.api_client.search_client.health_check", new_callable=AsyncMock) as mock_health:
        mock_health.return_value = False

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["dependencies"]["search_service"] == "unhealthy"


@pytest.mark.asyncio
async def test_search_stock_success():
    """Test successful stock search"""
    mock_result = {
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

    with patch("app.api_client.search_client.search", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = mock_result

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/search?query=DE0005140008")
            assert response.status_code == 200
            assert "Deutsche Bank" in response.text
            assert "DE0005140008" in response.text


@pytest.mark.asyncio
async def test_search_stock_not_found():
    """Test stock search when stock is not found"""
    mock_result = {
        "success": False,
        "message": "Stock not found",
        "detail": "Invalid ISIN",
    }

    with patch("app.api_client.search_client.search", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = mock_result

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/search?query=INVALID123")
            assert response.status_code == 200
            assert "Stock Not Found" in response.text or "Error" in response.text


@pytest.mark.asyncio
async def test_search_validation_error():
    """Test search with invalid query (too short)"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/search?query=")
        assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_suggestions_endpoint():
    """Test autocomplete suggestions endpoint"""
    mock_suggestions = [
        {"query": "DE0005140008", "result_found": True, "search_count": 5},
        {"query": "DBK.DE", "result_found": True, "search_count": 3},
    ]

    with patch(
        "app.api_client.search_client.get_suggestions", new_callable=AsyncMock
    ) as mock_suggestions_call:
        mock_suggestions_call.return_value = mock_suggestions

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/suggestions?query=DE")
            assert response.status_code == 200
            assert "DE0005140008" in response.text or "suggestion" in response.text.lower()


@pytest.mark.asyncio
async def test_suggestions_empty():
    """Test suggestions endpoint with no results"""
    with patch(
        "app.api_client.search_client.get_suggestions", new_callable=AsyncMock
    ) as mock_suggestions_call:
        mock_suggestions_call.return_value = []

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/suggestions?query=ZZZZZ")
            assert response.status_code == 200


@pytest.mark.asyncio
async def test_about_page():
    """Test about page renders correctly"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/about")
        assert response.status_code == 200
        assert "About" in response.text
        assert "QNT9" in response.text


@pytest.mark.asyncio
async def test_static_files():
    """Test static files are accessible"""
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
async def test_search_without_query():
    """Test search endpoint without query parameter"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/search")
        assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_htmx_headers():
    """Test that responses work with HTMX headers"""
    mock_result = {"success": True, "data": {"symbol": "TEST", "name": "Test Stock"}}

    with patch("app.api_client.search_client.search", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = mock_result

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Simulate HTMX request
            headers = {"HX-Request": "true", "HX-Target": "search-results"}
            response = await client.get("/search?query=TEST", headers=headers)
            assert response.status_code == 200
            # Response should be HTML partial, not full page
            assert "<!DOCTYPE html>" not in response.text
