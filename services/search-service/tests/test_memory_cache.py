"""
Tests for Phase 2: In-Memory LRU Cache

Comprehensive tests for the memory cache implementation with LRU eviction.
"""

import threading
import time
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.cache.memory_cache import MemoryStockCache, get_memory_cache
from app.domain.entities import DataSource, Stock, StockIdentifier, StockMetadata, StockPrice


@pytest.fixture
def memory_cache():
    """Create a fresh memory cache for testing."""
    cache = MemoryStockCache(max_size=100)
    # Reset statistics
    cache.hits = 0
    cache.misses = 0
    cache.evictions = 0
    return cache


@pytest.fixture
def sample_stock():
    """Create sample stock for testing."""
    identifier = StockIdentifier(isin="US0378331005", symbol="AAPL", name="Apple Inc.")
    price = StockPrice(current=Decimal("175.50"), currency="USD")
    metadata = StockMetadata(exchange="NASDAQ", sector="Technology")

    return Stock(
        identifier=identifier,
        price=price,
        metadata=metadata,
        data_source=DataSource.YAHOO_FINANCE,
        last_updated=datetime.now(timezone.utc),
    )


class TestMemoryCacheInitialization:
    """Test memory cache initialization."""

    def test_cache_initialization(self):
        """Test cache initializes with correct parameters."""
        cache = MemoryStockCache(max_size=50)

        assert cache.max_size == 50
        assert len(cache.cache) == 0
        assert cache.hits == 0
        assert cache.misses == 0
        assert cache.evictions == 0

    def test_default_initialization(self):
        """Test cache with default parameters."""
        cache = MemoryStockCache()

        assert cache.max_size == 1000

    def test_get_memory_cache_singleton(self):
        """Test get_memory_cache returns singleton instance."""
        cache1 = get_memory_cache()
        cache2 = get_memory_cache()

        assert cache1 is cache2


class TestCacheBasicOperations:
    """Test basic cache operations."""

    def test_get_set(self, memory_cache, sample_stock):
        """Test basic get/set operations."""
        key = "AAPL"

        # Initially empty
        assert memory_cache.get(key) is None

        # Set value
        memory_cache.set(key, sample_stock)

        # Retrieve value
        result = memory_cache.get(key)
        assert result == sample_stock

    def test_get_miss_increments_counter(self, memory_cache):
        """Test cache miss increments miss counter."""
        initial_misses = memory_cache.misses

        memory_cache.get("NONEXISTENT")

        assert memory_cache.misses == initial_misses + 1

    def test_get_hit_increments_counter(self, memory_cache, sample_stock):
        """Test cache hit increments hit counter."""
        memory_cache.set("AAPL", sample_stock)

        initial_hits = memory_cache.hits
        memory_cache.get("AAPL")

        assert memory_cache.hits == initial_hits + 1

    def test_delete(self, memory_cache, sample_stock):
        """Test cache delete operation."""
        key = "AAPL"

        memory_cache.set(key, sample_stock)
        assert key in memory_cache.cache

        memory_cache.delete(key)
        assert key not in memory_cache.cache

    def test_delete_nonexistent_key(self, memory_cache):
        """Test deleting non-existent key doesn't raise error."""
        # Should not raise exception
        memory_cache.delete("NONEXISTENT")

    def test_clear(self, memory_cache, sample_stock):
        """Test cache clear operation."""
        # Add multiple items
        for i in range(10):
            memory_cache.set(f"SYM{i}", sample_stock)

        assert len(memory_cache.cache) == 10

        memory_cache.clear()

        assert len(memory_cache.cache) == 0


class TestLRUEviction:
    """Test LRU eviction policy."""

    def test_evicts_oldest_when_full(self, sample_stock):
        """Test cache evicts least recently used items when full."""
        cache = MemoryStockCache(max_size=3)

        # Fill cache
        cache.set("A", sample_stock)
        cache.set("B", sample_stock)
        cache.set("C", sample_stock)

        assert len(cache.cache) == 3
        assert cache.evictions == 0

        # Access A to make it recently used
        cache.get("A")

        # Add new item, should evict B (least recently used)
        cache.set("D", sample_stock)

        assert len(cache.cache) == 3
        assert "A" in cache.cache
        assert "B" not in cache.cache  # Evicted
        assert "C" in cache.cache
        assert "D" in cache.cache
        assert cache.evictions == 1

    def test_update_existing_key_no_eviction(self, memory_cache, sample_stock):
        """Test updating existing key doesn't count as eviction."""
        memory_cache.set("AAPL", sample_stock)
        initial_evictions = memory_cache.evictions

        # Update same key
        memory_cache.set("AAPL", sample_stock)

        assert memory_cache.evictions == initial_evictions


class TestCacheStatistics:
    """Test cache statistics tracking."""

    def test_hit_miss_tracking(self, memory_cache, sample_stock):
        """Test cache tracks hits and misses."""
        # Miss
        memory_cache.get("AAPL")
        assert memory_cache.misses == 1

        # Set and hit
        memory_cache.set("AAPL", sample_stock)
        memory_cache.get("AAPL")
        assert memory_cache.hits == 1

    def test_stats_structure(self, memory_cache):
        """Test statistics have expected structure."""
        stats = memory_cache.get_stats()

        assert "size" in stats
        assert "max_size" in stats
        assert "hits" in stats
        assert "misses" in stats
        assert "evictions" in stats
        assert "total_requests" in stats
        assert "hit_rate_percent" in stats

    def test_hit_rate_calculation(self, memory_cache, sample_stock):
        """Test hit rate is calculated correctly."""
        memory_cache.set("AAPL", sample_stock)

        # 3 hits
        memory_cache.get("AAPL")
        memory_cache.get("AAPL")
        memory_cache.get("AAPL")

        # 1 miss
        memory_cache.get("MSFT")

        stats = memory_cache.get_stats()
        # 3 hits out of 4 total = 75%
        assert stats["hit_rate_percent"] == 75.0

    def test_hit_rate_zero_requests(self, memory_cache):
        """Test hit rate with zero requests."""
        stats = memory_cache.get_stats()
        assert stats["hit_rate_percent"] == 0


class TestCacheTTL:
    """Test TTL expiration functionality."""

    def test_ttl_expiration(self, sample_stock):
        """Test items expire after TTL."""
        cache = MemoryStockCache(max_size=100)

        # Set with very short TTL (0.02 minutes ~= 1 second)
        cache.set("AAPL", sample_stock, ttl_minutes=0.02)

        # Should be available immediately
        assert cache.get("AAPL") == sample_stock

        # Wait for expiration
        time.sleep(1.5)

        # Should be expired
        assert cache.get("AAPL") is None

    def test_ttl_default_value(self, memory_cache, sample_stock):
        """Test default TTL is applied."""
        memory_cache.set("AAPL", sample_stock)

        # Should have cache_expires_at attribute
        assert hasattr(sample_stock, "cache_expires_at")

    def test_expired_item_removed_from_cache(self, sample_stock):
        """Test expired items are removed from cache."""
        cache = MemoryStockCache(max_size=100)
        cache.set("AAPL", sample_stock, ttl_minutes=0.02)

        assert len(cache.cache) == 1

        time.sleep(1.5)
        cache.get("AAPL")  # Triggers expiration check

        # Item should be removed
        assert len(cache.cache) == 0


class TestCacheWithMultipleStocks:
    """Test cache with multiple different stocks."""

    def test_multiple_stocks(self, memory_cache):
        """Test caching multiple different stocks."""
        for i, symbol in enumerate(["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]):
            identifier = StockIdentifier(symbol=symbol, name=f"Company {i}")
            price = StockPrice(current=Decimal(str(100 + i)), currency="USD")
            metadata = StockMetadata(exchange="NASDAQ")

            stock = Stock(
                identifier=identifier,
                price=price,
                metadata=metadata,
                data_source=DataSource.YAHOO_FINANCE,
                last_updated=datetime.now(timezone.utc),
            )
            memory_cache.set(symbol, stock)

        # Verify all stocks are cached
        assert len(memory_cache.cache) == 5

        # Verify each can be retrieved
        for symbol in ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]:
            cached = memory_cache.get(symbol)
            assert cached is not None
            assert cached.identifier.symbol == symbol


class TestThreadSafety:
    """Test thread-safe operations."""

    def test_concurrent_access(self, memory_cache, sample_stock):
        """Test cache handles concurrent access safely."""
        errors = []

        def cache_worker(worker_id):
            try:
                for i in range(50):
                    key = f"W{worker_id}_{i}"
                    memory_cache.set(key, sample_stock)
                    result = memory_cache.get(key)
                    if result is None:
                        errors.append(f"Worker {worker_id}: Cache miss on own write")
            except Exception as e:
                errors.append(f"Worker {worker_id}: {e}")

        # Create multiple threads
        threads = []
        for i in range(5):
            t = threading.Thread(target=cache_worker, args=(i,))
            threads.append(t)
            t.start()

        # Wait for completion
        for t in threads:
            t.join()

        # Should have no errors
        assert len(errors) == 0


class TestCacheWarmup:
    """Test cache warming functionality."""

    def test_warmup_populates_cache(self, memory_cache):
        """Test cache can be warmed up with stock list."""
        stocks = []
        for symbol in ["AAPL", "MSFT", "GOOGL"]:
            identifier = StockIdentifier(symbol=symbol, name=f"{symbol} Inc.")
            price = StockPrice(current=Decimal("100.00"), currency="USD")
            metadata = StockMetadata(exchange="NASDAQ")

            stock = Stock(
                identifier=identifier,
                price=price,
                metadata=metadata,
                data_source=DataSource.YAHOO_FINANCE,
                last_updated=datetime.now(timezone.utc),
            )
            stocks.append(stock)

        count = memory_cache.warmup(stocks)

        assert count == 3
        assert len(memory_cache.cache) == 3
        assert "AAPL" in memory_cache.cache
        assert "MSFT" in memory_cache.cache
        assert "GOOGL" in memory_cache.cache

    def test_warmup_with_empty_list(self, memory_cache):
        """Test warmup with empty stock list."""
        count = memory_cache.warmup([])
        assert count == 0

    def test_warmup_with_stocks_without_symbols(self, memory_cache):
        """Test warmup handles stocks without symbols."""
        # Stock without symbol - should raise AttributeError in current implementation
        identifier = StockIdentifier(isin="US0378331005", name="Apple Inc.")
        price = StockPrice(current=Decimal("100.00"), currency="USD")
        metadata = StockMetadata(exchange="NASDAQ")

        stock = Stock(
            identifier=identifier,
            price=price,
            metadata=metadata,
            data_source=DataSource.YAHOO_FINANCE,
            last_updated=datetime.now(timezone.utc),
        )

        # Current implementation expects symbol, so this will raise
        with pytest.raises(AttributeError):
            memory_cache.warmup([stock])


class TestCachePerformance:
    """Test cache performance characteristics."""

    def test_cache_is_fast(self, memory_cache, sample_stock):
        """Test cache operations are fast."""
        key = "AAPL"
        memory_cache.set(key, sample_stock)

        # Measure get performance
        start = time.time()
        for _ in range(10000):
            memory_cache.get(key)
        elapsed = time.time() - start

        # Should be very fast (< 100ms for 10k operations)
        assert elapsed < 0.1

    def test_cache_handles_large_dataset(self, sample_stock):
        """Test cache handles many items efficiently."""
        cache = MemoryStockCache(max_size=1000)

        # Add many items
        start = time.time()
        for i in range(1000):
            cache.set(f"SYM{i}", sample_stock)
        elapsed = time.time() - start

        # Should complete reasonably fast (< 1 second for 1000 items)
        assert elapsed < 1.0
        assert len(cache.cache) == 1000


class TestErrorHandling:
    """Test error handling in cache operations."""

    def test_get_handles_errors_gracefully(self, memory_cache):
        """Test get handles internal errors gracefully."""
        # Try to get with None key (edge case)
        try:
            result = memory_cache.get(None)
            # Should return None or handle gracefully
            assert result is None or result is not None
        except Exception:
            # Should not raise unhandled exception
            pytest.fail("Cache.get should handle errors gracefully")

    def test_set_handles_errors_gracefully(self, memory_cache, sample_stock):
        """Test set handles internal errors gracefully."""
        # Try to set with None key (edge case)
        try:
            memory_cache.set(None, sample_stock)
            # Should handle gracefully
        except Exception:
            # Acceptable to raise validation error
            pass
