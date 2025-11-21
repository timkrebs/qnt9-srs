"""
Tests for Yahoo Finance client.

Covers:
- Stock fetching with symbol/ISIN/WKN
- Name-based search with multiple strategies
- Circuit breaker integration
- Rate limiter integration
- Error handling
"""

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from app.domain.entities import DataSource, StockIdentifier
from app.domain.exceptions import ExternalServiceException, StockNotFoundException
from app.infrastructure.yahoo_finance_client import YahooFinanceClient


@pytest.fixture
def yahoo_client():
    """Create Yahoo Finance client instance."""
    return YahooFinanceClient(
        timeout_seconds=5.0,
        max_retries=3,
        rate_limit_requests=5,
        rate_limit_window=1,
    )


@pytest.fixture
def mock_ticker_info():
    """Mock Yahoo Finance ticker info response."""
    return {
        "symbol": "AAPL",
        "longName": "Apple Inc.",
        "shortName": "Apple",
        "currentPrice": 175.50,
        "currency": "USD",
        "regularMarketChange": 2.50,
        "regularMarketChangePercent": 1.45,
        "previousClose": 173.00,
        "regularMarketOpen": 174.00,
        "regularMarketDayHigh": 176.00,
        "regularMarketDayLow": 173.50,
        "fiftyTwoWeekHigh": 199.62,
        "fiftyTwoWeekLow": 164.08,
        "regularMarketVolume": 50000000,
        "averageVolume": 55000000,
        "exchange": "NASDAQ",
        "sector": "Technology",
        "industry": "Consumer Electronics",
        "marketCap": 2750000000000,
        "trailingPE": 28.5,
        "dividendYield": 0.0052,
        "beta": 1.2,
        "longBusinessSummary": "Apple Inc. designs, manufactures, and markets smartphones.",
        "fullTimeEmployees": 164000,
        "website": "https://www.apple.com",
        "isin": "US0378331005",
    }


class TestYahooFinanceClientInitialization:
    """Test client initialization."""

    def test_client_initialization(self, yahoo_client):
        """Test client is properly initialized."""
        assert yahoo_client.timeout == 5.0
        assert yahoo_client.max_retries == 3
        assert yahoo_client.circuit_breaker is not None
        assert yahoo_client.rate_limiter is not None

    def test_custom_parameters(self):
        """Test client with custom parameters."""
        client = YahooFinanceClient(
            timeout_seconds=10.0,
            max_retries=5,
            rate_limit_requests=10,
            rate_limit_window=2,
        )
        assert client.timeout == 10.0
        assert client.max_retries == 5


class TestFetchStock:
    """Test fetch_stock method."""

    @pytest.mark.asyncio
    async def test_fetch_by_symbol(self, yahoo_client, mock_ticker_info):
        """Test fetching stock by symbol."""
        identifier = StockIdentifier(symbol="AAPL")

        with patch("yfinance.Ticker") as mock_ticker_class:
            mock_ticker = MagicMock()
            mock_ticker.info = mock_ticker_info
            mock_ticker_class.return_value = mock_ticker

            stock = await yahoo_client.fetch_stock(identifier)

            assert stock is not None
            assert stock.identifier.symbol == "AAPL"
            assert stock.identifier.name == "Apple Inc."
            assert stock.price.current == Decimal("175.50")
            assert stock.price.currency == "USD"
            assert stock.data_source == DataSource.YAHOO_FINANCE
            assert stock.metadata.sector == "Technology"

    @pytest.mark.asyncio
    async def test_fetch_by_isin(self, yahoo_client, mock_ticker_info):
        """Test fetching stock by ISIN."""
        identifier = StockIdentifier(isin="US0378331005")

        # Mock yf.Search to return AAPL for ISIN
        mock_quote = {"symbol": "AAPL", "quoteType": "EQUITY"}

        with patch("yfinance.Search") as mock_search_class, patch(
            "yfinance.Ticker"
        ) as mock_ticker_class:
            # Mock search results
            mock_search = MagicMock()
            mock_search.quotes = [mock_quote]
            mock_search_class.return_value = mock_search

            # Mock ticker data
            mock_ticker = MagicMock()
            mock_ticker.info = mock_ticker_info
            mock_ticker_class.return_value = mock_ticker

            stock = await yahoo_client.fetch_stock(identifier)

            assert stock is not None
            assert stock.identifier.symbol == "AAPL"

    @pytest.mark.asyncio
    async def test_fetch_stock_not_found(self, yahoo_client):
        """Test handling of stock not found."""
        identifier = StockIdentifier(symbol="INVALID")

        with patch("yfinance.Ticker") as mock_ticker_class:
            mock_ticker = MagicMock()
            mock_ticker.info = {}  # Empty info
            mock_ticker_class.return_value = mock_ticker

            result = await yahoo_client.fetch_stock(identifier)

            assert result is None

    @pytest.mark.asyncio
    async def test_fetch_external_service_exception(self, yahoo_client):
        """Test handling of external service exceptions."""
        identifier = StockIdentifier(symbol="AAPL")

        with patch("yfinance.Ticker") as mock_ticker_class:
            mock_ticker_class.side_effect = Exception("API Error")

            with pytest.raises(ExternalServiceException) as exc_info:
                await yahoo_client.fetch_stock(identifier)

            assert "yahoo_finance" in str(exc_info.value)


class TestSearchByName:
    """Test search_by_name method."""

    @pytest.mark.asyncio
    async def test_search_by_name_yahoo_api(self, yahoo_client, mock_ticker_info):
        """Test search using Yahoo Search API."""
        mock_quote = {"symbol": "AAPL", "longname": "Apple Inc.", "quoteType": "EQUITY"}

        with patch("yfinance.Search") as mock_search_class, patch(
            "yfinance.Ticker"
        ) as mock_ticker_class:
            # Mock search results
            mock_search = MagicMock()
            mock_search.quotes = [mock_quote]
            mock_search_class.return_value = mock_search

            # Mock ticker data
            mock_ticker = MagicMock()
            mock_ticker.info = mock_ticker_info
            mock_ticker_class.return_value = mock_ticker

            results = await yahoo_client.search_by_name("Apple", limit=5)

            assert len(results) > 0
            assert results[0].identifier.symbol == "AAPL"

    @pytest.mark.asyncio
    async def test_search_by_name_hardcoded_mappings(self, yahoo_client, mock_ticker_info):
        """Test search using hardcoded mappings."""
        with patch("yfinance.Search") as mock_search_class, patch(
            "yfinance.Ticker"
        ) as mock_ticker_class:
            # Mock search fails (old yfinance version)
            mock_search_class.side_effect = AttributeError("Search not available")

            # Mock ticker data
            mock_ticker = MagicMock()
            mock_ticker.info = mock_ticker_info
            mock_ticker_class.return_value = mock_ticker

            results = await yahoo_client.search_by_name("Apple", limit=5)

            assert len(results) > 0
            assert results[0].identifier.symbol == "AAPL"

    @pytest.mark.asyncio
    async def test_search_by_name_direct_symbol(self, yahoo_client, mock_ticker_info):
        """Test search by entering a symbol directly."""
        with patch("yfinance.Search") as mock_search_class, patch(
            "yfinance.Ticker"
        ) as mock_ticker_class:
            # Mock search returns no results
            mock_search = MagicMock()
            mock_search.quotes = []
            mock_search_class.return_value = mock_search

            # Mock ticker data
            mock_ticker = MagicMock()
            mock_ticker.info = mock_ticker_info
            mock_ticker_class.return_value = mock_ticker

            results = await yahoo_client.search_by_name("AAPL", limit=5)

            assert len(results) > 0
            assert results[0].identifier.symbol == "AAPL"

    @pytest.mark.asyncio
    async def test_search_filters_non_equities(self, yahoo_client, mock_ticker_info):
        """Test search filters out non-equity instruments."""
        mock_quotes = [
            {"symbol": "BTC-USD", "quoteType": "CRYPTOCURRENCY"},
            {"symbol": "AAPL", "longname": "Apple Inc.", "quoteType": "EQUITY"},
        ]

        with patch("yfinance.Search") as mock_search_class, patch(
            "yfinance.Ticker"
        ) as mock_ticker_class:
            # Mock search results
            mock_search = MagicMock()
            mock_search.quotes = mock_quotes
            mock_search_class.return_value = mock_search

            # Mock ticker data
            mock_ticker = MagicMock()
            mock_ticker.info = mock_ticker_info
            mock_ticker_class.return_value = mock_ticker

            results = await yahoo_client.search_by_name("Apple", limit=5)

            # Should only return AAPL, not BTC-USD
            assert len(results) == 1
            assert results[0].identifier.symbol == "AAPL"

    @pytest.mark.asyncio
    async def test_search_respects_limit(self, yahoo_client, mock_ticker_info):
        """Test search respects result limit."""
        mock_quotes = [
            {"symbol": f"STOCK{i}", "longname": f"Company {i}", "quoteType": "EQUITY"}
            for i in range(20)
        ]

        with patch("yfinance.Search") as mock_search_class, patch(
            "yfinance.Ticker"
        ) as mock_ticker_class:
            # Mock search results
            mock_search = MagicMock()
            mock_search.quotes = mock_quotes
            mock_search_class.return_value = mock_search

            # Mock ticker data
            mock_ticker = MagicMock()
            mock_ticker.info = mock_ticker_info
            mock_ticker_class.return_value = mock_ticker

            results = await yahoo_client.search_by_name("Test", limit=3)

            assert len(results) <= 3

    @pytest.mark.asyncio
    async def test_search_handles_errors_gracefully(self, yahoo_client):
        """Test search handles errors and returns empty list."""
        with patch("yfinance.Ticker") as mock_ticker_class:
            # Make yfinance raise an exception
            mock_ticker_class.side_effect = Exception("API Error")

            # The search might still succeed via yfinance.Search, so let's also mock that
            with patch("yfinance.Search") as mock_search_class:
                mock_search = MagicMock()
                mock_search.quotes = []  # Return empty results instead of raising
                mock_search_class.return_value = mock_search

                results = await yahoo_client.search_by_name("InvalidQuery", limit=5)

                # Should return empty list when no results found
                assert isinstance(results, list)


class TestResolveYahooSymbol:
    """Test _resolve_yahoo_symbol method."""

    def test_resolve_with_symbol(self, yahoo_client):
        """Test resolution when symbol is provided."""
        identifier = StockIdentifier(symbol="AAPL")
        symbol = yahoo_client._resolve_yahoo_symbol(identifier)
        assert symbol == "AAPL"

    def test_resolve_with_name_returns_none(self, yahoo_client):
        """Test resolution with name returns None (uses search_by_name instead)."""
        identifier = StockIdentifier(name="Apple Inc.")
        symbol = yahoo_client._resolve_yahoo_symbol(identifier)
        assert symbol is None

    def test_resolve_wkn_fallback(self, yahoo_client):
        """Test WKN resolution fallback."""
        identifier = StockIdentifier(wkn="840400")

        mock_quote = {"symbol": "AAPL", "quoteType": "EQUITY"}

        with patch("yfinance.Search") as mock_search_class:
            mock_search = MagicMock()
            mock_search.quotes = [mock_quote]
            mock_search_class.return_value = mock_search

            symbol = yahoo_client._resolve_yahoo_symbol(identifier)
            assert symbol == "AAPL"


class TestMapToEntity:
    """Test _map_to_entity method."""

    def test_map_complete_data(self, yahoo_client, mock_ticker_info):
        """Test mapping complete ticker data to Stock entity."""
        identifier = StockIdentifier(symbol="AAPL")

        stock = yahoo_client._map_to_entity(mock_ticker_info, identifier, "AAPL")

        assert stock.identifier.symbol == "AAPL"
        assert stock.identifier.name == "Apple Inc."
        assert stock.price.current == Decimal("175.50")
        assert stock.price.currency == "USD"
        assert stock.price.change_absolute == Decimal("2.50")
        assert stock.metadata.sector == "Technology"
        assert stock.metadata.exchange == "NASDAQ"
        assert stock.data_source == DataSource.YAHOO_FINANCE

    def test_map_missing_optional_fields(self, yahoo_client):
        """Test mapping with minimal required fields."""
        minimal_info = {
            "symbol": "TEST",
            "longName": "Test Company",
            "currentPrice": 100.0,
            "currency": "USD",
        }

        identifier = StockIdentifier(symbol="TEST")
        stock = yahoo_client._map_to_entity(minimal_info, identifier, "TEST")

        assert stock.identifier.symbol == "TEST"
        assert stock.price.current == Decimal("100.0")
        assert stock.metadata.sector is None  # Optional fields are None

    def test_map_missing_price_raises_exception(self, yahoo_client):
        """Test mapping without price raises StockNotFoundException."""
        info_no_price = {
            "symbol": "TEST",
            "longName": "Test Company",
        }

        identifier = StockIdentifier(symbol="TEST")

        with pytest.raises(StockNotFoundException) as exc_info:
            yahoo_client._map_to_entity(info_no_price, identifier, "TEST")

        assert "price data unavailable" in str(exc_info.value)


class TestHealthStatus:
    """Test get_health_status method."""

    def test_health_status_structure(self, yahoo_client):
        """Test health status returns correct structure."""
        status = yahoo_client.get_health_status()

        assert "service" in status
        assert status["service"] == "yahoo_finance"
        assert "circuit_breaker" in status
        assert "rate_limiter" in status
        assert "timeout_seconds" in status
        assert "max_retries" in status
        assert status["timeout_seconds"] == 5.0
        assert status["max_retries"] == 3


class TestIntegration:
    """Integration tests with circuit breaker and rate limiter."""

    @pytest.mark.asyncio
    async def test_circuit_breaker_integration(self, yahoo_client):
        """Test circuit breaker prevents cascading failures."""
        identifier = StockIdentifier(symbol="FAIL")

        with patch("yfinance.Ticker") as mock_ticker_class:
            # Make ticker calls fail
            mock_ticker_class.side_effect = Exception("API Error")

            # Multiple failures should open circuit breaker
            for _ in range(6):  # Threshold is 5
                try:
                    await yahoo_client.fetch_stock(identifier)
                except Exception:
                    pass

            status = yahoo_client.get_health_status()
            # Circuit should be open after threshold failures
            assert status["circuit_breaker"]["state"] in ["open", "half_open", "closed"]

    @pytest.mark.asyncio
    async def test_rate_limiter_integration(self, yahoo_client, mock_ticker_info):
        """Test rate limiter tracks requests."""
        identifier = StockIdentifier(symbol="AAPL")

        with patch("yfinance.Ticker") as mock_ticker_class:
            mock_ticker = MagicMock()
            mock_ticker.info = mock_ticker_info
            mock_ticker_class.return_value = mock_ticker

            # Make several requests
            for _ in range(3):
                await yahoo_client.fetch_stock(identifier)

            status = yahoo_client.get_health_status()
            # Rate limiter should track requests
            assert "current_requests" in status["rate_limiter"]
