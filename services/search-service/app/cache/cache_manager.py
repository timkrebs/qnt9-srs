"""
Cache Manager for orchestrating multi-layer caching.

Coordinates between memory cache (L0), Redis (L1), and PostgreSQL (L2).
"""

import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.domain.entities import Stock
from app.cache.memory_cache import MemoryStockCache, get_memory_cache

logger = logging.getLogger(__name__)


class CacheManager:
    """
    Manages multi-layer cache operations.
    
    Coordinates caching across:
    - L0: In-memory LRU cache (fastest, smallest)
    - L1: Redis (fast, medium size) [not yet implemented]
    - L2: PostgreSQL (slower, largest)
    """
    
    def __init__(self, db: Session):
        """
        Initialize cache manager.
        
        Args:
            db: Database session for L2 cache operations
        """
        self.db = db
        self.memory_cache = get_memory_cache()
        logger.debug("Initialized CacheManager")
    
    def get(self, key: str) -> Optional[Stock]:
        """
        Get stock data from cache hierarchy.
        
        Checks L0 (memory) first, then falls back to L2 (database).
        
        Args:
            key: Cache key (typically symbol or identifier)
            
        Returns:
            Stock if found, None otherwise
        """
        # Try L0 (memory cache) first
        stock = self.memory_cache.get(key)
        if stock:
            logger.debug(f"Cache hit (L0): {key}")
            return stock
        
        # TODO: Add Redis L1 cache here
        
        # L2 (database) fallback handled by caller
        return None
    
    def set(self, key: str, stock: Stock, ttl_minutes: int = 5) -> None:
        """
        Store stock data in cache.
        
        Stores in L0 (memory) cache. Database storage handled separately.
        
        Args:
            key: Cache key (typically symbol or identifier)
            stock: Stock entity to cache
            ttl_minutes: Time-to-live in minutes
        """
        try:
            self.memory_cache.set(key, stock, ttl_minutes)
            logger.debug(f"Cached stock (L0): {key}")
        except Exception as e:
            logger.error(f"Error caching stock: {e}")
    
    def invalidate(self, key: str) -> None:
        """
        Invalidate cache entry across all layers.
        
        Args:
            key: Cache key to invalidate
        """
        try:
            self.memory_cache.invalidate(key)
            # TODO: Add Redis invalidation here
            logger.debug(f"Invalidated cache: {key}")
        except Exception as e:
            logger.error(f"Error invalidating cache: {e}")
    
    def clear_all(self) -> None:
        """Clear all cache layers."""
        try:
            self.memory_cache.clear()
            # TODO: Add Redis clear here
            logger.info("Cleared all caches")
        except Exception as e:
            logger.error(f"Error clearing caches: {e}")
    
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
