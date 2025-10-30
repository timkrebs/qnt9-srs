"""
Cache management for stock data
Implements PostgreSQL-based caching with 5-minute TTL
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from .models import SearchHistory, StockCache
from .validators import detect_query_type

logger = logging.getLogger(__name__)

# Cache TTL: 5 minutes
CACHE_TTL_MINUTES = 5


class CacheManager:
    """Manages stock data caching with PostgreSQL"""

    def __init__(self, db: Session):
        self.db = db

    def get_cached_stock(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve stock data from cache if available and not expired

        Args:
            query: ISIN, WKN, or symbol to search

        Returns:
            Cached stock data or None if not found/expired
        """
        query = query.strip().upper()
        query_type = detect_query_type(query)

        try:
            # Build query based on type
            now = datetime.utcnow()

            if query_type == "isin":
                cache_entry = (
                    self.db.query(StockCache)
                    .filter(StockCache.isin == query, StockCache.expires_at > now)
                    .first()
                )
            elif query_type == "wkn":
                cache_entry = (
                    self.db.query(StockCache)
                    .filter(StockCache.wkn == query, StockCache.expires_at > now)
                    .first()
                )
            else:  # symbol
                cache_entry = (
                    self.db.query(StockCache)
                    .filter(StockCache.symbol == query, StockCache.expires_at > now)
                    .first()
                )

            if cache_entry:
                # Increment hit counter
                cache_entry.increment_hits()
                self.db.commit()

                logger.info(
                    f"Cache HIT for {query_type.upper()} {query} "
                    f"(age: {(now - cache_entry.created_at).total_seconds():.1f}s, "
                    f"hits: {cache_entry.cache_hits})"
                )

                # Calculate cache age
                cache_age = int((now - cache_entry.created_at).total_seconds())

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

            logger.debug(f"Cache MISS for {query_type.upper()} {query}")
            return None

        except Exception as e:
            logger.error(f"Error retrieving from cache: {e}")
            return None

    def save_to_cache(self, stock_data: Dict[str, Any], query: str) -> bool:
        """
        Save stock data to cache

        Args:
            stock_data: Stock data dictionary from API
            query: Original search query

        Returns:
            True if successfully cached
        """
        try:
            # Calculate expiry time (5 minutes from now)
            expires_at = datetime.utcnow() + timedelta(minutes=CACHE_TTL_MINUTES)

            # Prepare data
            symbol = stock_data.get("symbol", "").upper()
            isin = stock_data.get("isin")
            wkn = self._extract_wkn(stock_data)

            # Check if entry already exists
            existing = (
                self.db.query(StockCache)
                .filter(
                    or_(
                        StockCache.symbol == symbol,
                        StockCache.isin == isin if isin else False,
                    )
                )
                .first()
            )

            if existing:
                # Update existing entry
                existing.name = stock_data.get("name", "")
                existing.current_price = stock_data.get("current_price")
                existing.currency = stock_data.get("currency")
                existing.exchange = stock_data.get("exchange")
                existing.market_cap = stock_data.get("market_cap")
                existing.sector = stock_data.get("sector")
                existing.industry = stock_data.get("industry")
                existing.data_source = stock_data.get("source", "unknown")
                existing.raw_data = json.dumps(stock_data.get("raw_data", {}))
                existing.updated_at = datetime.utcnow()
                existing.expires_at = expires_at

                if isin and not existing.isin:
                    existing.isin = isin
                if wkn and not existing.wkn:
                    existing.wkn = wkn

                logger.info(f"Updated cache for symbol {symbol}")
            else:
                # Create new cache entry
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
                logger.info(f"Created new cache entry for symbol {symbol}")

            self.db.commit()
            return True

        except Exception as e:
            logger.error(f"Error saving to cache: {e}")
            self.db.rollback()
            return False

    def cleanup_expired(self) -> int:
        """
        Remove expired cache entries

        Returns:
            Number of entries removed
        """
        try:
            now = datetime.utcnow()
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
        Record search query for analytics and suggestions

        Args:
            query: Search query
            found: Whether the stock was found
        """
        try:
            query = query.strip().upper()
            query_type = detect_query_type(query)

            # Check if query exists
            existing = (
                self.db.query(SearchHistory)
                .filter(SearchHistory.query == query, SearchHistory.query_type == query_type)
                .first()
            )

            if existing:
                existing.search_count += 1
                existing.last_searched = datetime.utcnow()
                if found:
                    existing.result_found = 1
            else:
                history = SearchHistory(
                    query=query,
                    query_type=query_type,
                    result_found=1 if found else 0,
                    search_count=1,
                )
                self.db.add(history)

            self.db.commit()

        except Exception as e:
            logger.error(f"Error recording search history: {e}")
            self.db.rollback()

    def get_suggestions(self, query: str, limit: int = 5) -> list[str]:
        """
        Get search suggestions based on query

        Args:
            query: Partial search query
            limit: Maximum number of suggestions

        Returns:
            List of suggested queries
        """
        try:
            query = query.strip().upper()

            # Get similar successful searches
            suggestions = (
                self.db.query(SearchHistory)
                .filter(
                    SearchHistory.query.like(f"{query}%"),
                    SearchHistory.result_found == 1,
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
        Extract WKN from stock data if available

        Args:
            stock_data: Stock data dictionary

        Returns:
            WKN or None
        """
        # Check top-level first
        wkn = stock_data.get("wkn") or stock_data.get("WKN")
        if wkn:
            return wkn

        # WKN might be in raw_data for German stocks
        raw_data = stock_data.get("raw_data", {})
        return raw_data.get("wkn") or raw_data.get("WKN")

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics

        Returns:
            Dictionary with cache stats
        """
        try:
            now = datetime.utcnow()

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
