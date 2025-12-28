"""
External stock API client interface.

Defines the contract for stock data providers (Yahoo Finance, Alpha Vantage, etc.).
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from ..domain.entities import Stock, StockIdentifier


class IStockAPIClient(ABC):
    """
    Abstract interface for external stock data API clients.

    Implementations must provide methods to fetch stock data
    from external sources with proper error handling.
    """

    @abstractmethod
    async def fetch_stock(self, identifier: StockIdentifier) -> Optional[Stock]:
        """
        Fetch stock data by identifier.

        Args:
            identifier: Stock identifier (ISIN, WKN, Symbol)

        Returns:
            Stock entity with current data, or None if not found

        Raises:
            ExternalServiceException: If API call fails
            RateLimitExceededException: If rate limit exceeded
        """
        pass

    @abstractmethod
    async def search_by_name(self, name: str, limit: int = 10) -> List[Stock]:
        """
        Search stocks by company name.

        Args:
            name: Company name or partial name
            limit: Maximum number of results

        Returns:
            List of matching stocks

        Raises:
            ExternalServiceException: If API call fails
        """
        pass

    @abstractmethod
    def get_health_status(self) -> dict:
        """
        Get API client health status.

        Returns:
            Dictionary with health metrics (availability, rate limits, etc.)
        """
        pass
