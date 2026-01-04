"""
Shared dependencies for the application.

Provides dependency injection functions with proper state management
and explicit typing for use across routers.
"""

from typing import TYPE_CHECKING, Optional

import redis.asyncio as aioredis
from fastapi import HTTPException, Request, status

if TYPE_CHECKING:
    from .services.stock_service import StockSearchService


class ServiceContainer:
    """
    Service container for dependency injection.

    Provides centralized service management with proper initialization
    checks and error handling.
    """

    def __init__(self) -> None:
        """Initialize empty service container."""
        self._stock_service: Optional["StockSearchService"] = None

    def register_stock_service(self, service: "StockSearchService") -> None:
        """
        Register stock search service.

        Args:
            service: StockSearchService instance

        Raises:
            ValueError: If service is already registered
        """
        if self._stock_service is not None:
            raise ValueError("Stock service already registered")
        self._stock_service = service

    def get_stock_service(self) -> "StockSearchService":
        """
        Get registered stock service.

        Returns:
            StockSearchService instance

        Raises:
            HTTPException: If service not initialized (503 status)
        """
        if self._stock_service is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service not initialized. Please try again later.",
            )
        return self._stock_service


_container = ServiceContainer()


def get_service_container() -> ServiceContainer:
    """Get global service container instance."""
    return _container


async def get_stock_service() -> "StockSearchService":
    """
    Dependency injection function for stock service.

    Returns:
        StockSearchService instance

    Raises:
        HTTPException: If service not available
    """
    return _container.get_stock_service()


async def get_redis_client(request: Request) -> aioredis.Redis:
    """
    Dependency injection function for Redis client.

    Retrieves Redis client from the application state's Redis manager.

    Args:
        request: FastAPI request object

    Returns:
        Async Redis client instance

    Raises:
        HTTPException: If Redis not available
    """
    if not hasattr(request.app.state, "redis_manager"):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis not available. Please try again later.",
        )

    redis_manager = request.app.state.redis_manager
    return await redis_manager.get_client()
