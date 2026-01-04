"""
Stock repository interface (Abstract Base Class).

Defines the contract for stock data persistence and retrieval
independent of the underlying storage mechanism.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional

from ..domain.entities import IdentifierType, Stock, StockIdentifier


class IStockRepository(ABC):
    """
    Abstract repository interface for stock data operations.

    This interface defines all stock data access methods without
    implementation details, enabling dependency inversion.
    """

    @abstractmethod
    async def find_by_identifier(self, identifier: StockIdentifier) -> Optional[Stock]:
        """
        Find stock by any identifier (ISIN, WKN, Symbol, Name).

        Args:
            identifier: Stock identifier to search for

        Returns:
            Stock entity if found, None otherwise
        """
        pass

    @abstractmethod
    async def find_by_name(self, name: str, limit: int = 10) -> List[Stock]:
        """
        Search stocks by company name (fuzzy matching).

        Args:
            name: Company name or partial name
            limit: Maximum number of results

        Returns:
            List of matching stocks, sorted by relevance
        """
        pass

    @abstractmethod
    async def save(self, stock: Stock) -> Stock:
        """
        Save or update stock data.

        Args:
            stock: Stock entity to persist

        Returns:
            The saved stock entity
        """
        pass

    @abstractmethod
    async def delete_expired(self, before: datetime) -> int:
        """
        Delete expired cache entries.

        Args:
            before: Delete entries older than this timestamp

        Returns:
            Number of deleted entries
        """
        pass

    @abstractmethod
    async def get_cache_stats(self) -> dict:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache metrics (hits, misses, size, etc.)
        """
        pass

    @abstractmethod
    async def count_user_favorites(self, user_id: str) -> int:
        """
        Count number of favorites for a user.

        Args:
            user_id: User UUID

        Returns:
            Number of favorites
        """
        pass

    @abstractmethod
    async def add_favorite(self, user_id: str, symbol: str) -> None:
        """
        Add stock to user favorites.

        Args:
            user_id: User UUID
            symbol: Stock symbol
        """
        pass

    @abstractmethod
    async def remove_favorite(self, user_id: str, symbol: str) -> None:
        """
        Remove stock from user favorites.

        Args:
            user_id: User UUID
            symbol: Stock symbol
        """
        pass

    @abstractmethod
    async def get_user_favorites(self, user_id: str) -> List[str]:
        """
        Get list of user's favorite symbols.

        Args:
            user_id: User UUID

        Returns:
            List of stock symbols
        """
        pass


class ISymbolMappingRepository(ABC):
    """
    Repository for ISIN/WKN to Yahoo Symbol mappings.

    This persistent mapping reduces API calls and improves lookup speed.
    """

    @abstractmethod
    async def get_yahoo_symbol(
        self, isin: Optional[str] = None, wkn: Optional[str] = None
    ) -> Optional[str]:
        """
        Get Yahoo Finance symbol from ISIN or WKN.

        Args:
            isin: International Securities Identification Number
            wkn: German securities identification number

        Returns:
            Yahoo Finance symbol (e.g., 'BMW.DE') or None
        """
        pass

    @abstractmethod
    async def save_mapping(
        self,
        yahoo_symbol: str,
        isin: Optional[str] = None,
        wkn: Optional[str] = None,
        company_name: Optional[str] = None,
    ) -> None:
        """
        Save symbol mapping for future lookups.

        Args:
            yahoo_symbol: Yahoo Finance symbol
            isin: International Securities Identification Number
            wkn: German securities identification number
            company_name: Company name
        """
        pass

    @abstractmethod
    async def get_all_mappings(self) -> List[dict]:
        """
        Get all symbol mappings.

        Returns:
            List of mapping dictionaries
        """
        pass


class ISearchHistoryRepository(ABC):
    """
    Repository for search history and analytics.

    Tracks search queries for analytics and autocomplete suggestions.
    """

    @abstractmethod
    async def record_search(
        self,
        query: str,
        query_type: IdentifierType,
        found: bool,
        response_time_ms: float,
        user_id: Optional[str] = None,
    ) -> None:
        """
        Record a search query for analytics.

        Args:
            query: The search query
            query_type: Type of identifier
            found: Whether the search was successful
            response_time_ms: Response time in milliseconds
            user_id: Optional user ID for tracking user-specific history
        """
        pass

    @abstractmethod
    async def get_popular_searches(self, limit: int = 10) -> List[dict]:
        """
        Get most popular search queries.

        Args:
            limit: Maximum number of results

        Returns:
            List of popular queries with counts
        """
        pass

    @abstractmethod
    async def get_autocomplete_suggestions(
        self, prefix: str, limit: int = 10
    ) -> List[str]:
        """
        Get autocomplete suggestions based on search history.

        Args:
            prefix: Query prefix
            limit: Maximum number of suggestions

        Returns:
            List of suggested completions
        """
        pass

    @abstractmethod
    async def get_user_history(self, user_id: str, limit: int = 10) -> List[dict]:
        """
        Get user's search history.

        Args:
            user_id: User UUID
            limit: Maximum number of results

        Returns:
            List of search history entries with query and timestamp
        """
        pass

    @abstractmethod
    async def get_search_stats(self) -> dict:
        """
        Get search statistics for relevance scoring.

        Returns:
            Dictionary mapping stock symbols to search counts
            Format: {"AAPL": 1000, "MSFT": 800, ...}
        """
        pass
