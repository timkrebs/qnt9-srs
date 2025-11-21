"""
Tests for Phase 2: Cache Warmer

Comprehensive tests for cache warming functionality.
"""

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, Mock, patch

import pytest

from app.cache.cache_warmer import CacheWarmer, warmup_cache_on_startup
from app.cache.memory_cache import MemoryStockCache
from app.domain.entities import Stock
from app.models import StockCache, StockSearchIndex


@pytest.fixture
def mock_db():
    """Create mock database session."""
    return MagicMock()


@pytest.fixture
def mock_memory_cache():
    """Create mock memory cache."""
    cache = MagicMock(spec=MemoryStockCache)
    cache.set = MagicMock()
    cache.get_stats = MagicMock(
        return_value={"size": 0, "hits": 0, "misses": 0, "hit_rate_percent": 0.0}
    )
    return cache


@pytest.fixture
def cache_warmer(mock_db, mock_memory_cache):
    """Create cache warmer instance."""
    return CacheWarmer(mock_db, mock_memory_cache)


@pytest.fixture
def sample_stock_index():
    """Create sample stock search index."""
    stock_index = MagicMock(spec=StockSearchIndex)
    stock_index.symbol = "AAPL"
    stock_index.popularity_score = 100.0
    return stock_index


@pytest.fixture
def sample_stock_cache():
    """Create sample stock cache model."""
    stock_cache = MagicMock(spec=StockCache)
    stock_cache.symbol = "AAPL"
    stock_cache.isin = "US0378331005"
    stock_cache.wkn = "865985"
    stock_cache.name = "Apple Inc."
    stock_cache.exchange = "NASDAQ"
    stock_cache.current_price = Decimal("175.50")
    stock_cache.currency = "USD"
    stock_cache.market_cap = 2800000000000
    stock_cache.sector = "Technology"
    stock_cache.industry = "Consumer Electronics"
    stock_cache.data_source = "yahoo"
    stock_cache.created_at = datetime.now(timezone.utc)
    stock_cache.is_expired = MagicMock(return_value=False)
    return stock_cache


class TestCacheWarmerInitialization:
    """Test cache warmer initialization."""

    def test_initialization(self, mock_db, mock_memory_cache):
        """Test cache warmer initializes correctly."""
        warmer = CacheWarmer(mock_db, mock_memory_cache)

        assert warmer.db == mock_db
        assert warmer.memory_cache == mock_memory_cache


class TestWarmupFromPopularity:
    """Test warmup from popularity scores."""

    def test_warmup_basic(
        self, cache_warmer, mock_db, mock_memory_cache, sample_stock_index, sample_stock_cache
    ):
        """Test basic warmup functionality."""
        # Mock database queries
        mock_query = MagicMock()
        mock_query.order_by.return_value.limit.return_value.all.return_value = [sample_stock_index]

        mock_stock_query = MagicMock()
        mock_stock_query.filter.return_value.order_by.return_value.first.return_value = (
            sample_stock_cache
        )

        mock_db.query.side_effect = [mock_query, mock_stock_query]

        # Execute warmup
        count = cache_warmer.warmup(max_stocks=10)

        # Verify results
        assert count == 1
        assert mock_memory_cache.set.call_count >= 1

    def test_warmup_multiple_stocks(self, cache_warmer, mock_db, mock_memory_cache):
        """Test warming up multiple stocks."""
        # Create multiple stock indices
        stock_indices = []
        isin_map = {"AAPL": "US0378331005", "MSFT": "US5949181045", "GOOGL": "US02079K1079"}
        for symbol in ["AAPL", "MSFT", "GOOGL"]:
            index = MagicMock(spec=StockSearchIndex)
            index.symbol = symbol
            index.popularity_score = 100.0
            stock_indices.append(index)

        # Mock queries
        mock_query = MagicMock()
        mock_query.order_by.return_value.limit.return_value.all.return_value = stock_indices

        def create_stock_cache(symbol):
            cache = MagicMock(spec=StockCache)
            cache.symbol = symbol
            cache.isin = isin_map[symbol]
            cache.wkn = None
            cache.name = f"{symbol} Inc."
            cache.exchange = "NASDAQ"
            cache.current_price = Decimal("100.00")
            cache.currency = "USD"
            cache.market_cap = None
            cache.sector = "Technology"
            cache.industry = None
            cache.data_source = "yahoo"
            cache.is_expired = MagicMock(return_value=False)
            return cache

        stock_caches = [create_stock_cache(idx.symbol) for idx in stock_indices]

        # Set up query side effects
        call_count = [0]

        def query_side_effect(model):
            if model == StockSearchIndex:
                return mock_query
            else:  # StockCache
                idx = call_count[0]
                call_count[0] += 1
                mock_stock_query = MagicMock()
                if idx < len(stock_caches):
                    mock_stock_query.filter.return_value.order_by.return_value.first.return_value = stock_caches[
                        idx
                    ]
                else:
                    mock_stock_query.filter.return_value.order_by.return_value.first.return_value = (
                        None
                    )
                return mock_stock_query

        mock_db.query.side_effect = query_side_effect

        count = cache_warmer.warmup(max_stocks=10)

        assert count == 3
        # Should have cached each stock with its symbol and ISIN
        assert mock_memory_cache.set.call_count >= 3

    def test_warmup_skips_expired_stocks(
        self, cache_warmer, mock_db, mock_memory_cache, sample_stock_index, sample_stock_cache
    ):
        """Test warmup skips expired stocks."""
        # Mark stock as expired
        sample_stock_cache.is_expired = MagicMock(return_value=True)

        mock_query = MagicMock()
        mock_query.order_by.return_value.limit.return_value.all.return_value = [sample_stock_index]

        mock_stock_query = MagicMock()
        mock_stock_query.filter.return_value.order_by.return_value.first.return_value = (
            sample_stock_cache
        )

        mock_db.query.side_effect = [mock_query, mock_stock_query]

        count = cache_warmer.warmup(max_stocks=10)

        # Should skip expired stock
        assert count == 0
        assert mock_memory_cache.set.call_count == 0

    def test_warmup_skips_missing_stocks(
        self, cache_warmer, mock_db, mock_memory_cache, sample_stock_index
    ):
        """Test warmup skips stocks not found in cache."""
        mock_query = MagicMock()
        mock_query.order_by.return_value.limit.return_value.all.return_value = [sample_stock_index]

        mock_stock_query = MagicMock()
        mock_stock_query.filter.return_value.order_by.return_value.first.return_value = None

        mock_db.query.side_effect = [mock_query, mock_stock_query]

        count = cache_warmer.warmup(max_stocks=10)

        assert count == 0

    def test_warmup_handles_errors_gracefully(self, cache_warmer, mock_db, mock_memory_cache):
        """Test warmup handles database errors gracefully."""
        # Simulate database error
        mock_db.query.side_effect = Exception("Database error")

        count = cache_warmer.warmup(max_stocks=10)

        # Should return 0 on error
        assert count == 0

    def test_warmup_caches_with_multiple_keys(
        self, cache_warmer, mock_db, mock_memory_cache, sample_stock_index, sample_stock_cache
    ):
        """Test warmup caches stock with symbol, ISIN, and WKN."""
        mock_query = MagicMock()
        mock_query.order_by.return_value.limit.return_value.all.return_value = [sample_stock_index]

        mock_stock_query = MagicMock()
        mock_stock_query.filter.return_value.order_by.return_value.first.return_value = (
            sample_stock_cache
        )

        mock_db.query.side_effect = [mock_query, mock_stock_query]

        count = cache_warmer.warmup(max_stocks=10)

        # Should cache with symbol, ISIN, and WKN
        assert count == 1
        # 3 keys: symbol, isin, wkn
        assert mock_memory_cache.set.call_count == 3


class TestWarmupFromSearchHistory:
    """Test warmup from search history."""

    def test_warmup_from_history_basic(
        self, cache_warmer, mock_db, mock_memory_cache, sample_stock_cache
    ):
        """Test basic warmup from search history."""
        # Mock search history query
        mock_result = MagicMock()
        mock_result.__iter__ = Mock(return_value=iter([("AAPL", 100)]))
        mock_db.execute.return_value = mock_result

        # Mock stock cache query
        mock_stock_query = MagicMock()
        mock_stock_query.filter.return_value.order_by.return_value.first.return_value = (
            sample_stock_cache
        )
        mock_db.query.return_value = mock_stock_query

        count = cache_warmer.warmup_from_search_history(max_stocks=10)

        assert count == 1
        assert mock_memory_cache.set.call_count >= 1

    def test_warmup_from_history_multiple(self, cache_warmer, mock_db, mock_memory_cache):
        """Test warmup from history with multiple searches."""
        # Mock search history with multiple queries
        searches = [("AAPL", 150), ("MSFT", 100), ("GOOGL", 75)]
        mock_result = MagicMock()
        mock_result.__iter__ = Mock(return_value=iter(searches))
        mock_db.execute.return_value = mock_result

        # Mock stock cache queries with valid ISINs
        isin_map = {"AAPL": "US0378331005", "MSFT": "US5949181045", "GOOGL": "US02079K1079"}

        def create_stock(symbol):
            stock = MagicMock(spec=StockCache)
            stock.symbol = symbol
            stock.isin = isin_map[symbol]
            stock.wkn = None
            stock.name = f"{symbol} Inc."
            stock.exchange = "NASDAQ"
            stock.current_price = Decimal("100.00")
            stock.currency = "USD"
            stock.market_cap = None
            stock.sector = "Technology"
            stock.industry = None
            stock.data_source = "yahoo"
            stock.is_expired = MagicMock(return_value=False)
            return stock

        call_count = [0]

        def query_side_effect():
            idx = call_count[0]
            call_count[0] += 1
            mock_stock_query = MagicMock()
            if idx < len(searches):
                stock = create_stock(searches[idx][0])
                mock_stock_query.filter.return_value.order_by.return_value.first.return_value = (
                    stock
                )
            else:
                mock_stock_query.filter.return_value.order_by.return_value.first.return_value = None
            return mock_stock_query

        mock_db.query.side_effect = lambda model: query_side_effect()

        count = cache_warmer.warmup_from_search_history(max_stocks=10)

        assert count == 3

    def test_warmup_from_history_skips_expired(
        self, cache_warmer, mock_db, mock_memory_cache, sample_stock_cache
    ):
        """Test warmup from history skips expired stocks."""
        sample_stock_cache.is_expired = MagicMock(return_value=True)

        mock_result = MagicMock()
        mock_result.__iter__ = Mock(return_value=iter([("AAPL", 100)]))
        mock_db.execute.return_value = mock_result

        mock_stock_query = MagicMock()
        mock_stock_query.filter.return_value.order_by.return_value.first.return_value = (
            sample_stock_cache
        )
        mock_db.query.return_value = mock_stock_query

        count = cache_warmer.warmup_from_search_history(max_stocks=10)

        assert count == 0

    def test_warmup_from_history_handles_errors(self, cache_warmer, mock_db, mock_memory_cache):
        """Test warmup from history handles errors gracefully."""
        mock_db.execute.side_effect = Exception("Database error")

        count = cache_warmer.warmup_from_search_history(max_stocks=10)

        assert count == 0


class TestConvertToStockData:
    """Test conversion from StockCache to StockData."""

    def test_convert_complete_data(self, cache_warmer, sample_stock_cache):
        """Test converting stock cache with complete data."""
        stock_data = cache_warmer._convert_to_stock_data(sample_stock_cache)

        assert isinstance(stock_data, Stock)
        assert stock_data.identifier.symbol == "AAPL"
        assert stock_data.identifier.isin == "US0378331005"
        assert stock_data.identifier.wkn == "865985"
        assert stock_data.identifier.name == "Apple Inc."
        assert stock_data.price.current == Decimal("175.50")
        assert stock_data.price.currency == "USD"
        assert stock_data.metadata.sector == "Technology"

    def test_convert_minimal_data(self, cache_warmer):
        """Test converting stock cache with minimal data."""
        stock_cache = MagicMock(spec=StockCache)
        stock_cache.symbol = "AAPL"
        stock_cache.isin = "US0378331005"  # Valid ISIN
        stock_cache.wkn = None
        stock_cache.name = "Apple Inc."
        stock_cache.exchange = None
        stock_cache.current_price = Decimal("1.00")  # Must be positive, not None
        stock_cache.currency = "USD"
        stock_cache.market_cap = None
        stock_cache.sector = None
        stock_cache.industry = None
        stock_cache.data_source = "yahoo"
        stock_cache.created_at = datetime.now(timezone.utc)

        stock_data = cache_warmer._convert_to_stock_data(stock_cache)

        assert isinstance(stock_data, Stock)
        assert stock_data.identifier.symbol == "AAPL"
        assert stock_data.metadata.exchange == "Unknown"
        assert stock_data.price.current == Decimal("1.00")
        assert stock_data.price.currency == "USD"


class TestWarmupOnStartup:
    """Test warmup on application startup."""

    @patch("app.cache.cache_warmer.get_db")
    @patch("app.cache.memory_cache.get_memory_cache")
    def test_warmup_on_startup_success(self, mock_get_cache, mock_get_db):
        """Test successful warmup on startup."""
        # Mock database session
        mock_db_session = MagicMock()
        mock_get_db.return_value = iter([mock_db_session])

        # Mock memory cache
        mock_cache = MagicMock()
        mock_cache.get_stats.return_value = {"size": 100}
        mock_get_cache.return_value = mock_cache

        # Mock warmer methods
        with patch.object(CacheWarmer, "warmup", return_value=80):
            with patch.object(CacheWarmer, "warmup_from_search_history", return_value=20):
                # Should not raise exception
                warmup_cache_on_startup(max_stocks=1000)

        # Verify db session was closed
        mock_db_session.close.assert_called_once()

    @patch("app.cache.cache_warmer.get_db")
    @patch("app.cache.memory_cache.get_memory_cache")
    def test_warmup_on_startup_handles_errors(self, mock_get_cache, mock_get_db):
        """Test warmup on startup handles errors gracefully."""
        mock_get_db.side_effect = Exception("Database connection failed")

        # Should not raise exception
        try:
            warmup_cache_on_startup(max_stocks=1000)
        except Exception:
            pytest.fail("warmup_cache_on_startup should handle errors gracefully")


class TestCacheWarmerIntegration:
    """Integration tests for cache warmer."""

    def test_warmup_respects_max_stocks_limit(self, cache_warmer, mock_db, mock_memory_cache):
        """Test warmup respects max_stocks parameter."""
        # Create many stock indices
        stock_indices = []
        for i in range(100):
            index = MagicMock(spec=StockSearchIndex)
            index.symbol = f"SYM{i}"
            index.popularity_score = 100.0 - i
            stock_indices.append(index)

        mock_query = MagicMock()
        # Verify limit is called with correct value
        mock_limit = MagicMock()
        mock_limit.all.return_value = stock_indices[:10]
        mock_query.order_by.return_value.limit.return_value = mock_limit

        mock_db.query.return_value = mock_query

        cache_warmer.warmup(max_stocks=10)

        # Verify limit was called with 10
        mock_query.order_by.return_value.limit.assert_called_once_with(10)

    def test_warmup_orders_by_popularity(self, cache_warmer, mock_db, mock_memory_cache):
        """Test warmup orders stocks by popularity score."""
        mock_query = MagicMock()
        mock_query.order_by.return_value.limit.return_value.all.return_value = []

        mock_db.query.return_value = mock_query

        cache_warmer.warmup(max_stocks=10)

        # Verify order_by was called (checking it was called, actual order handled by SQLAlchemy)
        assert mock_query.order_by.called
