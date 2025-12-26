"""
In-memory LRU cache for hot stock data.

This module provides ultra-fast access to frequently searched stocks
using an in-memory Least Recently Used (LRU) cache. Target latency: <10ms.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Optional

from cachetools import LRUCache  # type: ignore[import-untyped]

from app.domain.entities import Stock

logger = logging.getLogger(__name__)


class MemoryStockCache:
    """
    In-memory LRU cache for stock data.

    Provides sub-millisecond access to the most popular stocks.
    Designed as Layer 0 (L0) cache before Redis and PostgreSQL.

    Cache hierarchy:
    - L0: In-Memory LRU (this class) - ~1μs access
    - L1: Redis - ~1ms access
    - L2: PostgreSQL - ~10ms access
    - L3: External API - ~500ms access

    Attributes:
        cache: LRU cache storing stock data
        max_size: Maximum number of items to cache (default: 1000)
        hits: Number of cache hits
        misses: Number of cache misses
        evictions: Number of items evicted due to size limit
    """

    def __init__(self, max_size: int = 1000):
        """
        Initialize memory cache.

        Args:
            max_size: Maximum number of stocks to cache (default: 1000)
        """
        self.cache: LRUCache = LRUCache(maxsize=max_size)
        self.max_size = max_size

        # Statistics
        self.hits = 0
        self.misses = 0
        self.evictions = 0

        logger.info(f"Initialized MemoryStockCache with max_size={max_size}")

    def get(self, key: str) -> Optional[Stock]:
        """
        Get stock data from cache.

        Args:
            key: Cache key (typically symbol or identifier)

        Returns:
            Stock if found and not expired, None otherwise
        """
        try:
            stock_data = self.cache.get(key)

            if stock_data is None:
                self.misses += 1
                logger.debug(f"Cache MISS: {key}")
                return None

            # Check if data is expired
            if self._is_expired(stock_data):
                # Remove expired entry
                del self.cache[key]
                self.misses += 1
                logger.debug(f"Cache MISS (expired): {key}")
                return None

            self.hits += 1
            logger.debug(f"Cache HIT: {key}")
            return stock_data

        except Exception as e:
            logger.error(f"Error getting from cache: {e}")
            self.misses += 1
            return None

    def set(self, key: str, stock: Stock, ttl_minutes: int = 5) -> None:
        """
        Store stock data in cache.

        Args:
            key: Cache key (typically symbol or identifier)
            stock: Stock entity to cache
            ttl_minutes: Time-to-live in minutes (default: 5)
        """
        try:
            # Check if we'll evict an item
            if len(self.cache) >= self.max_size and key not in self.cache:
                self.evictions += 1

            # Add expiration timestamp to stock (using object.__setattr__ for frozen dataclass)
            if not hasattr(stock, "cache_expires_at"):
                expires_at = datetime.now(timezone.utc).timestamp() + (ttl_minutes * 60)
                object.__setattr__(stock, "cache_expires_at", expires_at)

            self.cache[key] = stock
            logger.debug(f"Cached: {key} (TTL: {ttl_minutes}m)")

        except Exception as e:
            logger.error(f"Error setting cache: {e}")

    def delete(self, key: str) -> None:
        """
        Delete item from cache.

        Args:
            key: Cache key to delete
        """
        try:
            if key in self.cache:
                del self.cache[key]
                logger.debug(f"Deleted from cache: {key}")
        except Exception as e:
            logger.error(f"Error deleting from cache: {e}")

    def clear(self) -> None:
        """Clear all items from cache."""
        try:
            count = len(self.cache)
            self.cache.clear()
            logger.info(f"Cleared {count} items from cache")
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")

    def get_stats(self) -> Dict[str, int]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0

        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions,
            "total_requests": total_requests,
            "hit_rate_percent": int(round(hit_rate)),
        }

    def _is_expired(self, stock: Stock) -> bool:
        """
        Check if cached data has expired.

        Args:
            stock: Stock entity to check

        Returns:
            True if expired, False otherwise
        """
        if not hasattr(stock, "cache_expires_at"):
            return False

        current_time = datetime.now(timezone.utc).timestamp()
        return current_time > stock.cache_expires_at

    def warmup(self, stock_list: list[Stock]) -> int:
        """
        Pre-populate cache with stock data.

        Args:
            stock_list: List of stock entities to pre-load

        Returns:
            Number of items added to cache
        """
        count = 0
        for stock in stock_list:
            if hasattr(stock, "identifier") and hasattr(stock.identifier, "symbol"):
                symbol = stock.identifier.symbol
                if symbol:
                    key = symbol.upper()
                    self.set(key, stock)
                    count += 1

        logger.info(f"Warmed up cache with {count} stocks")
        return count


# Global cache instance
_memory_cache: Optional[MemoryStockCache] = None


def get_memory_cache(max_size: int = 1000) -> MemoryStockCache:
    """
    Get or create global memory cache instance.

    Args:
        max_size: Maximum cache size (only used on first call)

    Returns:
        Global MemoryStockCache instance
    """
    global _memory_cache

    if _memory_cache is None:
        _memory_cache = MemoryStockCache(max_size=max_size)

    return _memory_cache
