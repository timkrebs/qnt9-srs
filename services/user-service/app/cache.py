"""
In-memory caching module for user service.

Provides TTL-based caching for user profiles to reduce database load.
Uses LRU eviction when cache reaches maximum size.

Note: For production with multiple instances, replace with Redis-based
caching for distributed state management.
"""

import time
from collections import OrderedDict
from dataclasses import dataclass
from threading import Lock
from typing import Any, Dict, Generic, Optional, TypeVar

import structlog

logger = structlog.get_logger()

T = TypeVar("T")


@dataclass
class CacheEntry(Generic[T]):
    """A cached value with expiration time."""

    value: T
    expires_at: float


class TTLCache(Generic[T]):
    """
    Thread-safe in-memory cache with TTL and LRU eviction.

    Features:
    - Time-based expiration (TTL)
    - LRU eviction when max size reached
    - Thread-safe operations
    - Cache hit/miss statistics

    Attributes:
        max_size: Maximum number of entries
        default_ttl: Default TTL in seconds
    """

    def __init__(self, max_size: int = 1000, default_ttl: float = 60.0) -> None:
        """
        Initialize cache.

        Args:
            max_size: Maximum number of entries before LRU eviction
            default_ttl: Default time-to-live in seconds
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, CacheEntry[T]] = OrderedDict()
        self._lock = Lock()
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    def get(self, key: str) -> Optional[T]:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        with self._lock:
            entry = self._cache.get(key)

            if entry is None:
                self._misses += 1
                return None

            # Check expiration
            if time.time() > entry.expires_at:
                del self._cache[key]
                self._misses += 1
                logger.debug("Cache entry expired", key=key)
                return None

            # Move to end (most recently used)
            self._cache.move_to_end(key)
            self._hits += 1
            return entry.value

    def set(self, key: str, value: T, ttl: Optional[float] = None) -> None:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (uses default if None)
        """
        ttl = ttl if ttl is not None else self.default_ttl
        expires_at = time.time() + ttl

        with self._lock:
            # Remove existing entry if present
            if key in self._cache:
                del self._cache[key]

            # Evict oldest entries if at capacity
            while len(self._cache) >= self.max_size:
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
                self._evictions += 1
                logger.debug("Cache LRU eviction", evicted_key=oldest_key)

            self._cache[key] = CacheEntry(value=value, expires_at=expires_at)

    def delete(self, key: str) -> bool:
        """
        Delete entry from cache.

        Args:
            key: Cache key

        Returns:
            True if entry was deleted, False if not found
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self) -> None:
        """Clear all entries from cache."""
        with self._lock:
            self._cache.clear()

    def invalidate_pattern(self, prefix: str) -> int:
        """
        Invalidate all entries matching a key prefix.

        Args:
            prefix: Key prefix to match

        Returns:
            Number of entries invalidated
        """
        with self._lock:
            keys_to_delete = [k for k in self._cache if k.startswith(prefix)]
            for key in keys_to_delete:
                del self._cache[key]
            return len(keys_to_delete)

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with hit rate, size, and other stats
        """
        with self._lock:
            total = self._hits + self._misses
            hit_rate = (self._hits / total * 100) if total > 0 else 0.0

            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate_percent": round(hit_rate, 2),
                "evictions": self._evictions,
            }

    def cleanup_expired(self) -> int:
        """
        Remove all expired entries.

        Returns:
            Number of entries removed
        """
        now = time.time()
        with self._lock:
            expired_keys = [k for k, v in self._cache.items() if v.expires_at < now]
            for key in expired_keys:
                del self._cache[key]
            return len(expired_keys)


# Pre-configured caches for different data types
# User profiles: 60 second TTL, max 1000 entries
user_profile_cache: TTLCache[Dict[str, Any]] = TTLCache(max_size=1000, default_ttl=60.0)

# User tier info: 30 second TTL (more frequently updated)
user_tier_cache: TTLCache[Dict[str, Any]] = TTLCache(max_size=1000, default_ttl=30.0)


def cache_key_user_profile(user_id: str) -> str:
    """Generate cache key for user profile."""
    return f"user:profile:{user_id}"


def cache_key_user_tier(user_id: str) -> str:
    """Generate cache key for user tier."""
    return f"user:tier:{user_id}"
