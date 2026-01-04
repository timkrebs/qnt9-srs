"""
Business logic service layer.

Orchestrates stock search operations using repositories and external APIs,
implementing multi-layer caching and fault tolerance.
"""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional, Tuple

from ..cache.memory_cache import get_memory_cache
from ..domain.entities import IdentifierType, Stock, StockIdentifier
from ..domain.exceptions import StockNotFoundException, ValidationException
from ..infrastructure.stock_api_client import IStockAPIClient
from ..repositories.stock_repository import (ISearchHistoryRepository,
                                             IStockRepository)
from ..search import FuzzyMatcher, RelevanceScorer, SearchMatch

logger = logging.getLogger(__name__)


class StockSearchService:
    """
    Stock search service with multi-layer caching.

    Implements the following caching strategy:
    0. Check In-Memory LRU (ultra-fast, ~1μs)
    1. Check Redis (fast in-memory, ~1ms)
    2. Check PostgreSQL (persistent cache, ~10ms)
    3. Fetch from external API (Yahoo Finance, ~500ms)
    4. Save to all caches
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
        self.memory_cache = get_memory_cache()  # Layer 0 cache

        # Phase 4: Intelligent search components
        self.fuzzy_matcher = FuzzyMatcher(symbol_threshold=0.75, name_threshold=0.70)
        self.relevance_scorer = RelevanceScorer()
        self._search_stats_cache: Optional[Dict[str, Any]] = None
        self._stats_last_updated = 0.0

    async def search(self, query: str, user_id: Optional[str] = None) -> Stock:
        """
        Search for stock by any identifier.

        Implements multi-layer caching:
        - Layer 0: In-Memory LRU (~1μs)
        - Layer 1: Redis (5 min TTL, ~1ms)
        - Layer 2: PostgreSQL (5 min TTL, ~10ms)
        - Layer 3: External API (~500ms)

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
                await self._record_search(
                    query, identifier_type, True, start_time, user_id
                )
                return results[0]
            else:
                await self._record_search(
                    query, identifier_type, False, start_time, user_id
                )
                raise StockNotFoundException(query, "name")

        # Build identifier object for ISIN/WKN/Symbol searches
        identifier = self._build_identifier(query, identifier_type)
        cache_key = query.upper()

        try:
            # Layer 0: Check In-Memory LRU Cache
            cached_stock = self.memory_cache.get(cache_key)
            if cached_stock:
                logger.info(f"Found in MEMORY cache: {query}")
                await self._record_search(
                    query, identifier_type, True, start_time, user_id
                )
                return cached_stock

            # Layer 1: Check Redis
            stock = await self.redis_repo.find_by_identifier(identifier)
            if stock:
                logger.info(f"Found in Redis: {query}")
                # Save to memory cache for next time
                self.memory_cache.set(cache_key, stock)
                await self._record_search(
                    query, identifier_type, True, start_time, user_id
                )
                return stock

            # Layer 2: Check PostgreSQL
            stock = await self.postgres_repo.find_by_identifier(identifier)
            if stock:
                logger.info(f"Found in PostgreSQL: {query}")
                # Save to Redis and Memory for next time
                await self.redis_repo.save(stock)
                self.memory_cache.set(cache_key, stock)
                await self._record_search(
                    query, identifier_type, True, start_time, user_id
                )
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
                        name_results = await self.postgres_repo.find_by_name(
                            query[:8], limit=5
                        )
                        if name_results:
                            logger.info(
                                f"Found {len(name_results)} potential matches in cache "
                                f"for {identifier_type.value} {query}"
                            )
                            # Return first match and cache it with the new identifier
                            stock = name_results[0]
                            await self.redis_repo.save(stock)
                            self.memory_cache.set(cache_key, stock)
                            await self._record_search(
                                query, identifier_type, True, start_time, user_id
                            )
                            return stock
                    except Exception as e:
                        logger.debug(f"Cache lookup failed during fallback: {e}")

                await self._record_search(
                    query, identifier_type, False, start_time, user_id
                )
                raise StockNotFoundException(query, identifier_type.value)

            # Save to all caches (PostgreSQL, Redis, Memory)
            await self.postgres_repo.save(stock)
            await self.redis_repo.save(stock)
            self.memory_cache.set(cache_key, stock)

            await self._record_search(query, identifier_type, True, start_time, user_id)
            return stock

        except StockNotFoundException:
            raise
        except Exception as e:
            logger.error(f"Error during stock search: {e}")
            await self._record_search(
                query, identifier_type, False, start_time, user_id
            )
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
        if not name or len(name) < 2:
            raise ValidationException(
                "name", name, "Name must be at least 2 characters"
            )

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

    async def batch_search(
        self, symbols: List[str], user_id: Optional[str] = None
    ) -> List[Stock]:
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

    async def get_user_search_history(
        self, user_id: str, limit: int = 10
    ) -> List[dict]:
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

    def get_cache_stats(self) -> dict:
        """
        Get statistics from all cache layers.

        Returns:
            Dictionary with cache statistics
        """
        return {
            "memory_cache": self.memory_cache.get_stats(),
        }

    async def intelligent_search(
        self,
        query: str,
        limit: int = 10,
        user_id: Optional[str] = None,
        include_fuzzy: bool = True,
    ) -> List[SearchMatch]:
        """
        Intelligent search with fuzzy matching and relevance scoring.

        Multi-stage search strategy:
        1. Exact symbol match
        2. Exact name match
        3. Prefix matching
        4. Fuzzy symbol matching
        5. Fuzzy name matching

        All results ranked by relevance score.

        Args:
            query: Search query
            limit: Maximum results to return
            user_id: Optional user ID for personalization
            include_fuzzy: Whether to include fuzzy matches

        Returns:
            List of SearchMatch objects sorted by relevance
        """
        start_time = time.time()

        # Validate query
        query = query.strip()
        if not query or len(query) < 1:
            raise ValidationException("query", query, "Query cannot be empty")

        query_upper = query.upper()
        matches: List[Tuple[Stock, str, str, float]] = []

        # Stage 1: Try exact searches first
        try:
            # Exact symbol match
            identifier = StockIdentifier(symbol=query_upper)
            stock = await self.redis_repo.find_by_identifier(identifier)
            if not stock:
                stock = await self.postgres_repo.find_by_identifier(identifier)
            if stock:
                matches.append((stock, "exact", "symbol", 1.0))
                logger.info(f"Exact symbol match: {query_upper}")
        except Exception as e:
            logger.debug(f"No exact symbol match: {e}")

        # Stage 2: Search by name in database
        try:
            name_results = await self.postgres_repo.find_by_name(query, limit=limit)
            for stock in name_results:
                # Check if exact name match
                if (
                    stock.identifier.name
                    and query.lower() in stock.identifier.name.lower()
                ):
                    match_type = (
                        "exact"
                        if query.lower() == stock.identifier.name.lower()
                        else "contains"
                    )
                    matches.append((stock, match_type, "name", 1.0))
        except Exception as e:
            logger.debug(f"Name search error: {e}")

        # Stage 3: Fuzzy matching (if enabled and not enough exact matches)
        if include_fuzzy and len(matches) < limit:
            await self._add_fuzzy_matches(query, query_upper, matches, limit)

        # Stage 4: Rank results with relevance scoring
        await self._refresh_search_stats()

        # Get user history for recency boost
        user_history = []
        if user_id:
            try:
                history_entries = await self.get_user_search_history(user_id, limit=20)
                user_history = [
                    entry.get("query", "").upper() for entry in history_entries
                ]
            except Exception as e:
                logger.debug(f"Could not load user history: {e}")

        # Score and rank
        ranked_matches = self.relevance_scorer.score_batch(
            matches, user_search_history=user_history  # type: ignore[arg-type]
        )

        # Limit results
        ranked_matches = ranked_matches[:limit]

        # Record search
        latency_ms = (time.time() - start_time) * 1000
        found = len(ranked_matches) > 0
        await self._record_search(
            query, IdentifierType.NAME, found, start_time, user_id
        )

        logger.info(
            f"Intelligent search: query={query}, results={len(ranked_matches)}, "
            f"latency={latency_ms:.1f}ms"
        )

        return ranked_matches

    async def _add_fuzzy_matches(
        self,
        query: str,
        query_upper: str,
        matches: List[Tuple[Stock, str, str, float]],
        limit: int,
    ) -> None:
        """Add fuzzy matches to results list."""
        try:
            # Get candidates from database (wider search)
            candidates = await self.postgres_repo.find_by_name(query[:3], limit=50)

            # Fuzzy match against candidates
            for stock in candidates:
                # Skip if already matched
                if any(
                    m[0].identifier.symbol == stock.identifier.symbol for m in matches
                ):
                    continue

                # Try fuzzy symbol match
                if stock.identifier.symbol:
                    is_match, similarity = self.fuzzy_matcher.match_symbol(
                        query_upper, stock.identifier.symbol
                    )
                    if is_match:
                        matches.append((stock, "fuzzy", "symbol", similarity))
                        continue

                # Try fuzzy name match
                if stock.identifier.name:
                    is_match, similarity = self.fuzzy_matcher.match_name(
                        query, stock.identifier.name
                    )
                    if is_match:
                        matches.append((stock, "fuzzy", "name", similarity))

        except Exception as e:
            logger.debug(f"Fuzzy matching error: {e}")

    async def _refresh_search_stats(self) -> None:
        """Refresh search statistics for relevance scoring."""
        current_time = time.time()

        # Refresh every 5 minutes
        if current_time - self._stats_last_updated > 300:
            try:
                stats = await self.history_repo.get_search_stats()
                if stats:
                    self.relevance_scorer.update_search_stats(stats)
                    self._search_stats_cache = stats
                    self._stats_last_updated = int(current_time)
                    logger.info(f"Updated search stats: {len(stats)} symbols")
            except Exception as e:
                logger.warning(f"Failed to refresh search stats: {e}")

    async def get_search_suggestions(
        self, query: str, limit: int = 5, user_id: Optional[str] = None
    ) -> List[dict]:
        """
        Get autocomplete suggestions for partial query.

        Optimized for speed with minimal metadata.

        Args:
            query: Partial search query (min 1 character)
            limit: Maximum suggestions (default 5, max 10)
            user_id: Optional user ID for personalization

        Returns:
            List of suggestion dictionaries with symbol, name, and score
        """
        if limit > 10:
            limit = 10

        # Use intelligent search
        matches = await self.intelligent_search(
            query,
            limit=limit,
            user_id=user_id,
            include_fuzzy=len(query) >= 2,  # Only fuzzy match for 2+ chars
        )

        # Convert to lightweight suggestion format
        suggestions = []
        for match in matches:
            suggestions.append(
                {
                    "symbol": match.stock.identifier.symbol,
                    "name": match.stock.identifier.name,
                    "exchange": match.stock.metadata.exchange,
                    "relevance_score": round(match.score, 2),
                    "match_type": match.match_type,
                }
            )

        return suggestions
