"""
API routers for search service endpoints.
"""

from . import health_router, legacy_router, search_router

__all__ = ["search_router", "health_router", "legacy_router"]
