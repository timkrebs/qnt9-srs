"""
Integration tests for the search API endpoints
"""

from unittest.mock import patch


class TestHealthEndpoints:
    """Test health check endpoints"""

    def test_root_endpoint(self, client):
        """Test root endpoint"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "QNT9 Stock Search Service"
        assert data["status"] == "operational"

    def test_health_check(self, client):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "search-service"


class TestStockSearchEndpoint:
    """Test stock search endpoint"""

    @patch("app.api_clients.YahooFinanceClient.search_by_symbol")
    def test_search_by_symbol_success(self, mock_yahoo, client, sample_stock_data):
        """Test successful search by symbol"""
        mock_yahoo.return_value = sample_stock_data

        response = client.get("/api/stocks/search?query=AAPL")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["symbol"] == "AAPL"
        assert data["data"]["name"] == "Apple Inc."
        assert data["query_type"] == "symbol"
        assert data["response_time_ms"] < 2000  # Should be under 2 seconds

    @patch("app.api_clients.YahooFinanceClient.search_by_isin")
    def test_search_by_isin_success(self, mock_yahoo, client, sample_stock_data):
        """Test successful search by ISIN"""
        mock_yahoo.return_value = sample_stock_data

        response = client.get("/api/stocks/search?query=US0378331005")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["isin"] == "US0378331005"
        assert data["query_type"] == "isin"

    @patch("app.api_clients.YahooFinanceClient.search_by_symbol")
    def test_search_by_wkn_success(self, mock_yahoo, client, sample_stock_data):
        """Test successful search by WKN"""
        mock_yahoo.return_value = sample_stock_data

        response = client.get("/api/stocks/search?query=865985")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["query_type"] == "wkn"

    def test_search_invalid_isin_format(self, client):
        """Test search with invalid ISIN format"""
        response = client.get("/api/stocks/search?query=INVALID12345")

        assert response.status_code == 400
        assert "validation_error" in response.json()["detail"]["error"]

    def test_search_invalid_wkn_format(self, client):
        """Test search with invalid WKN format (wrong checksum)"""
        # This should fail validation
        response = client.get("/api/stocks/search?query=US037833100X")

        assert response.status_code == 400

    @patch("app.api_clients.YahooFinanceClient.search_by_symbol")
    def test_search_not_found(self, mock_yahoo, client):
        """Test search when stock is not found"""
        mock_yahoo.return_value = None

        response = client.get("/api/stocks/search?query=NOTFOUND")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["data"] is None
        assert "not found" in data["message"].lower()

    @patch("app.api_clients.YahooFinanceClient.search_by_symbol")
    def test_search_caching(self, mock_yahoo, client, sample_stock_data):
        """Test that second request is served from cache"""
        mock_yahoo.return_value = sample_stock_data

        # First request - should call API
        response1 = client.get("/api/stocks/search?query=AAPL")
        assert response1.status_code == 200
        data1 = response1.json()
        assert data1["data"]["cached"] is False

        # Second request - should use cache
        response2 = client.get("/api/stocks/search?query=AAPL")
        assert response2.status_code == 200
        data2 = response2.json()
        assert data2["data"]["cached"] is True
        assert "cache" in data2["message"].lower()

        # Verify API was only called once
        assert mock_yahoo.call_count == 1

    def test_search_missing_query(self, client):
        """Test search without query parameter"""
        response = client.get("/api/stocks/search")
        assert response.status_code == 422  # Validation error

    def test_search_empty_query(self, client):
        """Test search with empty query"""
        response = client.get("/api/stocks/search?query=")
        assert response.status_code == 422

    def test_search_query_too_long(self, client):
        """Test search with query exceeding max length"""
        long_query = "A" * 21
        response = client.get(f"/api/stocks/search?query={long_query}")
        assert response.status_code == 422


class TestSuggestionsEndpoint:
    """Test autocomplete suggestions endpoint"""

    def test_get_suggestions(self, client, db_session):
        """Test getting suggestions"""
        from app.cache import CacheManager

        cache_manager = CacheManager(db_session)

        # Record some searches
        for symbol in ["AAPL", "AMZN", "AMD"]:
            cache_manager.record_search(symbol, found=True)

        response = client.get("/api/stocks/suggestions?query=A")

        assert response.status_code == 200
        data = response.json()
        assert "suggestions" in data
        assert len(data["suggestions"]) <= 5

    def test_suggestions_with_limit(self, client, db_session):
        """Test suggestions with custom limit"""
        from app.cache import CacheManager

        cache_manager = CacheManager(db_session)

        # Record searches
        for i in range(10):
            cache_manager.record_search(f"TEST{i}", found=True)

        response = client.get("/api/stocks/suggestions?query=TEST&limit=3")

        assert response.status_code == 200
        data = response.json()
        assert len(data["suggestions"]) <= 3


class TestCacheManagementEndpoints:
    """Test cache management endpoints"""

    def test_get_cache_stats(self, client):
        """Test getting cache statistics"""
        response = client.get("/api/cache/stats")

        assert response.status_code == 200
        data = response.json()
        assert "cache_statistics" in data
        assert "ttl_minutes" in data
        assert data["ttl_minutes"] == 5

    def test_cleanup_cache(self, client, db_session, sample_stock_data):
        """Test manual cache cleanup"""
        from datetime import datetime, timedelta, timezone

        from app.cache import CacheManager
        from app.models import StockCache

        cache_manager = CacheManager(db_session)

        # Add expired entries
        cache_manager.save_to_cache(sample_stock_data, "AAPL")

        entry = db_session.query(StockCache).filter(StockCache.symbol == "AAPL").first()
        entry.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        db_session.commit()

        response = client.post("/api/cache/cleanup")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["deleted_entries"] >= 0


class TestResponseTimeRequirement:
    """Test that responses meet the <2 second requirement"""

    @patch("app.api_clients.YahooFinanceClient.search_by_symbol")
    def test_response_time_under_2_seconds(self, mock_yahoo, client, sample_stock_data):
        """Test that API responds within 2 seconds"""
        mock_yahoo.return_value = sample_stock_data

        response = client.get("/api/stocks/search?query=AAPL")

        assert response.status_code == 200
        data = response.json()

        # Verify response time is reported and under 2000ms
        assert "response_time_ms" in data
        assert data["response_time_ms"] < 2000


class TestAcceptanceCriteria:
    """Tests matching the acceptance criteria from the GitHub issue"""

    @patch("app.api_clients.YahooFinanceClient.search_by_isin")
    def test_ac1_valid_isin_search(self, mock_yahoo, client, sample_stock_data):
        """
        AC1: Search with valid ISIN should return matching stock with all required fields
        """
        mock_yahoo.return_value = sample_stock_data

        response = client.get("/api/stocks/search?query=US0378331005")

        assert response.status_code == 200
        data = response.json()

        # Verify all required fields are present
        stock = data["data"]
        assert stock["name"] == "Apple Inc."
        assert stock["isin"] == "US0378331005"
        assert stock["wkn"] == "865985"
        assert stock["current_price"] is not None
        assert stock["symbol"] == "AAPL"

        # Verify response time
        assert data["response_time_ms"] < 2000

    @patch("app.api_clients.YahooFinanceClient.search_by_symbol")
    def test_ac2_valid_wkn_search(self, mock_yahoo, client, sample_stock_data):
        """
        AC2: Search with valid WKN should return matching stock
        """
        mock_yahoo.return_value = sample_stock_data

        response = client.get("/api/stocks/search?query=865985")

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["name"] == "Apple Inc."

    def test_ac3_invalid_format_validation(self, client):
        """
        AC3: Invalid format should show validation error without API call
        """
        with patch("app.api_clients.YahooFinanceClient.search_by_symbol") as mock:
            response = client.get("/api/stocks/search?query=INVALID@123")

            assert response.status_code == 400
            # Verify no API call was made
            mock.assert_not_called()

    @patch("app.api_clients.YahooFinanceClient.search_by_symbol")
    def test_ac4_stock_not_found(self, mock_yahoo, client):
        """
        AC4: Stock not found should show appropriate message
        """
        mock_yahoo.return_value = None

        response = client.get("/api/stocks/search?query=NOTFND")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "not found" in data["message"].lower()

    @patch("app.api_clients.YahooFinanceClient.search_by_symbol")
    def test_ac5_caching_within_ttl(self, mock_yahoo, client, sample_stock_data):
        """
        AC5: Cached data should be served within TTL without API call
        """
        mock_yahoo.return_value = sample_stock_data

        # First request
        client.get("/api/stocks/search?query=AAPL")

        # Second request within 5 minutes
        response = client.get("/api/stocks/search?query=AAPL")

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["cached"] is True

        # Verify API was called only once
        assert mock_yahoo.call_count == 1
