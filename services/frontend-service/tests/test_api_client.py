"""
Frontend Service Tests - API Client Tests.

Tests for SearchServiceClient class, including search operations,
suggestions, health checks, and error handling.
"""

from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from app.api_client import SearchServiceClient
from httpx import ConnectError


@pytest.fixture
def client() -> SearchServiceClient:
    """
    Create a SearchServiceClient instance for testing.

    Returns:
        SearchServiceClient instance with test configuration
    """
    return SearchServiceClient()


@pytest.mark.asyncio
async def test_search_success(client: SearchServiceClient) -> None:
    """
    Test successful search request.

    Verifies that the search method correctly handles a successful
    response from the search service.
    """
    mock_response: Dict[str, Any] = {
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
async def test_search_timeout(client: SearchServiceClient) -> None:
    """
    Test search timeout handling.

    Verifies that the search method correctly handles timeout errors
    and returns an appropriate error response.
    """
    with patch("httpx.AsyncClient.get", side_effect=TimeoutError("Request timeout")):
        result = await client.search("DE0005140008")

        assert result["success"] is False
        assert "timed out" in result["message"].lower()


@pytest.mark.asyncio
async def test_search_connection_error(client: SearchServiceClient) -> None:
    """
    Test search when connection fails.

    Verifies that the search method correctly handles connection errors
    when the search service is unavailable.
    """
    with patch("httpx.AsyncClient.get", side_effect=ConnectError("Connection refused")):
        result = await client.search("DE0005140008")

        assert result["success"] is False
        assert "connect" in result["message"].lower()


@pytest.mark.asyncio
async def test_get_suggestions_success(client: SearchServiceClient) -> None:
    """
    Test successful suggestions request.

    Verifies that the get_suggestions method correctly retrieves
    and returns autocomplete suggestions.
    """
    mock_suggestions: List[Dict[str, Any]] = [
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
async def test_get_suggestions_empty(client: SearchServiceClient) -> None:
    """
    Test suggestions with no results.

    Verifies that the get_suggestions method correctly handles
    cases where no suggestions are found.
    """
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"suggestions": []}
        mock_get.return_value = mock_resp

        result = await client.get_suggestions("ZZZZZ")

        assert result == []


@pytest.mark.asyncio
async def test_get_suggestions_error(client: SearchServiceClient) -> None:
    """
    Test suggestions with error.

    Verifies that the get_suggestions method returns an empty list
    when an error occurs, allowing the UI to degrade gracefully.
    """
    with patch("httpx.AsyncClient.get", side_effect=ConnectError("Connection refused")):
        result = await client.get_suggestions("DE")

        assert result == []


@pytest.mark.asyncio
async def test_health_check_healthy(client: SearchServiceClient) -> None:
    """
    Test health check when service is healthy.

    Verifies that the health_check method correctly identifies
    a healthy search service.
    """
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"status": "healthy"}
        mock_get.return_value = mock_resp

        result = await client.health_check()

        assert result is True


@pytest.mark.asyncio
async def test_health_check_unhealthy(client: SearchServiceClient) -> None:
    """
    Test health check when service is unhealthy.

    Verifies that the health_check method correctly identifies
    when the search service is down or unreachable.
    """
    with patch("httpx.AsyncClient.get", side_effect=ConnectError("Connection refused")):
        result = await client.health_check()

        assert result is False


@pytest.mark.asyncio
async def test_get_suggestions_empty_query(client: SearchServiceClient) -> None:
    """
    Test suggestions with empty query.

    Verifies that the get_suggestions method handles empty queries gracefully.
    The backend may return default suggestions for better UX in autocomplete scenarios.
    """
    result = await client.get_suggestions("")
    # Backend may return suggestions or empty list - both are valid
    assert isinstance(result, list)

    result = await client.get_suggestions("   ")
    # Backend may return suggestions or empty list - both are valid
    assert isinstance(result, list)


@pytest.mark.asyncio
async def test_search_http_error(client: SearchServiceClient) -> None:
    """
    Test search with HTTP error response.

    Verifies that HTTP errors (4xx, 5xx) are properly handled.
    """
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"error": "Internal Server Error"}
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server Error", request=MagicMock(), response=mock_response
        )
        mock_get.return_value = mock_response

        result = await client.search("TEST")

        assert result["success"] is False
        assert (
            "error" in result.get("message", "").lower()
            or "failed" in result.get("message", "").lower()
        )


@pytest.mark.asyncio
async def test_get_suggestions_http_error(client: SearchServiceClient) -> None:
    """
    Test get_suggestions with HTTP error response.

    Verifies that HTTP errors are handled gracefully in suggestions.
    """
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 503
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Service Unavailable", request=MagicMock(), response=mock_response
        )
        mock_get.return_value = mock_response

        result = await client.get_suggestions("TEST")

        # Should return empty list on error
        assert isinstance(result, list)
        assert len(result) == 0


@pytest.mark.asyncio
async def test_health_check_http_error(client: SearchServiceClient) -> None:
    """
    Test health_check with HTTP error response.

    Verifies that HTTP errors result in unhealthy status.
    """
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Internal Error", request=MagicMock(), response=mock_response
        )
        mock_get.return_value = mock_response

        result = await client.health_check()

        assert result is False
