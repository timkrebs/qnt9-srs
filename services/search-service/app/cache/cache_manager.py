"""
Cache Manager for orchestrating multi-layer caching.

DEPRECATED: This module is superseded by direct repository usage
in StockSearchService which implements the multi-layer caching strategy.

For new code, use:
- MemoryCache (L0) via get_memory_cache()
- RedisRepository (L1) via dependency injection
- PostgresRepository (L2) via dependency injection

This module is kept for backward compatibility only.
"""

import logging
from typing import Optional

from app.cache.memory_cache import get_memory_cache
from app.domain.entities import Stock
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class CacheManager:
    """
    DEPRECATED: Legacy cache manager.

    Use StockSearchService which implements proper multi-layer caching.
    This class is kept for backward compatibility only.
    """

    def __init__(self, db: Session):
        """
        Initialize cache manager.

        Args:
            db: Database session
        """
        self.db = db
        self.memory_cache = get_memory_cache()
        logger.warning("CacheManager is deprecated. Use StockSearchService instead.")

    def get(self, key: str) -> Optional[Stock]:
        """
        Get stock from memory cache only.

        DEPRECATED: Use StockSearchService.search() instead.

        Args:
            key: Cache key

        Returns:
            Stock if found in memory cache, None otherwise
        """
        return self.memory_cache.get(key)

    def set(self, key: str, stock: Stock, ttl_minutes: int = 5) -> None:
        """
        Store stock in memory cache only.

        DEPRECATED: Use StockSearchService which handles all cache layers.

        Args:
            key: Cache key
            stock: Stock entity
            ttl_minutes: Time-to-live in minutes
        """
        try:
            self.memory_cache.set(key, stock, ttl_minutes)
        except Exception as e:
            logger.error("Error caching stock: %s", e)

    def invalidate(self, key: str) -> None:
        """
        Invalidate cache entry in memory only.

        DEPRECATED: This only affects L0 cache.

        Args:
            key: Cache key to invalidate
        """
        try:
            self.memory_cache.invalidate(key)
        except Exception as e:
            logger.error("Error invalidating cache: %s", e)

    def clear_all(self) -> None:
        """
        Clear memory cache only.

        DEPRECATED: This only affects L0 cache.
        """
        try:
            self.memory_cache.clear()
        except Exception as e:
            logger.error("Error clearing cache: %s", e)

    def get_stats(self) -> dict:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats from all layers
        """
        return {
            "memory_cache": self.memory_cache.get_stats(),
            # TODO: Add Redis stats here
        }
