"""
Tests for company name search functionality.

Tests the name search endpoint and related validation,
including fuzzy matching, relevance scoring, and caching.
"""

from datetime import datetime, timedelta, timezone

import pytest

from app.cache import CacheManager
from app.models import StockCache
from app.validators import MAX_NAME_SEARCH_RESULTS, NameSearchQuery


class TestNameSearchValidation:
    """Test suite for name search input validation."""

    def test_valid_name_query(self):
        """Test that valid company names are accepted."""
        # Minimum length (3 characters)
        query = NameSearchQuery(query="App")
        assert query.query == "App"

        # Regular company name
        query = NameSearchQuery(query="Apple Inc")
        assert query.query == "Apple Inc"

        # Long company name
        query = NameSearchQuery(query="International Business Machines Corporation")
        assert query.query == "International Business Machines Corporation"

    def test_query_normalization(self):
        """Test that queries are normalized (whitespace trimmed)."""
        query = NameSearchQuery(query="  Apple  ")
        assert query.query == "Apple"

        query = NameSearchQuery(query="Microsoft\t")
        assert query.query == "Microsoft"

    def test_query_too_short(self):
        """Test that queries shorter than 3 characters are rejected."""
        with pytest.raises(ValueError, match="at least 3 characters"):
            NameSearchQuery(query="AB")

        with pytest.raises(ValueError, match="at least 3 characters"):
            NameSearchQuery(query="A")

    def test_empty_query(self):
        """Test that empty queries are rejected."""
        with pytest.raises(ValueError, match="at least 3 characters"):
            NameSearchQuery(query="   ")

        with pytest.raises(ValueError):
            NameSearchQuery(query="")


class TestNameSearchEndpoint:
    """Test suite for the name search API endpoint."""

    def test_search_by_name_success(self, client, db_session):
        """Test successful name search with results."""
        # Add test data to cache
        cache_manager = CacheManager(db_session)

        stock_data = {
            "symbol": "AAPL",
            "name": "Apple Inc.",
            "current_price": 150.0,
            "currency": "USD",
            "exchange": "NASDAQ",
            "isin": "US0378331005",
            "wkn": "865985",
            "source": "yahoo",
        }

        cache_manager.save_to_cache(stock_data, "AAPL")
        db_session.flush()  # Ensure data is written
        db_session.commit()

        # Search for the stock
        response = client.get("/api/stocks/search/name?query=Apple")

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["total_results"] >= 1
        assert len(data["results"]) >= 1
        assert data["query"] == "Apple"
        assert data["response_time_ms"] >= 0

        # Check first result
        result = data["results"][0]
        assert result["symbol"] == "AAPL"
        assert result["name"] == "Apple Inc."
        assert result["relevance_score"] > 0.0

    def test_search_partial_match(self, client, db_session):
        """Test partial name matching."""
        # Add test data
        cache_manager = CacheManager(db_session)

        companies = [
            {"symbol": "MSFT", "name": "Microsoft Corporation"},
            {"symbol": "AAPL", "name": "Apple Inc."},
            {"symbol": "GOOGL", "name": "Alphabet Inc."},
        ]

        for company in companies:
            stock_data = {
                **company,
                "current_price": 100.0,
                "currency": "USD",
                "exchange": "NASDAQ",
                "source": "yahoo",
            }
            cache_manager.save_to_cache(stock_data, stock_data["symbol"])

        db_session.commit()

        # Search for "corp" should find Microsoft
        response = client.get("/api/stocks/search/name?query=Corp")
        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["total_results"] >= 1

        # Find Microsoft in results
        found = any(r["symbol"] == "MSFT" for r in data["results"])
        assert found, "Microsoft Corporation should be found with 'Corp' query"

    def test_search_no_results(self, client):
        """Test name search with no matching results."""
        response = client.get("/api/stocks/search/name?query=NonExistentCompany")

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["total_results"] == 0
        assert len(data["results"]) == 0
        assert data["message"] == "No stocks found matching your search"

    def test_search_case_insensitive(self, client, db_session):
        """Test that search is case-insensitive."""
        # Add test data
        cache_manager = CacheManager(db_session)

        stock_data = {
            "symbol": "AAPL",
            "name": "Apple Inc.",
            "current_price": 150.0,
            "currency": "USD",
            "exchange": "NASDAQ",
            "source": "yahoo",
        }

        cache_manager.save_to_cache(stock_data, stock_data["symbol"])
        db_session.commit()

        # Test different cases
        for query in ["apple", "APPLE", "ApPlE", "aPpLe"]:
            response = client.get(f"/api/stocks/search/name?query={query}")
            assert response.status_code == 200
            data = response.json()

            assert data["success"] is True
            assert data["total_results"] >= 1
            assert any(r["symbol"] == "AAPL" for r in data["results"])

    def test_search_with_limit(self, client, db_session):
        """Test that limit parameter works correctly."""
        # Add multiple test stocks
        cache_manager = CacheManager(db_session)

        for i in range(15):
            stock_data = {
                "symbol": f"TEST{i}",
                "name": f"Test Company {i}",
                "current_price": 100.0,
                "currency": "USD",
                "exchange": "NASDAQ",
                "source": "yahoo",
            }
            cache_manager.save_to_cache(stock_data, stock_data["symbol"])

        db_session.commit()

        # Test with limit=5
        response = client.get("/api/stocks/search/name?query=Test&limit=5")
        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert len(data["results"]) <= 5

    def test_search_min_length_validation(self, client):
        """Test that queries shorter than 3 characters are rejected."""
        response = client.get("/api/stocks/search/name?query=AB")
        assert response.status_code == 422  # Unprocessable Entity

    def test_search_empty_query(self, client):
        """Test that empty queries are rejected."""
        response = client.get("/api/stocks/search/name?query=")
        assert response.status_code == 422  # Unprocessable Entity

    def test_search_whitespace_only(self, client):
        """Test that whitespace-only queries are rejected."""
        response = client.get("/api/stocks/search/name?query=%20%20%20")
        assert response.status_code == 400


class TestRelevanceScoring:
    """Test suite for relevance scoring algorithm."""

    def test_exact_match_highest_score(self, db_session):
        """Test that exact matches get the highest relevance score."""
        cache_manager = CacheManager(db_session)

        # Add test data
        stock_data = {
            "symbol": "AAPL",
            "name": "Apple",
            "current_price": 150.0,
            "currency": "USD",
            "source": "yahoo",
        }
        cache_manager.save_to_cache(stock_data, stock_data["symbol"])
        db_session.commit()

        # Search with exact match
        results = cache_manager.search_by_name("Apple")

        assert len(results) == 1
        assert results[0]["relevance_score"] == 1.0

    def test_starts_with_high_score(self, db_session):
        """Test that matches starting with query get high score."""
        cache_manager = CacheManager(db_session)

        stock_data = {
            "symbol": "AAPL",
            "name": "Apple Inc.",
            "current_price": 150.0,
            "currency": "USD",
            "source": "yahoo",
        }
        cache_manager.save_to_cache(stock_data, stock_data["symbol"])
        db_session.commit()

        results = cache_manager.search_by_name("Apple")

        assert len(results) == 1
        assert results[0]["relevance_score"] == 0.9

    def test_contains_match_lower_score(self, db_session):
        """Test that partial matches get lower scores."""
        cache_manager = CacheManager(db_session)

        stock_data = {
            "symbol": "BRK.A",
            "name": "Berkshire Hathaway Inc.",
            "current_price": 500000.0,
            "currency": "USD",
            "source": "yahoo",
        }
        cache_manager.save_to_cache(stock_data, stock_data["symbol"])
        db_session.commit()

        results = cache_manager.search_by_name("Hathaway")

        assert len(results) == 1
        # Word boundary match should get 0.8
        assert results[0]["relevance_score"] == 0.8

    def test_results_sorted_by_relevance(self, db_session):
        """Test that results are sorted by relevance score."""
        cache_manager = CacheManager(db_session)

        companies = [
            {"symbol": "APL1", "name": "Applied Materials"},  # starts with
            {"symbol": "APL2", "name": "Apple Inc."},  # starts with
            {"symbol": "APL3", "name": "Snapple Group"},  # contains
        ]

        for company in companies:
            stock_data = {
                **company,
                "current_price": 100.0,
                "currency": "USD",
                "source": "yahoo",
            }
            cache_manager.save_to_cache(stock_data, stock_data["symbol"])

        db_session.commit()

        results = cache_manager.search_by_name("App")

        # Check that results are sorted by relevance
        for i in range(len(results) - 1):
            assert results[i]["relevance_score"] >= results[i + 1]["relevance_score"]


class TestNameSearchCache:
    """Test suite for name search caching behavior."""

    def test_search_ignores_expired_cache(self, db_session):
        """Test that expired cache entries are not returned in search."""
        # Add an expired entry directly
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        expired_entry = StockCache(
            symbol="AAPL",
            name="Apple Inc.",
            current_price=150.0,
            currency="USD",
            exchange="NASDAQ",
            data_source="yahoo",
            created_at=now - timedelta(minutes=10),
            updated_at=now - timedelta(minutes=10),
            expires_at=now - timedelta(minutes=5),  # Expired
        )

        db_session.add(expired_entry)
        db_session.commit()

        # Search should return no results
        cache_manager = CacheManager(db_session)
        results = cache_manager.search_by_name("Apple")

        assert len(results) == 0

    def test_search_returns_active_cache_only(self, db_session):
        """Test that only non-expired entries are returned."""
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        cache_manager = CacheManager(db_session)

        # Add active entry
        active_data = {
            "symbol": "AAPL",
            "name": "Apple Inc.",
            "current_price": 150.0,
            "currency": "USD",
            "source": "yahoo",
        }
        cache_manager.save_to_cache(active_data, "AAPL")

        # Add expired entry directly
        expired_entry = StockCache(
            symbol="MSFT",
            name="Microsoft Corporation",
            current_price=300.0,
            currency="USD",
            exchange="NASDAQ",
            data_source="yahoo",
            created_at=now - timedelta(minutes=10),
            updated_at=now - timedelta(minutes=10),
            expires_at=now - timedelta(minutes=1),  # Expired
        )

        db_session.add(expired_entry)
        db_session.commit()

        # Search should only return active entry
        results = cache_manager.search_by_name("Inc")

        assert len(results) == 1
        assert results[0]["symbol"] == "AAPL"


class TestAcceptanceCriteriaNameSearch:
    """Test suite for US-12 acceptance criteria."""

    def test_ac1_minimum_3_characters(self, client):
        """AC1: Search requires minimum 3 characters."""
        # Valid: 3 characters
        response = client.get("/api/stocks/search/name?query=App")
        assert response.status_code == 200

        # Invalid: 2 characters
        response = client.get("/api/stocks/search/name?query=Ab")
        assert response.status_code == 422

    def test_ac2_fuzzy_matching(self, client, db_session):
        """AC2: Fuzzy matching supports partial company names."""
        cache_manager = CacheManager(db_session)

        stock_data = {
            "symbol": "AAPL",
            "name": "Apple Inc.",
            "current_price": 150.0,
            "currency": "USD",
            "source": "yahoo",
        }
        cache_manager.save_to_cache(stock_data, stock_data["symbol"])
        db_session.commit()

        # Test partial matches
        for query in ["App", "apple", "Inc", "Apple I"]:
            response = client.get(f"/api/stocks/search/name?query={query}")
            assert response.status_code == 200
            data = response.json()
            assert data["total_results"] >= 1
            assert any(r["symbol"] == "AAPL" for r in data["results"])

    def test_ac3_top_10_results(self, client, db_session):
        """AC3: Returns top 10 results by default."""
        cache_manager = CacheManager(db_session)

        # Add 20 test companies
        for i in range(20):
            stock_data = {
                "symbol": f"TEST{i}",
                "name": f"Test Company {i}",
                "current_price": 100.0,
                "currency": "USD",
                "source": "yahoo",
            }
            cache_manager.save_to_cache(stock_data, stock_data["symbol"])

        db_session.commit()

        # Search without limit should return max 10
        response = client.get("/api/stocks/search/name?query=Test")
        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert len(data["results"]) <= MAX_NAME_SEARCH_RESULTS

    def test_ac4_response_time(self, client, db_session):
        """AC4: Response time should be under 1 second."""
        cache_manager = CacheManager(db_session)

        # Add test data
        for i in range(10):
            stock_data = {
                "symbol": f"TEST{i}",
                "name": f"Test Company {i}",
                "current_price": 100.0,
                "currency": "USD",
                "source": "yahoo",
            }
            cache_manager.save_to_cache(stock_data, stock_data["symbol"])

        db_session.commit()

        # Perform search and check response time
        response = client.get("/api/stocks/search/name?query=Test")
        assert response.status_code == 200
        data = response.json()

        # Response time should be included in response
        assert "response_time_ms" in data
        # Should be under 1000ms (1 second)
        assert data["response_time_ms"] < 1000

    def test_ac5_result_format(self, client, db_session):
        """AC5: Results include required fields."""
        cache_manager = CacheManager(db_session)

        stock_data = {
            "symbol": "AAPL",
            "name": "Apple Inc.",
            "isin": "US0378331005",
            "wkn": "865985",
            "current_price": 150.0,
            "currency": "USD",
            "exchange": "NASDAQ",
            "source": "yahoo",
        }
        cache_manager.save_to_cache(stock_data, stock_data["symbol"])
        db_session.commit()

        response = client.get("/api/stocks/search/name?query=Apple")
        assert response.status_code == 200
        data = response.json()

        assert len(data["results"]) >= 1
        result = data["results"][0]

        # Check all required fields are present
        assert "symbol" in result
        assert "name" in result
        assert "isin" in result
        assert "wkn" in result
        assert "current_price" in result
        assert "currency" in result
        assert "exchange" in result
        assert "relevance_score" in result

        # Verify field values
        assert result["symbol"] == "AAPL"
        assert result["name"] == "Apple Inc."
        assert result["isin"] == "US0378331005"
        assert result["wkn"] == "865985"
