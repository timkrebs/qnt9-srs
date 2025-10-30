"""
Unit tests for cache module
"""

from datetime import datetime, timedelta

from app.cache import CacheManager
from app.models import SearchHistory, StockCache


class TestCacheManager:
    """Test cache management functionality"""

    def test_cache_miss(self, db_session):
        """Test cache miss scenario"""
        cache_manager = CacheManager(db_session)
        result = cache_manager.get_cached_stock("AAPL")
        assert result is None

    def test_cache_save_and_retrieve(self, db_session, sample_stock_data):
        """Test saving to cache and retrieving"""
        cache_manager = CacheManager(db_session)

        # Save to cache
        success = cache_manager.save_to_cache(sample_stock_data, "AAPL")
        assert success is True

        # Retrieve from cache
        cached = cache_manager.get_cached_stock("AAPL")
        assert cached is not None
        assert cached["symbol"] == "AAPL"
        assert cached["name"] == "Apple Inc."
        assert cached["cached"] is True

    def test_cache_by_isin(self, db_session, sample_stock_data):
        """Test cache retrieval by ISIN"""
        cache_manager = CacheManager(db_session)

        cache_manager.save_to_cache(sample_stock_data, "US0378331005")

        # Retrieve by ISIN
        cached = cache_manager.get_cached_stock("US0378331005")
        assert cached is not None
        assert cached["symbol"] == "AAPL"
        assert cached["isin"] == "US0378331005"

    def test_cache_by_wkn(self, db_session, sample_stock_data):
        """Test cache retrieval by WKN"""
        cache_manager = CacheManager(db_session)

        cache_manager.save_to_cache(sample_stock_data, "865985")

        # Retrieve by WKN
        cached = cache_manager.get_cached_stock("865985")
        assert cached is not None
        assert cached["symbol"] == "AAPL"

    def test_cache_expiry(self, db_session, sample_stock_data):
        """Test cache expiration"""
        cache_manager = CacheManager(db_session)

        # Save to cache
        cache_manager.save_to_cache(sample_stock_data, "AAPL")

        # Manually expire the cache entry
        entry = db_session.query(StockCache).filter(StockCache.symbol == "AAPL").first()
        entry.expires_at = datetime.utcnow() - timedelta(minutes=1)
        db_session.commit()

        # Try to retrieve - should return None
        cached = cache_manager.get_cached_stock("AAPL")
        assert cached is None

    def test_cache_hit_counter(self, db_session, sample_stock_data):
        """Test cache hit counting"""
        cache_manager = CacheManager(db_session)

        cache_manager.save_to_cache(sample_stock_data, "AAPL")

        # Retrieve multiple times
        cache_manager.get_cached_stock("AAPL")
        cache_manager.get_cached_stock("AAPL")
        cache_manager.get_cached_stock("AAPL")

        # Check hit count
        entry = db_session.query(StockCache).filter(StockCache.symbol == "AAPL").first()
        assert entry.cache_hits == 3

    def test_cache_update(self, db_session, sample_stock_data):
        """Test updating existing cache entry"""
        cache_manager = CacheManager(db_session)

        # Save initial data
        cache_manager.save_to_cache(sample_stock_data, "AAPL")

        # Update with new price
        updated_data = sample_stock_data.copy()
        updated_data["current_price"] = 180.00

        cache_manager.save_to_cache(updated_data, "AAPL")

        # Verify update
        cached = cache_manager.get_cached_stock("AAPL")
        assert cached["current_price"] == 180.00

    def test_cleanup_expired(self, db_session, sample_stock_data):
        """Test cleanup of expired entries"""
        cache_manager = CacheManager(db_session)

        # Create multiple entries with unique ISINs
        for symbol, isin in [
            ("AAPL", "US0378331005"),
            ("MSFT", "US5949181045"),
            ("GOOGL", "US02079K3059"),
        ]:
            data = sample_stock_data.copy()
            data["symbol"] = symbol
            data["isin"] = isin
            data["wkn"] = None  # Clear WKN to avoid conflicts
            cache_manager.save_to_cache(data, symbol)

        # Expire 2 entries
        for symbol in ["AAPL", "MSFT"]:
            entry = db_session.query(StockCache).filter(StockCache.symbol == symbol).first()
            entry.expires_at = datetime.utcnow() - timedelta(minutes=1)
        db_session.commit()

        # Run cleanup
        deleted = cache_manager.cleanup_expired()
        assert deleted == 2

        # Verify only one entry remains
        remaining = db_session.query(StockCache).count()
        assert remaining == 1


class TestSearchHistory:
    """Test search history tracking"""

    def test_record_search(self, db_session):
        """Test recording search history"""
        cache_manager = CacheManager(db_session)

        cache_manager.record_search("AAPL", found=True)

        # Verify record
        history = db_session.query(SearchHistory).filter(SearchHistory.query == "AAPL").first()
        assert history is not None
        assert history.search_count == 1
        assert history.result_found == 1

    def test_record_multiple_searches(self, db_session):
        """Test recording multiple searches for same query"""
        cache_manager = CacheManager(db_session)

        # Search multiple times
        for _ in range(3):
            cache_manager.record_search("AAPL", found=True)

        # Verify count
        history = db_session.query(SearchHistory).filter(SearchHistory.query == "AAPL").first()
        assert history.search_count == 3

    def test_get_suggestions(self, db_session):
        """Test getting search suggestions"""
        cache_manager = CacheManager(db_session)

        # Record some successful searches
        queries = ["AAPL", "AMZN", "AMD", "GOOGL", "MSFT"]
        for query in queries:
            cache_manager.record_search(query, found=True)

        # Get suggestions starting with 'A'
        suggestions = cache_manager.get_suggestions("A", limit=5)
        assert len(suggestions) <= 5
        assert all(s.startswith("A") for s in suggestions)

    def test_suggestions_ordering(self, db_session):
        """Test that suggestions are ordered by popularity"""
        cache_manager = CacheManager(db_session)

        # Search with different frequencies
        for _ in range(5):
            cache_manager.record_search("AAPL", found=True)
        for _ in range(3):
            cache_manager.record_search("AMZN", found=True)
        for _ in range(1):
            cache_manager.record_search("AMD", found=True)

        # Get suggestions
        suggestions = cache_manager.get_suggestions("A", limit=5)

        # AAPL should be first (most searches)
        assert suggestions[0] == "AAPL"


class TestCacheStats:
    """Test cache statistics"""

    def test_cache_stats(self, db_session, sample_stock_data):
        """Test getting cache statistics"""
        cache_manager = CacheManager(db_session)

        # Add some entries with unique ISINs
        for symbol, isin in [
            ("AAPL", "US0378331005"),
            ("MSFT", "US5949181045"),
            ("GOOGL", "US02079K3059"),
        ]:
            data = sample_stock_data.copy()
            data["symbol"] = symbol
            data["isin"] = isin
            data["wkn"] = None  # Clear WKN to avoid conflicts
            cache_manager.save_to_cache(data, symbol)

        # Get some hits
        cache_manager.get_cached_stock("AAPL")
        cache_manager.get_cached_stock("AAPL")
        cache_manager.get_cached_stock("MSFT")

        stats = cache_manager.get_cache_stats()

        assert stats["total_entries"] == 3
        assert stats["active_entries"] == 3
        assert stats["expired_entries"] == 0
        assert stats["total_hits"] == 3
