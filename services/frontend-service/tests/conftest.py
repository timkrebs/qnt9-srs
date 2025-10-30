"""
Frontend Service Tests - Test Configuration
Fixtures and configuration for pytest
"""

import os

import pytest


@pytest.fixture(scope="session")
def test_settings():
    """Override settings for testing"""
    os.environ["SEARCH_SERVICE_URL"] = "http://test-search-service:8000"
    os.environ["DEBUG"] = "true"
    os.environ["HOST"] = "127.0.0.1"
    os.environ["PORT"] = "8001"


@pytest.fixture
def mock_stock_data():
    """Sample stock data for testing"""
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
def mock_search_result(mock_stock_data):
    """Sample successful search result"""
    return {
        "success": True,
        "data": mock_stock_data,
        "query_type": "isin",
        "response_time_ms": 150,
        "cached": False,
    }


@pytest.fixture
def mock_error_result():
    """Sample error result"""
    return {
        "success": False,
        "message": "Stock not found",
        "detail": "Invalid identifier",
    }


@pytest.fixture
def mock_suggestions():
    """Sample autocomplete suggestions"""
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


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line("markers", "asyncio: mark test as async")
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "unit: mark test as unit test")
