"""
Frontend Service Tests - Test Configuration.

Provides pytest fixtures and configuration for testing the frontend service.
Includes mock data fixtures and test environment setup.
"""

import os
from typing import Any, Dict, List

import pytest


@pytest.fixture(scope="session")
def test_settings() -> None:
    """
    Override settings for testing environment.

    Sets environment variables to ensure tests run with consistent
    configuration regardless of the host environment.
    """
    os.environ["SEARCH_SERVICE_URL"] = "http://test-search-service:8000"
    os.environ["DEBUG"] = "true"
    os.environ["HOST"] = "127.0.0.1"
    os.environ["PORT"] = "8001"
    os.environ["LOG_LEVEL"] = "DEBUG"


@pytest.fixture
def mock_stock_data() -> Dict[str, Any]:
    """
    Sample stock data for testing.

    Provides a complete stock data dictionary that matches the expected
    structure from the search service.

    Returns:
        Dictionary with sample stock information
    """
    return {
        "isin": "DE0005140008",
        "wkn": "514000",
        "name": "Deutsche Bank AG",
        "symbol": "DBK.DE",
        "current_price": 12.50,
        "currency": "EUR",
        "exchange": "XETRA",
        "country": "Germany",
        "sector": "Financial Services",
        "industry": "Banks",
        "market_cap": 25000000000,
        "pe_ratio": 8.5,
        "dividend_yield": 0.025,
        "volume": 5000000,
        "data_source": "Yahoo Finance",
        "cached": False,
    }


@pytest.fixture
def mock_search_result(mock_stock_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sample successful search result.

    Provides a complete search result dictionary including success status,
    stock data, and metadata.

    Args:
        mock_stock_data: Stock data fixture

    Returns:
        Dictionary with sample successful search result
    """
    return {
        "success": True,
        "data": mock_stock_data,
        "query_type": "isin",
        "response_time_ms": 150,
        "cached": False,
    }


@pytest.fixture
def mock_error_result() -> Dict[str, Any]:
    """
    Sample error result.

    Provides an error result dictionary for testing error handling.

    Returns:
        Dictionary with sample error response
    """
    return {
        "success": False,
        "message": "Stock not found",
        "detail": "Invalid identifier",
    }


@pytest.fixture
def mock_suggestions() -> List[Dict[str, Any]]:
    """
    Sample autocomplete suggestions.

    Provides a list of suggestion objects for testing autocomplete functionality.

    Returns:
        List of suggestion dictionaries
    """
    return [
        {
            "query": "DE0005140008",
            "result_found": True,
            "search_count": 5,
            "last_searched": "2025-01-20T10:30:00",
        },
        {
            "query": "DBK.DE",
            "result_found": True,
            "search_count": 3,
            "last_searched": "2025-01-20T09:15:00",
        },
        {
            "query": "514000",
            "result_found": True,
            "search_count": 2,
            "last_searched": "2025-01-19T14:20:00",
        },
    ]


def pytest_configure(config: Any) -> None:
    """
    Configure pytest with custom markers.

    Registers custom markers for categorizing tests.

    Args:
        config: Pytest configuration object
    """
    config.addinivalue_line(
        "markers",
        "asyncio: mark test as async",
    )
    config.addinivalue_line(
        "markers",
        "integration: mark test as integration test",
    )
    config.addinivalue_line(
        "markers",
        "unit: mark test as unit test",
    )
