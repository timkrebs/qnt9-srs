"""
Frontend Service Tests - API Client Tests
Tests for SearchServiceClient
"""

from unittest.mock import MagicMock, patch

import pytest
from httpx import ConnectError

from app.api_client import SearchServiceClient


@pytest.fixture
def client():
    """Create a SearchServiceClient instance"""
    return SearchServiceClient()


@pytest.mark.asyncio
async def test_search_success(client):
    """Test successful search request"""
    mock_response = {
        "success": True,
        "data": {
            "isin": "DE0005140008",
            "name": "Deutsche Bank AG",
            "symbol": "DBK.DE",
            "current_price": 12.50,
        },
        "query_type": "isin",
        "response_time_ms": 100,
    }

    with patch("httpx.AsyncClient.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_response
        mock_get.return_value = mock_resp

        result = await client.search("DE0005140008")

        assert result["success"] is True
        assert result["data"]["isin"] == "DE0005140008"


@pytest.mark.asyncio
async def test_search_timeout(client):
    """Test search timeout handling"""
    with patch("httpx.AsyncClient.get", side_effect=TimeoutError("Request timeout")):
        result = await client.search("DE0005140008")

        assert result["success"] is False
        assert "timed out" in result["message"].lower()


@pytest.mark.asyncio
async def test_search_connection_error(client):
    """Test search when connection fails"""
    with patch("httpx.AsyncClient.get", side_effect=ConnectError("Connection refused")):
        result = await client.search("DE0005140008")

        assert result["success"] is False


@pytest.mark.asyncio
async def test_get_suggestions_success(client):
    """Test successful suggestions request"""
    mock_suggestions = [
        {"query": "DE0005140008", "result_found": True, "search_count": 5},
        {"query": "DBK.DE", "result_found": True, "search_count": 3},
    ]

    with patch("httpx.AsyncClient.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"suggestions": mock_suggestions}
        mock_get.return_value = mock_resp

        result = await client.get_suggestions("DE", limit=5)

        assert len(result) == 2
        assert result[0]["query"] == "DE0005140008"


@pytest.mark.asyncio
async def test_get_suggestions_empty(client):
    """Test suggestions with no results"""
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"suggestions": []}
        mock_get.return_value = mock_resp

        result = await client.get_suggestions("ZZZZZ")

        assert result == []


@pytest.mark.asyncio
async def test_get_suggestions_error(client):
    """Test suggestions with error"""
    with patch("httpx.AsyncClient.get", side_effect=ConnectError("Connection refused")):
        result = await client.get_suggestions("DE")

        assert result == []


@pytest.mark.asyncio
async def test_health_check_healthy(client):
    """Test health check when service is healthy"""
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"status": "healthy"}
        mock_get.return_value = mock_resp

        result = await client.health_check()

        assert result is True


@pytest.mark.asyncio
async def test_health_check_unhealthy(client):
    """Test health check when service is unhealthy"""
    with patch("httpx.AsyncClient.get", side_effect=ConnectError("Connection refused")):
        result = await client.health_check()

        assert result is False
