"""
Shared dependencies for the application.

Provides dependency injection functions used across routers.
"""

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .services.stock_service import StockSearchService

# Global service instance (set by main app)
_stock_service: Optional["StockSearchService"] = None


def set_stock_service(service: "StockSearchService") -> None:
    """
    Set the global stock service instance.

    Called by main app during startup.
    """
    global _stock_service
    _stock_service = service


async def get_stock_service() -> "StockSearchService":
    """
    Get stock service instance for dependency injection.

    Used by all routers that need the stock service.
    """
    if _stock_service is None:
        raise RuntimeError("Stock service not initialized")
    return _stock_service
