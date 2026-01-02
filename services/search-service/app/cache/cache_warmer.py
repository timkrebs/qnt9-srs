"""
Cache warmer for pre-populating memory cache on startup.

Loads the most popular stocks into memory for ultra-fast access.
"""

import logging

from app.cache.memory_cache import MemoryStockCache
from app.database import get_db
from app.domain.entities import (
    DataSource,
    Stock,
    StockIdentifier,
    StockMetadata,
    StockPrice,
)
from app.models import StockCache, StockSearchIndex
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class CacheWarmer:
    """
    Pre-populates memory cache with popular stocks.

    Loads stocks based on popularity score from stock_search_index
    and current data from stock_cache.
    """

    def __init__(self, db: Session, memory_cache: MemoryStockCache):
        """
        Initialize cache warmer.

        Args:
            db: Database session
            memory_cache: Memory cache instance to populate
        """
        self.db = db
        self.memory_cache = memory_cache

    def warmup(self, max_stocks: int = 1000) -> int:
        """
        Warm up cache with most popular stocks.

        Args:
            max_stocks: Maximum number of stocks to pre-load

        Returns:
            Number of stocks loaded into cache
        """
        logger.info(f"Starting cache warmup for top {max_stocks} stocks...")

        try:
            # Get top stocks by popularity from search index
            popular_stocks = (
                self.db.query(StockSearchIndex)
                .order_by(StockSearchIndex.popularity_score.desc())
                .limit(max_stocks)
                .all()
            )

            logger.info(f"Found {len(popular_stocks)} popular stocks to cache")

            loaded_count = 0
            for stock_index in popular_stocks:
                # Get current data from stock_cache
                stock_cache = (
                    self.db.query(StockCache)
                    .filter(StockCache.symbol == stock_index.symbol)
                    .order_by(StockCache.created_at.desc())
                    .first()
                )

                if stock_cache and not stock_cache.is_expired():
                    # Convert to StockData entity
                    stock_data = self._convert_to_stock_data(stock_cache)

                    # Cache with multiple keys for flexibility
                    keys = [stock_cache.symbol.upper()]
                    if stock_cache.isin:
                        keys.append(stock_cache.isin.upper())
                    if stock_cache.wkn:
                        keys.append(stock_cache.wkn.upper())

                    for key in keys:
                        self.memory_cache.set(key, stock_data, ttl_minutes=5)

                    loaded_count += 1

            logger.info(f"Cache warmup complete: {loaded_count} stocks loaded")
            return loaded_count

        except Exception as e:
            logger.error(f"Error during cache warmup: {e}")
            return 0

    def warmup_from_search_history(self, max_stocks: int = 500) -> int:
        """
        Warm up cache based on recent search history.

        Args:
            max_stocks: Maximum number of stocks to pre-load

        Returns:
            Number of stocks loaded into cache
        """
        logger.info(f"Warming up cache from search history (top {max_stocks})...")

        try:
            # Get most searched symbols from history
            result = self.db.execute(
                text(
                    """
                    SELECT query, SUM(search_count) as total_searches
                    FROM search_history
                    WHERE result_found = 1
                    GROUP BY query
                    ORDER BY total_searches DESC
                    LIMIT :limit
                """
                ),
                {"limit": max_stocks},
            )

            loaded_count = 0
            for row in result:
                query = row[0].upper()

                # Try to find in stock_cache
                stock_cache = (
                    self.db.query(StockCache)
                    .filter(
                        (StockCache.symbol == query)
                        | (StockCache.isin == query)
                        | (StockCache.wkn == query)
                    )
                    .order_by(StockCache.created_at.desc())
                    .first()
                )

                if stock_cache and not stock_cache.is_expired():
                    stock_data = self._convert_to_stock_data(stock_cache)
                    self.memory_cache.set(query, stock_data, ttl_minutes=5)
                    loaded_count += 1

            logger.info(f"Search history warmup complete: {loaded_count} stocks loaded")
            return loaded_count

        except Exception as e:
            logger.error(f"Error during search history warmup: {e}")
            return 0

    def _convert_to_stock_data(self, stock_cache: StockCache) -> Stock:
        """
        Convert StockCache model to Stock entity.

        Args:
            stock_cache: StockCache database model

        Returns:
            Stock entity
        """
        from decimal import Decimal

        identifier = StockIdentifier(
            symbol=stock_cache.symbol,
            isin=stock_cache.isin,
            wkn=stock_cache.wkn,
            name=stock_cache.name,
        )

        price = StockPrice(
            current=Decimal(str(stock_cache.current_price or 0.0)),
            currency=stock_cache.currency or "USD",
        )

        metadata = StockMetadata(
            exchange=stock_cache.exchange or "Unknown",
            sector=stock_cache.sector,
            industry=stock_cache.industry,
            market_cap=stock_cache.market_cap,
        )

        return Stock(
            identifier=identifier,
            price=price,
            metadata=metadata,
            data_source=(
                DataSource(stock_cache.data_source)
                if stock_cache.data_source
                else DataSource.YAHOO_FINANCE
            ),
            last_updated=stock_cache.created_at,
        )


def warmup_cache_on_startup(max_stocks: int = 1000) -> None:
    """
    Warm up cache on application startup.

    Args:
        max_stocks: Maximum number of stocks to pre-load
    """
    from app.cache.memory_cache import get_memory_cache

    logger.info("Starting cache warmup on application startup...")

    db = None
    try:
        db = next(get_db())
        memory_cache = get_memory_cache()
        warmer = CacheWarmer(db, memory_cache)

        # Warmup from popularity
        popularity_count = warmer.warmup(max_stocks=max_stocks)

        # Warmup from search history (additional boost)
        history_count = warmer.warmup_from_search_history(max_stocks=500)

        stats = memory_cache.get_stats()
        logger.info(
            f"Cache warmup finished: {stats['size']} stocks cached "
            f"({popularity_count} from popularity, {history_count} from history)"
        )

    except Exception as e:
        logger.error(f"Failed to warm up cache on startup: {e}")
    finally:
        if db:
            db.close()
