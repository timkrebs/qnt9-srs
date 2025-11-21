"""
Business logic service layer.

Orchestrates stock search operations using repositories and external APIs,
implementing multi-layer caching and fault tolerance.
"""

import asyncio
import logging
import time
from typing import List, Optional

from ..domain.entities import IdentifierType, Stock, StockIdentifier
from ..domain.exceptions import StockNotFoundException, ValidationException
from ..infrastructure.stock_api_client import IStockAPIClient
from ..repositories.stock_repository import ISearchHistoryRepository, IStockRepository

logger = logging.getLogger(__name__)


class StockSearchService:
    """
    Stock search service with multi-layer caching.

    Implements the following caching strategy:
    1. Check Redis (fast in-memory)
    2. Check PostgreSQL (persistent cache)
    3. Fetch from external API (Yahoo Finance)
    4. Save to both caches
    """

    def __init__(
        self,
        redis_repo: IStockRepository,
        postgres_repo: IStockRepository,
        api_client: IStockAPIClient,
        history_repo: ISearchHistoryRepository,
    ):
        """
        Initialize search service.

        Args:
            redis_repo: Redis repository for Layer 1 cache
            postgres_repo: PostgreSQL repository for Layer 2 cache
            api_client: External API client
            history_repo: Search history repository
        """
        self.redis_repo = redis_repo
        self.postgres_repo = postgres_repo
        self.api_client = api_client
        self.history_repo = history_repo

    async def search(self, query: str, user_id: Optional[str] = None) -> Stock:
        """
        Search for stock by any identifier.

        Implements multi-layer caching:
        - Layer 1: Redis (5 min TTL)
        - Layer 2: PostgreSQL (5 min TTL)
        - Layer 3: External API

        Args:
            query: Search query (ISIN, WKN, Symbol, or Name)

        Returns:
            Stock entity with current data

        Raises:
            StockNotFoundException: If stock not found in any source
            ValidationException: If query is invalid
        """
        start_time = time.time()

        # Validate and normalize query
        query = query.strip()
        if not query:
            raise ValidationException("query", query, "Query cannot be empty")

        # Detect identifier type
        identifier_type = StockIdentifier.detect_type(query.upper())

        # For NAME queries, use search_by_name and return first result
        if identifier_type == IdentifierType.NAME:
            logger.info(f"Detected name search for: {query}")
            results = await self.search_by_name(query, limit=1)
            if results:
                await self._record_search(query, identifier_type, True, start_time, user_id)
                return results[0]
            else:
                await self._record_search(query, identifier_type, False, start_time, user_id)
                raise StockNotFoundException(query, "name")

        # Build identifier object for ISIN/WKN/Symbol searches
        identifier = self._build_identifier(query, identifier_type)

        try:
            # Layer 1: Check Redis
            stock = await self.redis_repo.find_by_identifier(identifier)
            if stock:
                logger.info(f"Found in Redis: {query}")
                await self._record_search(query, identifier_type, True, start_time, user_id)
                return stock

            # Layer 2: Check PostgreSQL
            stock = await self.postgres_repo.find_by_identifier(identifier)
            if stock:
                logger.info(f"Found in PostgreSQL: {query}")
                # Save to Redis for next time
                await self.redis_repo.save(stock)
                await self._record_search(query, identifier_type, True, start_time, user_id)
                return stock

            # Layer 3: Fetch from external API
            logger.info(f"Fetching from external API: {query}")
            stock = await self.api_client.fetch_stock(identifier)

            if not stock:
                # Fallback for ISIN/WKN: Try name search if available
                if identifier_type in [IdentifierType.ISIN, IdentifierType.WKN]:
                    logger.info(
                        f"{identifier_type.value} lookup failed for {query}, "
                        f"trying alternative search methods"
                    )

                    # Try to get company name from PostgreSQL cache (partial match)
                    # This might help if we've seen this ISIN before with a different query
                    try:
                        name_results = await self.postgres_repo.find_by_name(query[:8], limit=5)
                        if name_results:
                            logger.info(
                                f"Found {len(name_results)} potential matches in cache "
                                f"for {identifier_type.value} {query}"
                            )
                            # Return first match and cache it with the new identifier
                            stock = name_results[0]
                            await self.redis_repo.save(stock)
                            await self._record_search(
                                query, identifier_type, True, start_time, user_id
                            )
                            return stock
                    except Exception as e:
                        logger.debug(f"Cache lookup failed during fallback: {e}")

                await self._record_search(query, identifier_type, False, start_time, user_id)
                raise StockNotFoundException(query, identifier_type.value)

            # Save to both caches
            await self.postgres_repo.save(stock)
            await self.redis_repo.save(stock)

            await self._record_search(query, identifier_type, True, start_time, user_id)
            return stock

        except StockNotFoundException:
            raise
        except Exception as e:
            logger.error(f"Error during stock search: {e}")
            await self._record_search(query, identifier_type, False, start_time, user_id)
            raise

    async def search_by_name(self, name: str, limit: int = 10) -> List[Stock]:
        """
        Search stocks by company name.

        Performs fuzzy matching and returns multiple results.

        Args:
            name: Company name or partial name
            limit: Maximum number of results

        Returns:
            List of matching stocks, sorted by relevance
        """
        start_time = time.time()

        # Validate
        if not name or len(name) < 3:
            raise ValidationException("name", name, "Name must be at least 3 characters")

        try:
            # Check PostgreSQL cache first
            results = await self.postgres_repo.find_by_name(name, limit)

            if results:
                logger.info(f"Found {len(results)} results in PostgreSQL for: {name}")
                await self._record_search(name, IdentifierType.NAME, True, start_time)
                return results

            # Fetch from external API
            logger.info(f"Searching external API for name: {name}")
            results = await self.api_client.search_by_name(name, limit)

            # Cache all results
            for stock in results:
                await self.postgres_repo.save(stock)
                await self.redis_repo.save(stock)

            found = len(results) > 0
            await self._record_search(name, IdentifierType.NAME, found, start_time)

            return results

        except Exception as e:
            logger.error(f"Error during name search: {e}")
            await self._record_search(name, IdentifierType.NAME, False, start_time)
            raise

    async def get_cache_statistics(self) -> dict:
        """
        Get statistics from all cache layers.

        Returns:
            Dictionary with cache metrics
        """
        redis_stats = await self.redis_repo.get_cache_stats()
        postgres_stats = await self.postgres_repo.get_cache_stats()
        api_health = self.api_client.get_health_status()

        return {
            "redis": redis_stats,
            "postgresql": postgres_stats,
            "external_api": api_health,
        }

    def _build_identifier(self, query: str, id_type: IdentifierType) -> StockIdentifier:
        """Build StockIdentifier from query and type."""
        query_upper = query.upper()

        if id_type == IdentifierType.ISIN:
            return StockIdentifier(isin=query_upper)
        elif id_type == IdentifierType.WKN:
            return StockIdentifier(wkn=query_upper)
        elif id_type == IdentifierType.SYMBOL:
            return StockIdentifier(symbol=query_upper)
        else:
            # Name - preserve original casing
            return StockIdentifier(name=query)

    async def _record_search(
        self,
        query: str,
        query_type: IdentifierType,
        found: bool,
        start_time: float,
        user_id: Optional[str] = None,
    ) -> None:
        """Record search in history for analytics."""
        try:
            response_time_ms = (time.time() - start_time) * 1000
            await self.history_repo.record_search(
                query=query,
                query_type=query_type,
                found=found,
                response_time_ms=response_time_ms,
                user_id=user_id,
            )
        except Exception as e:
            # Don't fail the request if history recording fails
            logger.warning(f"Failed to record search history: {e}")

    async def batch_search(self, symbols: List[str], user_id: Optional[str] = None) -> List[Stock]:
        """
        Search multiple stocks efficiently using concurrent requests.

        Args:
            symbols: List of stock symbols to search
            user_id: Optional user ID for history tracking

        Returns:
            List of Stock objects (excludes symbols that failed)

        Example:
            stocks = await service.batch_search(["AAPL", "MSFT", "GOOGL"], user_id="user123")
        """
        logger.info(f"Batch search for {len(symbols)} symbols")

        # Create concurrent search tasks
        tasks = [self.search(symbol, user_id=user_id) for symbol in symbols]

        # Execute all searches concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out exceptions and return only successful Stock objects
        stocks = []
        for i, result in enumerate(results):
            if isinstance(result, Stock):
                stocks.append(result)
            elif isinstance(result, Exception):
                logger.warning(f"Failed to fetch {symbols[i]}: {result}")

        logger.info(f"Batch search completed: {len(stocks)}/{len(symbols)} successful")
        return stocks

    async def get_user_search_history(self, user_id: str, limit: int = 10) -> List[dict]:
        """
        Get user's recent search history.

        Args:
            user_id: User UUID
            limit: Maximum number of results

        Returns:
            List of search history entries with query, timestamp, and result

        Example:
            history = await service.get_user_search_history("user123", limit=20)
        """
        try:
            history = await self.history_repo.get_user_history(user_id, limit)
            logger.info(f"Retrieved {len(history)} history entries for user {user_id}")
            return history
        except Exception as e:
            logger.error(f"Error fetching user history: {e}")
            return []

    async def add_to_favorites(self, user_id: str, symbol: str, tier: str) -> None:
        """
        Add stock to user favorites with tier limits.

        Args:
            user_id: User UUID
            symbol: Stock symbol
            tier: User tier (free or paid)

        Raises:
            ValidationException: If user exceeds tier limit

        Example:
            await service.add_to_favorites("user123", "AAPL", "free")
        """
        max_favorites = 20 if tier == "paid" else 5

        # Check current favorites count
        current_count = await self.postgres_repo.count_user_favorites(user_id)

        if current_count >= max_favorites:
            raise ValidationException(
                "favorites",
                symbol,
                f"{tier.title()} tier limited to {max_favorites} favorites. Upgrade for more.",
            )

        # Add to favorites
        await self.postgres_repo.add_favorite(user_id, symbol)
        logger.info(f"Added {symbol} to favorites for user {user_id}")

    async def remove_from_favorites(self, user_id: str, symbol: str) -> None:
        """
        Remove stock from user favorites.

        Args:
            user_id: User UUID
            symbol: Stock symbol

        Example:
            await service.remove_from_favorites("user123", "AAPL")
        """
        await self.postgres_repo.remove_favorite(user_id, symbol)
        logger.info(f"Removed {symbol} from favorites for user {user_id}")

    async def get_favorites(self, user_id: str) -> List[Stock]:
        """
        Get user's favorite stocks with current prices.

        Args:
            user_id: User UUID

        Returns:
            List of Stock objects for favorited symbols

        Example:
            favorites = await service.get_favorites("user123")
        """
        # Get favorite symbols from database
        symbols = await self.postgres_repo.get_user_favorites(user_id)

        if not symbols:
            return []

        # Batch search for all favorites to get current prices
        stocks = await self.batch_search(symbols, user_id=user_id)

        logger.info(f"Retrieved {len(stocks)} favorites for user {user_id}")
        return stocks
