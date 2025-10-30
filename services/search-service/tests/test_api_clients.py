"""
Tests for API clients (Yahoo Finance and Alpha Vantage)
"""
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from app.api_clients import AlphaVantageClient, RateLimiter, YahooFinanceClient


class TestRateLimiter:
    """Test RateLimiter functionality"""

    def test_rate_limiter_allows_requests_within_limit(self):
        """Test that requests are allowed within rate limit"""
        limiter = RateLimiter(max_requests=5, window_seconds=60)

        # Should allow first 5 requests
        for _ in range(5):
            assert limiter.is_allowed() is True
            limiter.record_request()

    def test_rate_limiter_blocks_requests_over_limit(self):
        """Test that requests are blocked when over limit"""
        limiter = RateLimiter(max_requests=2, window_seconds=60)

        # First 2 requests allowed
        assert limiter.is_allowed() is True
        limiter.record_request()
        assert limiter.is_allowed() is True
        limiter.record_request()

        # Third request blocked
        assert limiter.is_allowed() is False

    def test_rate_limiter_cleans_old_requests(self):
        """Test that old requests are removed from tracking"""
        limiter = RateLimiter(max_requests=2, window_seconds=1)

        # Add old request
        old_time = datetime.utcnow() - timedelta(seconds=2)
        limiter.requests.append(old_time)

        # Should be allowed as old request is cleaned
        assert limiter.is_allowed() is True


class TestYahooFinanceClient:
    """Test Yahoo Finance client"""

    @patch("app.api_clients.yf.Ticker")
    def test_search_by_isin_success(self, mock_ticker):
        """Test successful ISIN search"""
        # Mock Yahoo Finance response
        mock_info = {
            "symbol": "AAPL",
            "shortName": "Apple Inc.",
            "currentPrice": 150.0,
            "currency": "USD",
            "exchange": "NASDAQ",
            "marketCap": 2500000000000,
            "sector": "Technology",
            "industry": "Consumer Electronics",
        }
        mock_ticker.return_value.info = mock_info

        client = YahooFinanceClient()
        result = client.search_by_isin("US0378331005")

        assert result is not None
        assert result["symbol"] == "AAPL"
        assert result["name"] == "Apple Inc."
        assert result["current_price"] == 150.0

    @patch("app.api_clients.yf.Ticker")
    def test_search_by_isin_no_data(self, mock_ticker):
        """Test ISIN search with no data"""
        mock_ticker.return_value.info = {}

        client = YahooFinanceClient()
        result = client.search_by_isin("INVALID123456")

        assert result is None

    @patch("app.api_clients.yf.Ticker")
    def test_search_by_wkn_success(self, mock_ticker):
        """Test successful WKN search"""
        mock_info = {
            "symbol": "SAP",
            "shortName": "SAP SE",
            "currentPrice": 120.0,
            "currency": "EUR",
        }
        mock_ticker.return_value.info = mock_info

        client = YahooFinanceClient()
        result = client.search_by_wkn("716460")

        assert result is not None
        assert result["symbol"] == "SAP"

    @patch("app.api_clients.yf.Ticker")
    def test_search_by_symbol_success(self, mock_ticker):
        """Test successful symbol search"""
        mock_info = {
            "symbol": "MSFT",
            "shortName": "Microsoft Corporation",
            "currentPrice": 300.0,
            "currency": "USD",
        }
        mock_ticker.return_value.info = mock_info

        client = YahooFinanceClient()
        result = client.search_by_symbol("MSFT")

        assert result is not None
        assert result["symbol"] == "MSFT"
        assert result["name"] == "Microsoft Corporation"

    @patch("app.api_clients.yf.Ticker")
    def test_search_respects_rate_limit(self, mock_ticker):
        """Test that rate limiting is respected"""
        client = YahooFinanceClient()
        client.rate_limiter = RateLimiter(max_requests=1, window_seconds=60)

        mock_ticker.return_value.info = {"symbol": "AAPL"}

        # First request should work
        result1 = client.search_by_symbol("AAPL")
        assert result1 is not None

        # Second request should be rate limited
        result2 = client.search_by_symbol("MSFT")
        assert result2 is None

    @patch("app.api_clients.yf.Ticker")
    def test_isin_to_symbol_conversion(self, mock_ticker):
        """Test ISIN to symbol conversion helper"""
        mock_ticker.return_value.info = {"symbol": "AAPL"}

        client = YahooFinanceClient()
        symbol = client._isin_to_symbol("US0378331005")

        assert symbol == "AAPL"

    @patch("app.api_clients.yf.Ticker")
    def test_isin_to_symbol_failure(self, mock_ticker):
        """Test ISIN to symbol conversion failure"""
        mock_ticker.return_value.info = {}

        client = YahooFinanceClient()
        symbol = client._isin_to_symbol("INVALID")

        assert symbol is None


class TestAlphaVantageClient:
    """Test Alpha Vantage client"""

    @patch("app.api_clients.requests.get")
    def test_search_by_isin_success(self, mock_get):
        """Test successful ISIN search via Alpha Vantage"""
        # Mock API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "Global Quote": {
                "01. symbol": "AAPL",
                "05. price": "150.00",
                "08. previous close": "148.00",
            }
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        client = AlphaVantageClient(api_key="test_key")
        result = client.search_by_isin("US0378331005")

        # Alpha Vantage doesn't support ISIN directly
        assert result is None

    @patch("app.api_clients.requests.get")
    def test_search_by_symbol_success(self, mock_get):
        """Test successful symbol search"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "Global Quote": {
                "01. symbol": "AAPL",
                "05. price": "150.00",
                "08. previous close": "148.00",
            }
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        client = AlphaVantageClient(api_key="test_key")
        result = client.search_by_symbol("AAPL")

        assert result is not None
        assert result["symbol"] == "AAPL"
        assert result["current_price"] == 150.0

    @patch("app.api_clients.requests.get")
    def test_search_respects_rate_limit(self, mock_get):
        """Test that rate limiting is respected"""
        client = AlphaVantageClient(api_key="test_key")
        client.rate_limiter = RateLimiter(max_requests=1, window_seconds=60)

        mock_response = Mock()
        mock_response.json.return_value = {"Global Quote": {"01. symbol": "AAPL"}}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        # First request should work
        result1 = client.search_by_symbol("AAPL")
        assert result1 is not None

        # Second request should be rate limited
        result2 = client.search_by_symbol("MSFT")
        assert result2 is None

    @patch("app.api_clients.requests.get")
    def test_search_handles_api_error(self, mock_get):
        """Test handling of API errors"""
        mock_get.side_effect = Exception("API Error")

        client = AlphaVantageClient(api_key="test_key")
        result = client.search_by_symbol("AAPL")

        assert result is None

    @patch("app.api_clients.requests.get")
    def test_search_handles_empty_response(self, mock_get):
        """Test handling of empty API response"""
        mock_response = Mock()
        mock_response.json.return_value = {}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        client = AlphaVantageClient(api_key="test_key")
        result = client.search_by_symbol("INVALID")

        assert result is None

    def test_uses_demo_key_by_default(self):
        """Test that demo API key is used by default"""
        client = AlphaVantageClient()
        assert client.api_key == "demo"

    def test_uses_custom_api_key(self):
        """Test that custom API key is used when provided"""
        client = AlphaVantageClient(api_key="custom_key")
        assert client.api_key == "custom_key"
