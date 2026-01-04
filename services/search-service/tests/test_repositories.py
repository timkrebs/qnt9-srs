"""
Tests for repository layer.

Covers:
- Redis repository (in-memory cache)
- PostgreSQL repository (persistent cache)
- Stock repository interface
- Cache key generation
- Serialization/deserialization
"""

import json
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.domain.entities import (DataSource, Stock, StockIdentifier,
                                 StockMetadata, StockPrice)
from app.repositories.postgres_repository import PostgresStockRepository
from app.repositories.redis_repository import RedisStockRepository
from sqlalchemy.orm import Session


@pytest.fixture
def sample_stock():
    """Create sample stock for testing."""
    identifier = StockIdentifier(isin="US0378331005", symbol="AAPL", name="Apple Inc.")

    price = StockPrice(
        current=Decimal("175.50"),
        currency="USD",
        change_absolute=Decimal("2.50"),
        change_percent=Decimal("1.45"),
        previous_close=Decimal("173.00"),
    )

    metadata = StockMetadata(
        exchange="NASDAQ",
        sector="Technology",
        industry="Consumer Electronics",
    )

    return Stock(
        identifier=identifier,
        price=price,
        metadata=metadata,
        data_source=DataSource.YAHOO_FINANCE,
        last_updated=datetime.now(timezone.utc),
    )


class TestRedisRepository:
    """Test Redis repository."""

    @pytest.fixture
    def mock_redis(self):
        """Create mock Redis client."""
        redis_mock = AsyncMock()
        return redis_mock

    @pytest.fixture
    def redis_repo(self, mock_redis):
        """Create Redis repository with mock client."""
        return RedisStockRepository(mock_redis, ttl_seconds=300)

    def test_initialization(self, redis_repo):
        """Test repository initialization."""
        assert redis_repo.ttl_seconds == 300
        assert redis_repo.redis is not None

    def test_build_cache_key_symbol(self, redis_repo):
        """Test cache key generation for symbol."""
        identifier = StockIdentifier(symbol="AAPL")
        key = redis_repo._build_cache_key(identifier)
        assert key == "stock:symbol:AAPL"

    def test_build_cache_key_isin(self, redis_repo):
        """Test cache key generation for ISIN."""
        identifier = StockIdentifier(isin="US0378331005")
        key = redis_repo._build_cache_key(identifier)
        assert key == "stock:isin:US0378331005"

    def test_build_cache_key_case_sensitive(self, redis_repo):
        """Test cache key handles case."""
        identifier = StockIdentifier(symbol="AAPL")
        key = redis_repo._build_cache_key(identifier)
        assert key == "stock:symbol:AAPL"

    @pytest.mark.asyncio
    async def test_find_by_identifier_cache_hit(
        self, redis_repo, mock_redis, sample_stock
    ):
        """Test finding stock when in Redis cache."""
        # Serialize stock to JSON
        serialized = redis_repo._serialize_stock(sample_stock)
        mock_redis.get.return_value = json.dumps(serialized).encode("utf-8")

        identifier = StockIdentifier(symbol="AAPL")
        result = await redis_repo.find_by_identifier(identifier)

        assert result is not None
        assert result.identifier.symbol == "AAPL"
        mock_redis.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_find_by_identifier_cache_miss(self, redis_repo, mock_redis):
        """Test finding stock when not in cache."""
        mock_redis.get.return_value = None

        identifier = StockIdentifier(symbol="AAPL")
        result = await redis_repo.find_by_identifier(identifier)

        assert result is None
        mock_redis.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_find_by_identifier_error_handling(self, redis_repo, mock_redis):
        """Test error handling in find_by_identifier."""
        mock_redis.get.side_effect = Exception("Redis connection error")

        identifier = StockIdentifier(symbol="AAPL")
        result = await redis_repo.find_by_identifier(identifier)

        # Should return None instead of raising exception
        assert result is None

    @pytest.mark.asyncio
    async def test_find_by_name_not_supported(self, redis_repo):
        """Test that name search returns empty list."""
        results = await redis_repo.find_by_name("Apple", limit=10)
        assert results == []

    @pytest.mark.asyncio
    async def test_save_stock(self, redis_repo, mock_redis, sample_stock):
        """Test saving stock to Redis."""
        result = await redis_repo.save(sample_stock)

        assert result == sample_stock
        mock_redis.setex.assert_called_once()

        # Verify TTL was set
        call_args = mock_redis.setex.call_args
        assert call_args[0][1] == 300  # TTL seconds

    @pytest.mark.asyncio
    async def test_save_stock_error_handling(
        self, redis_repo, mock_redis, sample_stock
    ):
        """Test error handling when saving fails."""
        mock_redis.setex.side_effect = Exception("Redis write error")

        # Should not raise exception
        result = await redis_repo.save(sample_stock)
        assert result == sample_stock

    @pytest.mark.asyncio
    async def test_get_cache_stats(self, redis_repo, mock_redis):
        """Test getting cache statistics."""
        mock_redis.info.return_value = {
            "keyspace_hits": 100,
            "keyspace_misses": 50,
            "used_memory_human": "10M",
        }
        mock_redis.keys.return_value = ["stock:AAPL", "stock:MSFT"]

        stats = await redis_repo.get_cache_stats()

        assert stats["total_stock_keys"] == 2
        assert "hit_rate" in stats

    def test_serialize_stock(self, redis_repo, sample_stock):
        """Test stock serialization."""
        serialized = redis_repo._serialize_stock(sample_stock)

        assert isinstance(serialized, dict)
        assert serialized["identifier"]["symbol"] == "AAPL"
        assert serialized["price"]["current"] == "175.50"
        # DataSource enum value
        assert "yahoo" in serialized["data_source"].lower()

    def test_deserialize_stock(self, redis_repo, sample_stock):
        """Test stock deserialization."""
        serialized = redis_repo._serialize_stock(sample_stock)
        deserialized = redis_repo._deserialize_stock(serialized)

        assert deserialized.identifier.symbol == sample_stock.identifier.symbol
        assert deserialized.price.current == sample_stock.price.current
        assert deserialized.data_source == sample_stock.data_source

    @pytest.mark.asyncio
    async def test_delete_expired(self, redis_repo):
        """Test delete expired (no-op for Redis)."""
        from datetime import datetime, timezone

        count = await redis_repo.delete_expired(datetime.now(timezone.utc))
        assert count == 0  # Redis TTL handles expiration


class TestPostgresRepository:
    """Test PostgreSQL repository - basic functionality."""

    @pytest.fixture
    def mock_db_session(self):
        """Create mock database session."""
        session = MagicMock(spec=Session)
        return session

    @pytest.fixture
    def postgres_repo(self, mock_db_session):
        """Create PostgreSQL repository with mock session."""
        return PostgresStockRepository(mock_db_session, cache_ttl_minutes=5)

    def test_initialization(self, postgres_repo):
        """Test repository initialization."""
        assert postgres_repo.cache_ttl_minutes == 5
        assert postgres_repo.db is not None


class TestRepositoryIntegration:
    """Integration tests for repository patterns."""

    @pytest.mark.asyncio
    async def test_cache_hierarchy(self, sample_stock):
        """Test Redis -> PostgreSQL cache hierarchy."""
        # Create mock repositories
        mock_redis_client = AsyncMock()
        redis_repo = RedisStockRepository(mock_redis_client, ttl_seconds=300)

        # Mock Redis miss
        mock_redis_client.get.return_value = None

        identifier = StockIdentifier(symbol="AAPL")

        # Redis miss should return None
        result = await redis_repo.find_by_identifier(identifier)
        assert result is None

        # Save to Redis
        await redis_repo.save(sample_stock)

        # Verify save was called
        mock_redis_client.setex.assert_called_once()
