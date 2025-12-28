"""
Redis implementation of stock repository.

Implements in-memory caching layer for fast stock data retrieval.
"""

import json
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional

import redis.asyncio as redis

from ..domain.entities import (
    DataSource,
    Stock,
    StockIdentifier,
    StockMetadata,
    StockPrice,
)
from .stock_repository import IStockRepository

logger = logging.getLogger(__name__)


class RedisStockRepository(IStockRepository):
    """
    Redis implementation for fast in-memory stock caching.

    Provides Layer 1 caching with TTL-based expiration.
    """

    def __init__(self, redis_client: redis.Redis, ttl_seconds: int = 300):
        """
        Initialize Redis repository.

        Args:
            redis_client: Async Redis client
            ttl_seconds: Time-to-live for cache entries (default: 5 minutes)
        """
        self.redis = redis_client
        self.ttl_seconds = ttl_seconds

    def _build_cache_key(self, identifier: StockIdentifier) -> str:
        """
        Build normalized cache key.

        Args:
            identifier: Stock identifier

        Returns:
            Cache key in format: stock:{type}:{value}
        """
        id_type, value = identifier.get_primary_identifier()
        normalized_value = value.upper().strip()
        return f"stock:{id_type.value}:{normalized_value}"

    async def find_by_identifier(self, identifier: StockIdentifier) -> Optional[Stock]:
        """Find stock in Redis cache."""
        try:
            cache_key = self._build_cache_key(identifier)
            cached_data = await self.redis.get(cache_key)

            if cached_data:
                logger.info(f"Redis cache HIT: {cache_key}")
                data = json.loads(cached_data)
                return self._deserialize_stock(data)

            logger.debug(f"Redis cache MISS: {cache_key}")
            return None

        except Exception as e:
            logger.error(f"Error finding stock in Redis: {e}")
            # Don't raise exception - allow fallback to PostgreSQL
            return None

    async def find_by_name(self, name: str, limit: int = 10) -> List[Stock]:
        """
        Search by name in Redis.

        Note: Redis doesn't support efficient fuzzy search.
        This returns empty list - name search should use PostgreSQL.
        """
        logger.debug("Name search not supported in Redis, use PostgreSQL")
        return []

    async def save(self, stock: Stock) -> Stock:
        """Save stock to Redis with TTL."""
        try:
            cache_key = self._build_cache_key(stock.identifier)

            # Serialize stock to JSON
            data = self._serialize_stock(stock)

            # Save with TTL
            await self.redis.setex(cache_key, self.ttl_seconds, json.dumps(data))

            logger.info(f"Saved to Redis: {cache_key} (TTL: {self.ttl_seconds}s)")
            return stock

        except Exception as e:
            logger.error(f"Error saving stock to Redis: {e}")
            # Don't raise - caching failure shouldn't break the flow
            return stock

    async def delete_expired(self, before: datetime) -> int:
        """
        Delete expired entries.

        Note: Redis handles expiration automatically via TTL.
        This method is a no-op for Redis.
        """
        return 0

    async def get_cache_stats(self) -> dict:
        """Get Redis cache statistics."""
        try:
            info = await self.redis.info("stats")
            _ = await self.redis.info("keyspace")  # Reserved for future use

            # Count stock keys
            stock_keys = await self.redis.keys("stock:*")

            return {
                "total_stock_keys": len(stock_keys),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "hit_rate": self._calculate_hit_rate(info),
                "ttl_seconds": self.ttl_seconds,
                "memory_used": info.get("used_memory_human", "unknown"),
            }
        except Exception as e:
            logger.error(f"Error getting Redis stats: {e}")
            return {}

    def _calculate_hit_rate(self, info: dict) -> float:
        """Calculate cache hit rate percentage."""
        hits = info.get("keyspace_hits", 0)
        misses = info.get("keyspace_misses", 0)
        total = hits + misses

        if total == 0:
            return 0.0

        return round((hits / total) * 100, 2)

    def _serialize_stock(self, stock: Stock) -> dict:
        """Serialize stock entity to dict for JSON storage."""
        return {
            "identifier": {
                "isin": stock.identifier.isin,
                "wkn": stock.identifier.wkn,
                "symbol": stock.identifier.symbol,
                "name": stock.identifier.name,
            },
            "price": {
                "current": str(stock.price.current),
                "currency": stock.price.currency,
                "change_absolute": (
                    str(stock.price.change_absolute) if stock.price.change_absolute else None
                ),
                "change_percent": (
                    str(stock.price.change_percent) if stock.price.change_percent else None
                ),
                "previous_close": (
                    str(stock.price.previous_close) if stock.price.previous_close else None
                ),
                "open": str(stock.price.open_price) if stock.price.open_price else None,
                "day_high": str(stock.price.day_high) if stock.price.day_high else None,
                "day_low": str(stock.price.day_low) if stock.price.day_low else None,
                "week_52_high": str(stock.price.week_52_high) if stock.price.week_52_high else None,
                "week_52_low": str(stock.price.week_52_low) if stock.price.week_52_low else None,
                "volume": stock.price.volume,
                "avg_volume": stock.price.avg_volume,
            },
            "metadata": {
                "exchange": stock.metadata.exchange,
                "sector": stock.metadata.sector,
                "industry": stock.metadata.industry,
                "market_cap": str(stock.metadata.market_cap) if stock.metadata.market_cap else None,
                "pe_ratio": str(stock.metadata.pe_ratio) if stock.metadata.pe_ratio else None,
                "dividend_yield": (
                    str(stock.metadata.dividend_yield) if stock.metadata.dividend_yield else None
                ),
                "beta": str(stock.metadata.beta) if stock.metadata.beta else None,
            },
            "data_source": stock.data_source.value,
            "last_updated": stock.last_updated.isoformat(),
            "cached_at": datetime.now(timezone.utc).isoformat(),
        }

    def _deserialize_stock(self, data: dict) -> Stock:
        """Deserialize dict to stock entity."""
        identifier = StockIdentifier(
            isin=data["identifier"].get("isin"),
            wkn=data["identifier"].get("wkn"),
            symbol=data["identifier"].get("symbol"),
            name=data["identifier"].get("name"),
        )

        price_data = data["price"]
        price = StockPrice(
            current=Decimal(price_data["current"]),
            currency=price_data["currency"],
            change_absolute=(
                Decimal(price_data["change_absolute"])
                if price_data.get("change_absolute")
                else None
            ),
            change_percent=(
                Decimal(price_data["change_percent"]) if price_data.get("change_percent") else None
            ),
            previous_close=(
                Decimal(price_data["previous_close"]) if price_data.get("previous_close") else None
            ),
            open_price=Decimal(price_data["open"]) if price_data.get("open") else None,
            day_high=Decimal(price_data["day_high"]) if price_data.get("day_high") else None,
            day_low=Decimal(price_data["day_low"]) if price_data.get("day_low") else None,
            week_52_high=(
                Decimal(price_data["week_52_high"]) if price_data.get("week_52_high") else None
            ),
            week_52_low=(
                Decimal(price_data["week_52_low"]) if price_data.get("week_52_low") else None
            ),
            volume=price_data.get("volume"),
            avg_volume=price_data.get("avg_volume"),
        )

        metadata_data = data["metadata"]
        metadata = StockMetadata(
            exchange=metadata_data.get("exchange"),
            sector=metadata_data.get("sector"),
            industry=metadata_data.get("industry"),
            market_cap=(
                Decimal(metadata_data["market_cap"]) if metadata_data.get("market_cap") else None
            ),
            pe_ratio=Decimal(metadata_data["pe_ratio"]) if metadata_data.get("pe_ratio") else None,
            dividend_yield=(
                Decimal(metadata_data["dividend_yield"])
                if metadata_data.get("dividend_yield")
                else None
            ),
            beta=Decimal(metadata_data["beta"]) if metadata_data.get("beta") else None,
        )

        # Calculate cache age
        cached_at = datetime.fromisoformat(data["cached_at"])
        cache_age = int((datetime.now(timezone.utc) - cached_at).total_seconds())

        return Stock(
            identifier=identifier,
            price=price,
            metadata=metadata,
            data_source=DataSource(data["data_source"]),
            last_updated=datetime.fromisoformat(data["last_updated"]),
            cache_age_seconds=cache_age,
        )

    async def count_user_favorites(self, user_id: str) -> int:
        """Not supported in Redis - use PostgreSQL."""
        return 0

    async def add_favorite(self, user_id: str, symbol: str) -> None:
        """Not supported in Redis - use PostgreSQL."""
        pass

    async def remove_favorite(self, user_id: str, symbol: str) -> None:
        """Not supported in Redis - use PostgreSQL."""
        pass

    async def get_user_favorites(self, user_id: str) -> List[str]:
        """Not supported in Redis - use PostgreSQL."""
        return []
