"""
Unit tests for stock report endpoint and functionality.

Tests cover:
- Stock report API endpoint
- Report caching mechanisms
- Fallback logic for cached data
- Error handling and edge cases
- ISIN to symbol resolution
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch


class TestStockReportEndpoint:
    """Test stock report endpoint functionality"""

    @patch("app.api_clients.StockAPIClient.get_stock_report_data")
    def test_get_stock_report_by_symbol_success(self, mock_report_data, client):
        """Test successful stock report retrieval by symbol"""
        mock_report_data.return_value = {
            "basic_info": {
                "symbol": "AAPL",
                "name": "Apple Inc.",
                "isin": "US0378331005",
                "wkn": "865985",
                "current_price": 175.50,
                "currency": "USD",
                "exchange": "NASDAQ",
                "market_cap": 2800000000000,
                "sector": "Technology",
                "industry": "Consumer Electronics",
                "source": "yahoo",
                "raw_data": {},
            },
            "price_history_7d": [
                {
                    "timestamp": "2024-01-01T00:00:00Z",
                    "price": 170.0,
                    "volume": 1000000,
                },
                {
                    "timestamp": "2024-01-02T00:00:00Z",
                    "price": 172.0,
                    "volume": 1100000,
                },
                {
                    "timestamp": "2024-01-03T00:00:00Z",
                    "price": 175.5,
                    "volume": 1200000,
                },
            ],
            "week_52_range": {
                "high": 199.62,
                "low": 164.08,
                "high_date": "2024-06-15T00:00:00Z",
                "low_date": "2023-12-01T00:00:00Z",
            },
            "price_change_1d": {
                "absolute": 2.5,
                "percentage": 1.44,
                "direction": "up",
            },
        }

        response = client.get("/api/stocks/AAPL/report")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["symbol"] == "AAPL"
        assert data["data"]["name"] == "Apple Inc."
        assert data["data"]["current_price"] == 175.50
        assert data["data"]["currency"] == "USD"
        assert data["data"]["price_change_1d"]["direction"] == "up"
        assert len(data["data"]["price_history_7d"]) == 3
        assert data["response_time_ms"] < 2000  # Under 2 seconds requirement

    @patch("app.api_clients.YahooFinanceClient.search_by_isin")
    @patch("app.api_clients.StockAPIClient.get_stock_report_data")
    def test_get_stock_report_by_isin_success(
        self, mock_report_data, mock_search_isin, client
    ):
        """Test successful stock report retrieval by ISIN"""
        # Mock ISIN to symbol conversion
        mock_search_isin.return_value = {
            "symbol": "AAPL",
            "name": "Apple Inc.",
            "isin": "US0378331005",
        }

        # Mock report data
        mock_report_data.return_value = {
            "basic_info": {
                "symbol": "AAPL",
                "name": "Apple Inc.",
                "isin": "US0378331005",
                "current_price": 175.50,
                "currency": "USD",
                "exchange": "NASDAQ",
                "source": "yahoo",
                "raw_data": {},
            },
            "price_history_7d": [
                {"timestamp": "2024-01-01T00:00:00Z", "price": 170.0, "volume": 1000000}
            ],
            "week_52_range": {"high": 199.62, "low": 164.08},
            "price_change_1d": {"absolute": 2.5, "percentage": 1.44, "direction": "up"},
        }

        response = client.get("/api/stocks/US0378331005/report")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["isin"] == "US0378331005"

    @patch("app.api_clients.StockAPIClient.get_stock_report_data")
    def test_get_stock_report_not_found(self, mock_report_data, client):
        """Test stock report when stock not found"""
        mock_report_data.return_value = None

        response = client.get("/api/stocks/NOTFOUND/report")

        assert response.status_code == 404
        data = response.json()
        assert "stock_not_found" in data["detail"]["error"]

    @patch("app.api_clients.YahooFinanceClient.search_by_isin")
    def test_get_stock_report_isin_not_found(self, mock_search_isin, client):
        """Test stock report when ISIN cannot be resolved to symbol"""
        mock_search_isin.return_value = None

        response = client.get("/api/stocks/US0000000000/report")

        assert response.status_code == 404
        data = response.json()
        assert "stock_not_found" in data["detail"]["error"]


class TestStockReportCaching:
    """Test stock report caching functionality"""

    @patch("app.api_clients.StockAPIClient.get_stock_report_data")
    def test_report_caching_works(self, mock_report_data, client):
        """Test that second request is served from cache"""
        mock_report_data.return_value = {
            "basic_info": {
                "symbol": "AAPL",
                "name": "Apple Inc.",
                "current_price": 175.50,
                "currency": "USD",
                "exchange": "NASDAQ",
                "source": "yahoo",
                "raw_data": {},
            },
            "price_history_7d": [
                {"timestamp": "2024-01-01T00:00:00Z", "price": 170.0, "volume": 1000000}
            ],
            "week_52_range": {"high": 199.62, "low": 164.08},
            "price_change_1d": {"absolute": 2.5, "percentage": 1.44, "direction": "up"},
        }

        # First request - should hit API
        response1 = client.get("/api/stocks/AAPL/report")
        assert response1.status_code == 200
        assert mock_report_data.call_count == 1

        # Second request - should hit cache
        response2 = client.get("/api/stocks/AAPL/report")
        assert response2.status_code == 200
        # Mock should not be called again
        assert mock_report_data.call_count == 1

        # Verify cache indicator
        data = response2.json()
        assert data["data"]["cached"] is True

    @patch("app.api_clients.StockAPIClient.get_stock_report_data")
    def test_stale_cache_fallback(self, mock_report_data, client, db_session):
        """Test fallback to stale cache when API fails"""
        from app.models import StockReportCache

        # Create expired cache entry
        expired_at = datetime.now(timezone.utc) - timedelta(minutes=10)
        stale_entry = StockReportCache(
            symbol="AAPL",
            name="Apple Inc.",
            current_price=170.0,
            currency="USD",
            exchange="NASDAQ",
            data_source="yahoo",
            expires_at=expired_at,
            price_history_7d='[{"timestamp": "2024-01-01T00:00:00Z", "price": 170.0}]',
        )
        db_session.add(stale_entry)
        db_session.commit()

        # Mock API failure
        mock_report_data.return_value = None

        response = client.get("/api/stocks/AAPL/report")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "cached data from" in data["message"].lower()
        assert data["data"]["cached"] is True


class TestStockReportPriceChange:
    """Test price change calculations in stock report"""

    @patch("app.api_clients.StockAPIClient.get_stock_report_data")
    def test_price_change_up(self, mock_report_data, client):
        """Test price increase is correctly indicated"""
        mock_report_data.return_value = {
            "basic_info": {
                "symbol": "AAPL",
                "name": "Apple Inc.",
                "current_price": 175.50,
                "currency": "USD",
                "exchange": "NASDAQ",
                "source": "yahoo",
                "raw_data": {},
            },
            "price_history_7d": [],
            "week_52_range": {"high": 199.62, "low": 164.08},
            "price_change_1d": {
                "absolute": 5.25,
                "percentage": 3.08,
                "direction": "up",
            },
        }

        response = client.get("/api/stocks/AAPL/report")

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["price_change_1d"]["direction"] == "up"
        assert data["data"]["price_change_1d"]["absolute"] == 5.25
        assert data["data"]["price_change_1d"]["percentage"] == 3.08

    @patch("app.api_clients.StockAPIClient.get_stock_report_data")
    def test_price_change_down(self, mock_report_data, client):
        """Test price decrease is correctly indicated"""
        mock_report_data.return_value = {
            "basic_info": {
                "symbol": "AAPL",
                "name": "Apple Inc.",
                "current_price": 170.0,
                "currency": "USD",
                "exchange": "NASDAQ",
                "source": "yahoo",
                "raw_data": {},
            },
            "price_history_7d": [],
            "week_52_range": {"high": 199.62, "low": 164.08},
            "price_change_1d": {
                "absolute": -3.50,
                "percentage": -2.02,
                "direction": "down",
            },
        }

        response = client.get("/api/stocks/AAPL/report")

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["price_change_1d"]["direction"] == "down"
        assert data["data"]["price_change_1d"]["absolute"] == -3.50
        assert data["data"]["price_change_1d"]["percentage"] == -2.02


class TestStockReport52WeekRange:
    """Test 52-week high/low range in stock report"""

    @patch("app.api_clients.StockAPIClient.get_stock_report_data")
    def test_52_week_range_included(self, mock_report_data, client):
        """Test 52-week range is included in report"""
        mock_report_data.return_value = {
            "basic_info": {
                "symbol": "AAPL",
                "name": "Apple Inc.",
                "current_price": 175.50,
                "currency": "USD",
                "exchange": "NASDAQ",
                "source": "yahoo",
                "raw_data": {},
            },
            "price_history_7d": [],
            "week_52_range": {
                "high": 199.62,
                "low": 164.08,
                "high_date": "2024-06-15T00:00:00Z",
                "low_date": "2023-12-01T00:00:00Z",
            },
            "price_change_1d": {"absolute": 2.5, "percentage": 1.44, "direction": "up"},
        }

        response = client.get("/api/stocks/AAPL/report")

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["week_52_range"]["high"] == 199.62
        assert data["data"]["week_52_range"]["low"] == 164.08
        assert data["data"]["week_52_range"]["high_date"] == "2024-06-15T00:00:00Z"
        assert data["data"]["week_52_range"]["low_date"] == "2023-12-01T00:00:00Z"


class TestStockReportHistoricalData:
    """Test historical price data in stock report"""

    @patch("app.api_clients.StockAPIClient.get_stock_report_data")
    def test_7_day_history_included(self, mock_report_data, client):
        """Test 7-day price history is included in report"""
        mock_report_data.return_value = {
            "basic_info": {
                "symbol": "AAPL",
                "name": "Apple Inc.",
                "current_price": 175.50,
                "currency": "USD",
                "exchange": "NASDAQ",
                "source": "yahoo",
                "raw_data": {},
            },
            "price_history_7d": [
                {
                    "timestamp": "2024-01-01T00:00:00Z",
                    "price": 170.0,
                    "volume": 1000000,
                },
                {
                    "timestamp": "2024-01-02T00:00:00Z",
                    "price": 171.5,
                    "volume": 1050000,
                },
                {
                    "timestamp": "2024-01-03T00:00:00Z",
                    "price": 172.0,
                    "volume": 1100000,
                },
                {
                    "timestamp": "2024-01-04T00:00:00Z",
                    "price": 173.5,
                    "volume": 1150000,
                },
                {
                    "timestamp": "2024-01-05T00:00:00Z",
                    "price": 174.0,
                    "volume": 1200000,
                },
                {
                    "timestamp": "2024-01-06T00:00:00Z",
                    "price": 175.0,
                    "volume": 1250000,
                },
                {
                    "timestamp": "2024-01-07T00:00:00Z",
                    "price": 175.5,
                    "volume": 1300000,
                },
            ],
            "week_52_range": {"high": 199.62, "low": 164.08},
            "price_change_1d": {"absolute": 2.5, "percentage": 1.44, "direction": "up"},
        }

        response = client.get("/api/stocks/AAPL/report")

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]["price_history_7d"]) == 7
        assert (
            data["data"]["price_history_7d"][0]["timestamp"] == "2024-01-01T00:00:00Z"
        )
        assert data["data"]["price_history_7d"][0]["price"] == 170.0
        assert data["data"]["price_history_7d"][0]["volume"] == 1000000


class TestStockReportErrorHandling:
    """Test error handling in stock report endpoint"""

    @patch("app.api_clients.StockAPIClient.get_stock_report_data")
    def test_api_error_handling(self, mock_report_data, client):
        """Test graceful error handling when API fails"""
        mock_report_data.side_effect = Exception("API Error")

        response = client.get("/api/stocks/AAPL/report")

        assert response.status_code == 500
        data = response.json()
        assert "internal_error" in data["detail"]["error"]

    @patch("app.api_clients.StockAPIClient.get_stock_report_data")
    def test_incomplete_data_validation(self, mock_report_data, client):
        """Test validation of incomplete report data"""
        # Missing required fields
        mock_report_data.return_value = {
            "basic_info": {
                "symbol": "AAPL",
                # Missing name, current_price, etc.
            },
            "price_history_7d": [],
            "week_52_range": None,
            "price_change_1d": None,
        }

        response = client.get("/api/stocks/AAPL/report")

        # Should handle gracefully
        assert response.status_code in [400, 500]


class TestStockReportResponseTime:
    """Test response time requirements"""

    @patch("app.api_clients.StockAPIClient.get_stock_report_data")
    def test_response_time_under_2_seconds(self, mock_report_data, client):
        """Test that response time is under 2 seconds"""
        mock_report_data.return_value = {
            "basic_info": {
                "symbol": "AAPL",
                "name": "Apple Inc.",
                "current_price": 175.50,
                "currency": "USD",
                "exchange": "NASDAQ",
                "source": "yahoo",
                "raw_data": {},
            },
            "price_history_7d": [
                {"timestamp": "2024-01-01T00:00:00Z", "price": 170.0, "volume": 1000000}
            ],
            "week_52_range": {"high": 199.62, "low": 164.08},
            "price_change_1d": {"absolute": 2.5, "percentage": 1.44, "direction": "up"},
        }

        response = client.get("/api/stocks/AAPL/report")

        assert response.status_code == 200
        data = response.json()
        assert data["response_time_ms"] < 2000  # Under 2 seconds requirement
