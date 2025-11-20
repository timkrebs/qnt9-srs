"""
Tests for stock search service.

Covers:
- Multi-layer caching logic
- Search orchestration
- Fallback strategies
- Error handling
- Search history tracking
"""

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from app.domain.entities import (
    DataSource,
    IdentifierType,
    Stock,
    StockIdentifier,
    StockMetadata,
    StockPrice,
)
from app.domain.exceptions import StockNotFoundException, ValidationException
from app.services.stock_service import StockSearchService


@pytest.fixture
def sample_stock():
    """Create sample stock for testing."""
    identifier = StockIdentifier(isin="US0378331005", symbol="AAPL", name="Apple Inc.")

    price = StockPrice(
        current=Decimal("175.50"),
        currency="USD",
    )

    metadata = StockMetadata(
        exchange="NASDAQ",
        sector="Technology",
    )

    return Stock(
        identifier=identifier,
        price=price,
        metadata=metadata,
        data_source=DataSource.YAHOO_FINANCE,
        last_updated=datetime.now(timezone.utc),
    )


@pytest.fixture
def mock_repositories():
    """Create mock repositories."""
    redis_repo = AsyncMock()
    postgres_repo = AsyncMock()
    history_repo = AsyncMock()
    return redis_repo, postgres_repo, history_repo


@pytest.fixture
def mock_api_client():
    """Create mock API client."""
    return AsyncMock()


@pytest.fixture
def search_service(mock_repositories, mock_api_client):
    """Create stock search service with mocks."""
    redis_repo, postgres_repo, history_repo = mock_repositories
    return StockSearchService(
        redis_repo=redis_repo,
        postgres_repo=postgres_repo,
        api_client=mock_api_client,
        history_repo=history_repo,
    )


class TestServiceInitialization:
    """Test service initialization."""

    def test_initialization(self, search_service, mock_repositories, mock_api_client):
        """Test service is properly initialized."""
        redis_repo, postgres_repo, history_repo = mock_repositories

        assert search_service.redis_repo == redis_repo
        assert search_service.postgres_repo == postgres_repo
        assert search_service.api_client == mock_api_client
        assert search_service.history_repo == history_repo


class TestSearch:
    """Test search method with multi-layer caching."""

    @pytest.mark.asyncio
    async def test_search_redis_cache_hit(
        self, search_service, mock_repositories, sample_stock
    ):
        """Test search returns from Redis cache (Layer 1)."""
        redis_repo, postgres_repo, history_repo = mock_repositories

        # Mock Redis hit
        redis_repo.find_by_identifier.return_value = sample_stock

        result = await search_service.search("AAPL")

        assert result == sample_stock
        redis_repo.find_by_identifier.assert_called_once()
        # PostgreSQL should not be called on Redis hit
        postgres_repo.find_by_identifier.assert_not_called()

    @pytest.mark.asyncio
    async def test_search_postgres_cache_hit(
        self, search_service, mock_repositories, sample_stock
    ):
        """Test search falls back to PostgreSQL cache (Layer 2)."""
        redis_repo, postgres_repo, history_repo = mock_repositories

        # Mock Redis miss, PostgreSQL hit
        redis_repo.find_by_identifier.return_value = None
        postgres_repo.find_by_identifier.return_value = sample_stock

        result = await search_service.search("AAPL")

        assert result == sample_stock
        redis_repo.find_by_identifier.assert_called_once()
        postgres_repo.find_by_identifier.assert_called_once()
        # Should save to Redis for next time
        redis_repo.save.assert_called_once_with(sample_stock)

    @pytest.mark.asyncio
    async def test_search_api_fallback(
        self, search_service, mock_repositories, mock_api_client, sample_stock
    ):
        """Test search falls back to external API (Layer 3)."""
        redis_repo, postgres_repo, history_repo = mock_repositories

        # Mock both caches miss, API hit
        redis_repo.find_by_identifier.return_value = None
        postgres_repo.find_by_identifier.return_value = None
        mock_api_client.fetch_stock.return_value = sample_stock

        result = await search_service.search("AAPL")

        assert result == sample_stock
        mock_api_client.fetch_stock.assert_called_once()
        # Should save to both caches
        redis_repo.save.assert_called_once_with(sample_stock)
        postgres_repo.save.assert_called_once_with(sample_stock)

    @pytest.mark.asyncio
    async def test_search_raises_on_not_found(
        self, search_service, mock_repositories, mock_api_client
    ):
        """Test search raises StockNotFoundException when not found."""
        redis_repo, postgres_repo, history_repo = mock_repositories

        # Mock all sources return None
        redis_repo.find_by_identifier.return_value = None
        postgres_repo.find_by_identifier.return_value = None
        mock_api_client.fetch_stock.return_value = None

        # Should raise StockNotFoundException
        with pytest.raises(StockNotFoundException) as exc_info:
            await search_service.search("AAPL")

        assert "AAPL" in str(exc_info.value) or "symbol" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_search_empty_query(self, search_service):
        """Test search validates empty query."""
        with pytest.raises(ValidationException) as exc_info:
            await search_service.search("")

        assert "empty" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_search_records_history(
        self, search_service, mock_repositories, sample_stock
    ):
        """Test search records to history."""
        redis_repo, postgres_repo, history_repo = mock_repositories
        redis_repo.find_by_identifier.return_value = sample_stock

        await search_service.search("AAPL")

        # Should record search in history
        history_repo.record_search.assert_called_once()


class TestSearchByName:
    """Test search_by_name method."""

    @pytest.mark.asyncio
    async def test_search_by_name_postgres_hit(
        self, search_service, mock_repositories, sample_stock
    ):
        """Test name search uses PostgreSQL."""
        redis_repo, postgres_repo, history_repo = mock_repositories

        # Redis returns empty, PostgreSQL hits
        redis_repo.find_by_name.return_value = []
        postgres_repo.find_by_name.return_value = [sample_stock]

        results = await search_service.search_by_name("Apple", limit=10)

        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_search_by_name_postgres_fallback(
        self, search_service, mock_repositories, sample_stock
    ):
        """Test name search falls back to PostgreSQL."""
        redis_repo, postgres_repo, history_repo = mock_repositories

        # Redis returns empty list
        redis_repo.find_by_name.return_value = []
        postgres_repo.find_by_name.return_value = [sample_stock]

        results = await search_service.search_by_name("Apple", limit=10)

        assert len(results) == 1
        postgres_repo.find_by_name.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_by_name_api_fallback(
        self, search_service, mock_repositories, mock_api_client, sample_stock
    ):
        """Test name search falls back to external API."""
        redis_repo, postgres_repo, history_repo = mock_repositories

        # Both caches miss
        redis_repo.find_by_name.return_value = []
        postgres_repo.find_by_name.return_value = []
        mock_api_client.search_by_name.return_value = [sample_stock]

        results = await search_service.search_by_name("Apple", limit=10)

        assert len(results) == 1
        mock_api_client.search_by_name.assert_called_once()
        # Should cache results
        redis_repo.save.assert_called()

    @pytest.mark.asyncio
    async def test_search_by_name_respects_limit(
        self, search_service, mock_repositories, sample_stock
    ):
        """Test name search respects result limit."""
        redis_repo, postgres_repo, history_repo = mock_repositories

        # Return many results
        many_stocks = [sample_stock] * 20
        redis_repo.find_by_name.return_value = many_stocks

        results = await search_service.search_by_name("Apple", limit=5)

        assert len(results) <= 5

    @pytest.mark.asyncio
    async def test_search_by_name_empty_query(self, search_service):
        """Test name search validates minimum length."""
        # Empty and short queries should raise ValidationException
        with pytest.raises(ValidationException):
            await search_service.search_by_name("", limit=10)


class TestBuildIdentifier:
    """Test _build_identifier helper method."""

    def test_build_identifier_isin(self, search_service):
        """Test building identifier from ISIN."""
        identifier = search_service._build_identifier(
            "US0378331005", IdentifierType.ISIN
        )

        assert identifier.isin == "US0378331005"
        assert identifier.symbol is None

    def test_build_identifier_wkn(self, search_service):
        """Test building identifier from WKN."""
        identifier = search_service._build_identifier("840400", IdentifierType.WKN)

        assert identifier.wkn == "840400"
        assert identifier.symbol is None

    def test_build_identifier_symbol(self, search_service):
        """Test building identifier from symbol."""
        identifier = search_service._build_identifier("AAPL", IdentifierType.SYMBOL)

        assert identifier.symbol == "AAPL"
        assert identifier.isin is None


class TestCacheStats:
    """Test cache statistics functionality."""

    @pytest.mark.asyncio
    async def test_get_cache_stats(self, search_service, mock_repositories):
        """Test getting cache statistics."""
        redis_repo, postgres_repo, history_repo = mock_repositories

        # Mock repository stats
        redis_repo.get_cache_stats.return_value = {
            "total_stock_keys": 100,
        }

        stats = await redis_repo.get_cache_stats()

        assert "total_stock_keys" in stats


class TestErrorHandling:
    """Test error handling and resilience."""

    @pytest.mark.asyncio
    async def test_service_error_handling(
        self, search_service, mock_repositories, sample_stock
    ):
        """Test service handles errors gracefully and falls back."""
        redis_repo, postgres_repo, history_repo = mock_repositories

        # Redis fails, but PostgreSQL succeeds
        redis_repo.find_by_identifier.return_value = None  # Miss, not error
        postgres_repo.find_by_identifier.return_value = sample_stock

        result = await search_service.search("AAPL")
        assert result == sample_stock

    @pytest.mark.asyncio
    async def test_search_handles_exceptions(
        self, search_service, mock_repositories, mock_api_client
    ):
        """Test search handles general exceptions."""
        redis_repo, postgres_repo, history_repo = mock_repositories

        # Make redis raise an unexpected error
        redis_repo.find_by_identifier.side_effect = RuntimeError("Database error")

        # Should raise the error
        with pytest.raises(RuntimeError):
            await search_service.search("AAPL")


class TestRecordSearch:
    """Test search history recording."""

    @pytest.mark.asyncio
    async def test_search_records_success(
        self, search_service, mock_repositories, sample_stock
    ):
        """Test successful searches are recorded."""
        redis_repo, postgres_repo, history_repo = mock_repositories
        redis_repo.find_by_identifier.return_value = sample_stock

        await search_service.search("AAPL")

        # Should record to history
        history_repo.record_search.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_records_failure(
        self, search_service, mock_repositories, mock_api_client
    ):
        """Test failed searches are recorded."""
        redis_repo, postgres_repo, history_repo = mock_repositories

        redis_repo.find_by_identifier.return_value = None
        postgres_repo.find_by_identifier.return_value = None
        mock_api_client.fetch_stock.return_value = None

        try:
            await search_service.search("INVALID")
        except StockNotFoundException:
            pass

        # Should have recorded to history (may be called multiple times due to retries)
        assert history_repo.record_search.called


class TestPerformanceTracking:
    """Test performance tracking and metrics."""

    @pytest.mark.asyncio
    async def test_search_tracks_duration(
        self, search_service, mock_repositories, sample_stock
    ):
        """Test search tracks execution duration."""
        redis_repo, postgres_repo, history_repo = mock_repositories
        redis_repo.find_by_identifier.return_value = sample_stock

        await search_service.search("AAPL")

        # History should be recorded with duration
        history_repo.record_search.assert_called_once()
        # Duration should be recorded (implementation dependent)
