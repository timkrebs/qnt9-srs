"""
PostgreSQL implementation of stock repository.

Implements persistent storage for stock metadata and historical data.
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from ..domain.entities import (
    DataSource,
    IdentifierType,
    Stock,
    StockIdentifier,
    StockMetadata,
    StockPrice,
)
from ..domain.exceptions import CacheException
from ..models import SearchHistory, StockCache
from .stock_repository import (
    ISearchHistoryRepository,
    IStockRepository,
    ISymbolMappingRepository,
)

logger = logging.getLogger(__name__)


class PostgresStockRepository(IStockRepository):
    """PostgreSQL implementation for stock data persistence."""

    def __init__(self, db: Session, cache_ttl_minutes: int = 5):
        """
        Initialize repository.

        Args:
            db: SQLAlchemy database session
            cache_ttl_minutes: Cache time-to-live in minutes
        """
        self.db = db
        self.cache_ttl_minutes = cache_ttl_minutes

    async def find_by_identifier(self, identifier: StockIdentifier) -> Optional[Stock]:
        """Find stock by identifier from PostgreSQL cache."""
        try:
            now = datetime.now(timezone.utc).replace(tzinfo=None)

            # Build query based on available identifiers
            query = self.db.query(StockCache).filter(StockCache.expires_at > now)

            if identifier.isin:
                query = query.filter(StockCache.isin == identifier.isin)
            elif identifier.wkn:
                query = query.filter(StockCache.wkn == identifier.wkn)
            elif identifier.symbol:
                query = query.filter(StockCache.symbol == identifier.symbol)
            else:
                return None

            cache_entry = query.first()

            if cache_entry:
                # Increment hit counter
                cache_entry.cache_hits += 1
                self.db.commit()

                return self._map_to_entity(cache_entry)

            return None

        except Exception as e:
            logger.error(f"Error finding stock in PostgreSQL: {e}")
            raise CacheException("find", str(e))

    async def find_by_name(self, name: str, limit: int = 10) -> List[Stock]:
        """Search stocks by company name with fuzzy matching."""
        try:
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            name_upper = name.upper()

            # Query with ILIKE for fuzzy matching
            results = (
                self.db.query(StockCache)
                .filter(
                    StockCache.expires_at > now,
                    or_(
                        StockCache.name.ilike(f"%{name}%"),
                        StockCache.name.ilike(f"%{name_upper}%"),
                    ),
                )
                .limit(limit)
                .all()
            )

            return [self._map_to_entity(entry) for entry in results]

        except Exception as e:
            logger.error(f"Error searching by name in PostgreSQL: {e}")
            return []

    async def save(self, stock: Stock) -> Stock:
        """Save or update stock in PostgreSQL cache."""
        try:
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            expires_at = now + timedelta(minutes=self.cache_ttl_minutes)

            # Find existing entry
            existing = None
            if stock.identifier.isin:
                existing = (
                    self.db.query(StockCache)
                    .filter(StockCache.isin == stock.identifier.isin)
                    .first()
                )
            elif stock.identifier.wkn:
                existing = (
                    self.db.query(StockCache)
                    .filter(StockCache.wkn == stock.identifier.wkn)
                    .first()
                )
            elif stock.identifier.symbol:
                existing = (
                    self.db.query(StockCache)
                    .filter(StockCache.symbol == stock.identifier.symbol)
                    .first()
                )

            if existing:
                # Update existing
                self._update_cache_entry(existing, stock, expires_at)
            else:
                # Create new
                cache_entry = self._create_cache_entry(stock, now, expires_at)
                self.db.add(cache_entry)

            self.db.commit()
            return stock

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error saving stock to PostgreSQL: {e}")
            raise CacheException("save", str(e))

    async def delete_expired(self, before: datetime) -> int:
        """Delete expired cache entries."""
        try:
            deleted = (
                self.db.query(StockCache)
                .filter(StockCache.expires_at < before)
                .delete()
            )
            self.db.commit()
            return deleted
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting expired entries: {e}")
            return 0

    async def get_cache_stats(self) -> dict:
        """Get cache statistics."""
        try:
            now = datetime.now(timezone.utc).replace(tzinfo=None)

            total = self.db.query(func.count(StockCache.id)).scalar()
            valid = (
                self.db.query(func.count(StockCache.id))
                .filter(StockCache.expires_at > now)
                .scalar()
            )
            expired = total - valid

            total_hits = self.db.query(func.sum(StockCache.cache_hits)).scalar() or 0

            return {
                "total_entries": total,
                "valid_entries": valid,
                "expired_entries": expired,
                "total_hits": total_hits,
                "cache_ttl_minutes": self.cache_ttl_minutes,
            }
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {}

    def _map_to_entity(self, cache_entry: StockCache) -> Stock:
        """Map database model to domain entity."""
        cache_age = int(
            (
                datetime.now(timezone.utc).replace(tzinfo=None) - cache_entry.created_at
            ).total_seconds()
        )

        identifier = StockIdentifier(
            isin=cache_entry.isin,
            wkn=cache_entry.wkn,
            symbol=cache_entry.symbol,
            name=cache_entry.name,
        )

        price = StockPrice(
            current=Decimal(str(cache_entry.current_price)),
            currency=cache_entry.currency or "USD",
            previous_close=Decimal(str(cache_entry.previous_close))
            if hasattr(cache_entry, "previous_close") and cache_entry.previous_close
            else None,
        )

        metadata = StockMetadata(
            exchange=cache_entry.exchange,
            sector=cache_entry.sector,
            industry=cache_entry.industry,
            market_cap=Decimal(str(cache_entry.market_cap))
            if cache_entry.market_cap
            else None,
        )

        return Stock(
            identifier=identifier,
            price=price,
            metadata=metadata,
            data_source=DataSource(cache_entry.data_source),
            last_updated=cache_entry.updated_at,
            cache_age_seconds=cache_age,
        )

    def _create_cache_entry(
        self, stock: Stock, now: datetime, expires_at: datetime
    ) -> StockCache:
        """Create new cache entry from stock entity."""
        return StockCache(
            isin=stock.identifier.isin,
            wkn=stock.identifier.wkn,
            symbol=stock.identifier.symbol,
            name=stock.identifier.name,
            current_price=float(stock.price.current),
            currency=stock.price.currency,
            exchange=stock.metadata.exchange,
            market_cap=float(stock.metadata.market_cap)
            if stock.metadata.market_cap
            else None,
            sector=stock.metadata.sector,
            industry=stock.metadata.industry,
            data_source=stock.data_source.value,
            raw_data=json.dumps(stock.to_dict()),
            created_at=now,
            updated_at=now,
            expires_at=expires_at,
            cache_hits=0,
        )

    def _update_cache_entry(
        self, entry: StockCache, stock: Stock, expires_at: datetime
    ) -> None:
        """Update existing cache entry."""
        entry.current_price = float(stock.price.current)
        entry.currency = stock.price.currency
        entry.exchange = stock.metadata.exchange
        entry.sector = stock.metadata.sector
        entry.industry = stock.metadata.industry
        entry.market_cap = (
            float(stock.metadata.market_cap) if stock.metadata.market_cap else None
        )
        entry.data_source = stock.data_source.value
        entry.raw_data = json.dumps(stock.to_dict())
        entry.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        entry.expires_at = expires_at

    async def count_user_favorites(self, user_id: str) -> int:
        """Count number of favorites for a user."""
        try:
            from ..models import UserFavorite

            count = (
                self.db.query(func.count(UserFavorite.id))
                .filter(UserFavorite.user_id == user_id)
                .scalar()
            )
            return count or 0
        except Exception as e:
            logger.error(f"Error counting user favorites: {e}")
            return 0

    async def add_favorite(self, user_id: str, symbol: str) -> None:
        """Add stock to user favorites."""
        try:
            from ..models import UserFavorite

            # Check if already exists
            existing = (
                self.db.query(UserFavorite)
                .filter(UserFavorite.user_id == user_id, UserFavorite.symbol == symbol)
                .first()
            )

            if not existing:
                favorite = UserFavorite(
                    user_id=user_id,
                    symbol=symbol,
                    added_at=datetime.now(timezone.utc).replace(tzinfo=None),
                )
                self.db.add(favorite)
                self.db.commit()
                logger.info(f"Added favorite {symbol} for user {user_id}")
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error adding favorite: {e}")
            raise

    async def remove_favorite(self, user_id: str, symbol: str) -> None:
        """Remove stock from user favorites."""
        try:
            from ..models import UserFavorite

            self.db.query(UserFavorite).filter(
                UserFavorite.user_id == user_id, UserFavorite.symbol == symbol
            ).delete()
            self.db.commit()
            logger.info(f"Removed favorite {symbol} for user {user_id}")
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error removing favorite: {e}")
            raise

    async def get_user_favorites(self, user_id: str) -> List[str]:
        """Get list of user's favorite symbols."""
        try:
            from ..models import UserFavorite

            favorites = (
                self.db.query(UserFavorite.symbol)
                .filter(UserFavorite.user_id == user_id)
                .order_by(UserFavorite.added_at.desc())
                .all()
            )

            return [f.symbol for f in favorites]
        except Exception as e:
            logger.error(f"Error getting user favorites: {e}")
            return []


class PostgresSearchHistoryRepository(ISearchHistoryRepository):
    """PostgreSQL implementation for search history tracking."""

    def __init__(self, db: Session):
        self.db = db

    async def record_search(
        self,
        query: str,
        query_type: IdentifierType,
        found: bool,
        response_time_ms: float,
        user_id: Optional[str] = None,
    ) -> None:
        """Record search query."""
        try:
            # Check if entry already exists
            existing = (
                self.db.query(SearchHistory)
                .filter(
                    SearchHistory.query == query,
                    SearchHistory.query_type == query_type.value,
                )
                .first()
            )

            if existing:
                # Update existing entry
                existing.search_count += 1
                existing.result_found = 1 if found else 0
                existing.last_searched = datetime.now(timezone.utc).replace(tzinfo=None)
                if user_id and not existing.user_id:
                    existing.user_id = user_id
            else:
                # Create new entry
                history_entry = SearchHistory(
                    query=query,
                    query_type=query_type.value,
                    result_found=1 if found else 0,
                    search_count=1,
                    user_id=user_id,
                    created_at=datetime.now(timezone.utc).replace(tzinfo=None),
                    last_searched=datetime.now(timezone.utc).replace(tzinfo=None),
                )
                self.db.add(history_entry)

            self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error recording search history: {e}")
            raise

    async def get_popular_searches(self, limit: int = 10) -> List[dict]:
        """Get most popular searches."""
        try:
            results = (
                self.db.query(
                    SearchHistory.query, func.count(SearchHistory.id).label("count")
                )
                .group_by(SearchHistory.query)
                .order_by(func.count(SearchHistory.id).desc())
                .limit(limit)
                .all()
            )
            return [{"query": r.query, "count": r.count} for r in results]
        except Exception as e:
            logger.error(f"Error getting popular searches: {e}")
            return []

    async def get_autocomplete_suggestions(
        self, prefix: str, limit: int = 10
    ) -> List[str]:
        """Get autocomplete suggestions."""
        try:
            results = (
                self.db.query(SearchHistory.query)
                .filter(SearchHistory.query.ilike(f"{prefix}%"))
                .group_by(SearchHistory.query)
                .order_by(func.count(SearchHistory.id).desc())
                .limit(limit)
                .all()
            )
            return [r.query for r in results]
        except Exception as e:
            logger.error(f"Error getting autocomplete suggestions: {e}")
            return []

    async def get_user_history(self, user_id: str, limit: int = 10) -> List[dict]:
        """Get user's search history."""
        try:
            results = (
                self.db.query(SearchHistory)
                .filter(SearchHistory.user_id == user_id)
                .order_by(SearchHistory.last_searched.desc())
                .limit(limit)
                .all()
            )

            return [
                {
                    "query": r.query,
                    "query_type": r.query_type,
                    "found": bool(r.result_found),
                    "search_count": r.search_count,
                    "last_searched": r.last_searched.isoformat()
                    if r.last_searched
                    else None,
                }
                for r in results
            ]
        except Exception as e:
            logger.error(f"Error getting user history: {e}")
            return []


class PostgresSymbolMappingRepository(ISymbolMappingRepository):
    """PostgreSQL implementation for symbol mappings (to be extended)."""

    def __init__(self, db: Session):
        self.db = db

    async def get_yahoo_symbol(
        self, isin: Optional[str] = None, wkn: Optional[str] = None
    ) -> Optional[str]:
        """Get Yahoo symbol from cache (future implementation)."""
        # TODO: Implement with dedicated mapping table
        return None

    async def save_mapping(
        self,
        yahoo_symbol: str,
        isin: Optional[str] = None,
        wkn: Optional[str] = None,
        company_name: Optional[str] = None,
    ) -> None:
        """Save symbol mapping (future implementation)."""
        # TODO: Implement with dedicated mapping table
        pass

    async def get_all_mappings(self) -> List[dict]:
        """Get all mappings (future implementation)."""
        # TODO: Implement with dedicated mapping table
        return []
