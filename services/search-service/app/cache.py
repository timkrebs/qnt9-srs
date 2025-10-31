"""
Cache management for stock data.

This module implements PostgreSQL-based caching with time-to-live (TTL)
management for stock data. It reduces external API calls and improves
response times.
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from sqlalchemy import func, or_, text
from sqlalchemy.orm import Session

from .models import SearchHistory, StockCache
from .validators import MAX_NAME_SEARCH_RESULTS, detect_query_type

logger = logging.getLogger(__name__)

# Cache configuration constants
CACHE_TTL_MINUTES = 5
RESULT_FOUND = 1
RESULT_NOT_FOUND = 0
SEARCH_COUNT_INCREMENT = 1

# Relevance scoring constants
SCORE_EXACT_MATCH = 1.0
SCORE_STARTS_WITH = 0.9
SCORE_WORD_BOUNDARY = 0.8
SCORE_CONTAINS_BASE = 0.6
SCORE_LENGTH_BONUS_MAX = 0.2
SCORE_NO_MATCH = 0.0


class CacheManager:
    """
    Manages stock data caching with PostgreSQL backend.

    Provides methods for retrieving, storing, and managing cached stock data
    with automatic expiration and analytics tracking.

    Attributes:
        db: SQLAlchemy database session
    """

    def __init__(self, db: Session):
        """
        Initialize cache manager.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def get_cached_stock(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve stock data from cache if available and not expired.

        Automatically increments cache hit counter when data is found.

        Args:
            query: ISIN, WKN, or symbol to search

        Returns:
            Cached stock data dictionary or None if not found/expired
        """
        query = query.strip().upper()
        query_type = detect_query_type(query)

        try:
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            cache_entry = self._get_cache_entry(query, query_type, now)

            if cache_entry:
                cache_entry.increment_hits()
                self.db.commit()

                cache_age = int((now - cache_entry.created_at).total_seconds())

                logger.info(
                    f"Cache HIT for {query_type.upper()} {query} "
                    f"(age: {cache_age}s, hits: {cache_entry.cache_hits})"
                )

                return self._build_stock_dict(cache_entry, cache_age)

            logger.debug(f"Cache MISS for {query_type.upper()} {query}")
            return None

        except Exception as e:
            logger.error(f"Error retrieving from cache: {e}")
            return None

    def _get_cache_entry(self, query: str, query_type: str, now: datetime) -> Optional[StockCache]:
        """
        Get cache entry based on query type.

        Args:
            query: Search query
            query_type: Type of query ('isin', 'wkn', or 'symbol')
            now: Current timestamp

        Returns:
            StockCache entry or None if not found
        """
        if query_type == "isin":
            return (
                self.db.query(StockCache)
                .filter(StockCache.isin == query, StockCache.expires_at > now)
                .first()
            )
        elif query_type == "wkn":
            return (
                self.db.query(StockCache)
                .filter(StockCache.wkn == query, StockCache.expires_at > now)
                .first()
            )
        else:
            return (
                self.db.query(StockCache)
                .filter(StockCache.symbol == query, StockCache.expires_at > now)
                .first()
            )

    def _build_stock_dict(self, cache_entry: StockCache, cache_age: int) -> Dict[str, Any]:
        """
        Build stock data dictionary from cache entry.

        Args:
            cache_entry: StockCache database entry
            cache_age: Age of cache entry in seconds

        Returns:
            Dictionary containing stock data
        """
        return {
            "symbol": cache_entry.symbol,
            "name": cache_entry.name,
            "isin": cache_entry.isin,
            "wkn": cache_entry.wkn,
            "current_price": cache_entry.current_price,
            "currency": cache_entry.currency,
            "exchange": cache_entry.exchange,
            "market_cap": cache_entry.market_cap,
            "sector": cache_entry.sector,
            "industry": cache_entry.industry,
            "source": cache_entry.data_source,
            "cached": True,
            "cache_age_seconds": cache_age,
        }

    def save_to_cache(self, stock_data: Dict[str, Any], query: str) -> bool:
        """
        Save stock data to cache with automatic TTL.

        Updates existing entries if found, otherwise creates new entry.

        Args:
            stock_data: Stock data dictionary from API
            query: Original search query

        Returns:
            True if successfully cached, False otherwise
        """
        try:
            expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(
                minutes=CACHE_TTL_MINUTES
            )

            symbol = stock_data.get("symbol", "").upper()
            isin = stock_data.get("isin")
            wkn = self._extract_wkn(stock_data)

            existing = self._find_existing_entry(symbol, isin)

            if existing:
                self._update_cache_entry(existing, stock_data, isin, wkn, expires_at)
                logger.info(f"Updated cache for symbol {symbol}")
            else:
                self._create_cache_entry(stock_data, symbol, isin, wkn, expires_at)
                logger.info(f"Created new cache entry for symbol {symbol}")

            self.db.commit()
            return True

        except Exception as e:
            logger.error(f"Error saving to cache: {e}")
            self.db.rollback()
            return False

    def _find_existing_entry(self, symbol: str, isin: Optional[str]) -> Optional[StockCache]:
        """
        Find existing cache entry by symbol or ISIN.

        Args:
            symbol: Stock ticker symbol
            isin: ISIN code (optional)

        Returns:
            Existing StockCache entry or None
        """
        return (
            self.db.query(StockCache)
            .filter(
                or_(
                    StockCache.symbol == symbol,
                    StockCache.isin == isin if isin else False,
                )
            )
            .first()
        )

    def _update_cache_entry(
        self,
        entry: StockCache,
        stock_data: Dict[str, Any],
        isin: Optional[str],
        wkn: Optional[str],
        expires_at: datetime,
    ) -> None:
        """
        Update existing cache entry with new data.

        Args:
            entry: Existing StockCache entry
            stock_data: New stock data
            isin: ISIN code
            wkn: WKN code
            expires_at: New expiration timestamp
        """
        entry.name = stock_data.get("name", "")
        entry.current_price = stock_data.get("current_price")
        entry.currency = stock_data.get("currency")
        entry.exchange = stock_data.get("exchange")
        entry.market_cap = stock_data.get("market_cap")
        entry.sector = stock_data.get("sector")
        entry.industry = stock_data.get("industry")
        entry.data_source = stock_data.get("source", "unknown")
        entry.raw_data = json.dumps(stock_data.get("raw_data", {}))
        entry.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        entry.expires_at = expires_at

        if isin and not entry.isin:
            entry.isin = isin
        if wkn and not entry.wkn:
            entry.wkn = wkn

    def _create_cache_entry(
        self,
        stock_data: Dict[str, Any],
        symbol: str,
        isin: Optional[str],
        wkn: Optional[str],
        expires_at: datetime,
    ) -> None:
        """
        Create new cache entry.

        Args:
            stock_data: Stock data from API
            symbol: Stock ticker symbol
            isin: ISIN code
            wkn: WKN code
            expires_at: Expiration timestamp
        """
        cache_entry = StockCache(
            symbol=symbol,
            isin=isin,
            wkn=wkn,
            name=stock_data.get("name", ""),
            current_price=stock_data.get("current_price"),
            currency=stock_data.get("currency"),
            exchange=stock_data.get("exchange"),
            market_cap=stock_data.get("market_cap"),
            sector=stock_data.get("sector"),
            industry=stock_data.get("industry"),
            data_source=stock_data.get("source", "unknown"),
            raw_data=json.dumps(stock_data.get("raw_data", {})),
            expires_at=expires_at,
        )
        self.db.add(cache_entry)

    def cleanup_expired(self) -> int:
        """
        Remove expired cache entries from database.

        Returns:
            Number of entries removed
        """
        try:
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            deleted = self.db.query(StockCache).filter(StockCache.expires_at < now).delete()
            self.db.commit()

            if deleted > 0:
                logger.info(f"Cleaned up {deleted} expired cache entries")

            return deleted

        except Exception as e:
            logger.error(f"Error cleaning up cache: {e}")
            self.db.rollback()
            return 0

    def record_search(self, query: str, found: bool) -> None:
        """
        Record search query for analytics and suggestions.

        Tracks query frequency and success rate for autocomplete suggestions.

        Args:
            query: Search query string
            found: Whether the stock was found
        """
        try:
            query = query.strip().upper()
            query_type = detect_query_type(query)

            existing = (
                self.db.query(SearchHistory)
                .filter(SearchHistory.query == query, SearchHistory.query_type == query_type)
                .first()
            )

            if existing:
                existing.search_count += SEARCH_COUNT_INCREMENT
                existing.last_searched = datetime.now(timezone.utc).replace(tzinfo=None)
                if found:
                    existing.result_found = RESULT_FOUND
            else:
                history = SearchHistory(
                    query=query,
                    query_type=query_type,
                    result_found=RESULT_FOUND if found else RESULT_NOT_FOUND,
                    search_count=1,
                )
                self.db.add(history)

            self.db.commit()

        except Exception as e:
            logger.error(f"Error recording search history: {e}")
            self.db.rollback()

    def get_suggestions(self, query: str, limit: int = 5) -> list[str]:
        """
        Get autocomplete suggestions based on query prefix.

        Returns popular successful searches matching the query prefix.

        Args:
            query: Partial search query
            limit: Maximum number of suggestions to return

        Returns:
            List of suggested query strings
        """
        try:
            query = query.strip().upper()

            suggestions = (
                self.db.query(SearchHistory)
                .filter(
                    SearchHistory.query.like(f"{query}%"),
                    SearchHistory.result_found == RESULT_FOUND,
                )
                .order_by(SearchHistory.search_count.desc())
                .limit(limit)
                .all()
            )

            return [s.query for s in suggestions]

        except Exception as e:
            logger.error(f"Error getting suggestions: {e}")
            return []

    def _extract_wkn(self, stock_data: Dict[str, Any]) -> Optional[str]:
        """
        Extract WKN from stock data if available.

        Args:
            stock_data: Stock data dictionary

        Returns:
            WKN string or None if not found
        """
        wkn = stock_data.get("wkn") or stock_data.get("WKN")
        if wkn:
            return wkn

        raw_data = stock_data.get("raw_data", {})
        return raw_data.get("wkn") or raw_data.get("WKN")

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics for monitoring and debugging.

        Returns:
            Dictionary containing cache statistics:
            - total_entries: Total number of cache entries
            - active_entries: Number of non-expired entries
            - expired_entries: Number of expired entries
            - total_hits: Sum of all cache hits
        """
        try:
            now = datetime.now(timezone.utc).replace(tzinfo=None)

            total_entries = self.db.query(StockCache).count()
            active_entries = self.db.query(StockCache).filter(StockCache.expires_at > now).count()
            expired_entries = total_entries - active_entries

            total_hits = (
                self.db.query(StockCache).with_entities(func.sum(StockCache.cache_hits)).scalar()
                or 0
            )

            return {
                "total_entries": total_entries,
                "active_entries": active_entries,
                "expired_entries": expired_entries,
                "total_hits": total_hits,
            }

        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {}

    def search_by_name(
        self, query: str, limit: int = MAX_NAME_SEARCH_RESULTS
    ) -> list[Dict[str, Any]]:
        """
        Search for stocks by company name using fuzzy matching.

        Performs case-insensitive partial matching on the name field.
        Returns only non-expired cached entries sorted by relevance.

        Args:
            query: Company name search string
            limit: Maximum number of results to return (default: 10)

        Returns:
            List of stock dictionaries with relevance scores
        """
        query = query.strip()

        if not query:
            return []

        try:
            now = datetime.now(timezone.utc).replace(tzinfo=None)

            # Detect database type to choose search strategy
            dialect_name = self.db.bind.dialect.name

            if dialect_name == "postgresql" and self._has_fts_support():
                # Use PostgreSQL full-text search for better performance
                logger.debug(f"Using PostgreSQL full-text search for '{query}'")
                cache_entries = self._search_with_fts(query, now, limit)
            else:
                # Fall back to ILIKE for SQLite or when FTS not available
                logger.debug(f"Using ILIKE search for '{query}'")
                cache_entries = self._search_with_ilike(query, now, limit)

            results = []
            for entry in cache_entries:
                # Calculate relevance score based on match quality
                relevance = self._calculate_relevance_score(query, entry.name)

                result = {
                    "symbol": entry.symbol,
                    "name": entry.name,
                    "isin": entry.isin,
                    "wkn": entry.wkn,
                    "current_price": entry.current_price,
                    "currency": entry.currency,
                    "exchange": entry.exchange,
                    "relevance_score": relevance,
                }
                results.append(result)

            # Sort by relevance score (highest first)
            results.sort(key=lambda x: x["relevance_score"], reverse=True)

            logger.info(f"Name search for '{query}' returned {len(results)} results")
            return results

        except Exception as e:
            logger.error(f"Error searching by name: {e}")
            return []

    def _has_fts_support(self) -> bool:
        """
        Check if database has full-text search support.

        Checks for PostgreSQL database and presence of name_search_vector column.

        Returns:
            True if full-text search is available and usable
        """
        try:
            # Check if we're using PostgreSQL
            if self.db.bind.dialect.name != "postgresql":
                return False

            # Check if the name_search_vector column exists
            # by attempting to access it
            inspector = self.db.bind.dialect.get_inspector(self.db.bind)
            columns = [col["name"] for col in inspector.get_columns("stock_cache")]

            return "name_search_vector" in columns

        except Exception as e:
            logger.debug(f"FTS support check failed: {e}")
            return False

    def _search_with_fts(self, query: str, now: datetime, limit: int) -> list[StockCache]:
        """
        Search using PostgreSQL full-text search.

        Uses tsvector and tsquery for fast, ranked full-text search.

        Args:
            query: Search query string
            now: Current timestamp for expiration check
            limit: Maximum results to return

        Returns:
            List of StockCache entries matching the search
        """
        # Convert query to tsquery format (AND operation between words)
        # This creates a phrase search with prefix matching
        search_query = " & ".join(f"{word}:*" for word in query.split())

        # Use text() for raw SQL since name_search_vector isn't in the model
        return (
            self.db.query(StockCache)
            .filter(
                StockCache.expires_at > now,
                text("name_search_vector @@ to_tsquery('english', :query)"),
            )
            .params(query=search_query)
            .limit(limit)
            .all()
        )

    def _search_with_ilike(self, query: str, now: datetime, limit: int) -> list[StockCache]:
        """
        Search using case-insensitive LIKE (fallback for SQLite).

        Args:
            query: Search query string
            now: Current timestamp for expiration check
            limit: Maximum results to return

        Returns:
            List of StockCache entries matching the search
        """
        search_pattern = f"%{query}%"

        return (
            self.db.query(StockCache)
            .filter(StockCache.expires_at > now, StockCache.name.ilike(search_pattern))
            .limit(limit)
            .all()
        )

    def _calculate_relevance_score(self, query: str, name: str) -> float:
        """
        Calculate relevance score for name matching.

        Scoring algorithm:
        - Exact match: 1.0
        - Starts with query: 0.9
        - Contains query as word boundary: 0.8
        - Contains query anywhere: 0.6 + length bonus (up to 0.2)
        - No match: 0.0

        Args:
            query: Search query (normalized)
            name: Company name from database

        Returns:
            Relevance score between 0.0 and 1.0
        """
        if not name:
            return SCORE_NO_MATCH

        query_lower = query.lower()
        name_lower = name.lower()

        # Exact match
        if query_lower == name_lower:
            return SCORE_EXACT_MATCH

        # Starts with query
        if name_lower.startswith(query_lower):
            return SCORE_STARTS_WITH

        # Word boundary match (query appears as separate word)
        if self._matches_word_boundary(query_lower, name_lower):
            return SCORE_WORD_BOUNDARY

        # Contains query anywhere
        if query_lower in name_lower:
            return self._calculate_contains_score(query, name)

        return SCORE_NO_MATCH

    def _matches_word_boundary(self, query_lower: str, name_lower: str) -> bool:
        """
        Check if query matches a word boundary in the name.

        Args:
            query_lower: Lowercase search query
            name_lower: Lowercase company name

        Returns:
            True if query matches start of any word
        """
        words = name_lower.split()
        return any(word.startswith(query_lower) for word in words)

    def _calculate_contains_score(self, query: str, name: str) -> float:
        """
        Calculate score for substring match with length bonus.

        Shorter names get higher scores as they are more specific.

        Args:
            query: Original query string
            name: Company name string

        Returns:
            Score between SCORE_CONTAINS_BASE and (SCORE_CONTAINS_BASE + SCORE_LENGTH_BONUS_MAX)
        """
        length_ratio = len(query) / len(name)
        length_bonus = length_ratio * SCORE_LENGTH_BONUS_MAX
        return SCORE_CONTAINS_BASE + length_bonus
