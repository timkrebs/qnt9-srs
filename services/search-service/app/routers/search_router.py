"""
Stock search API router with authentication and tier-based access control.

Handles all stock search endpoints with proper validation, error handling,
authentication, and rate limiting.
"""

from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

from ..core.auth import User, get_current_user, require_authentication
from ..core.rate_limiter import rate_limiter
from ..dependencies import get_stock_service
from ..domain.exceptions import (
    CircuitBreakerOpenException,
    RateLimitExceededException,
    StockNotFoundException,
    ValidationException,
)
from ..services.stock_service import StockSearchService

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1", tags=["search"])


# Request/Response Models
class SearchRequest(BaseModel):
    """Stock search request model."""

    query: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="ISIN, WKN, Symbol, or company name",
        json_schema_extra={"example": "US0378331005"},
    )


class StockResponse(BaseModel):
    """Stock data response model."""

    success: bool = True
    data: dict
    message: str = "Stock found successfully"
    cache_source: str = Field(description="Source: redis, postgresql, or api")
    user_tier: Optional[str] = Field(None, description="User tier (anonymous, free, paid)")


class SearchByNameRequest(BaseModel):
    """Name search request model."""

    name: str = Field(
        ...,
        min_length=3,
        max_length=100,
        description="Company name or partial name",
        json_schema_extra={"example": "Apple"},
    )
    limit: int = Field(default=10, ge=1, le=20, description="Maximum number of results")


class ErrorResponse(BaseModel):
    """Error response model."""

    success: bool = False
    error: str
    message: str
    details: dict = {}


class CacheStatsResponse(BaseModel):
    """Cache statistics response."""

    redis: dict
    postgresql: dict
    external_api: dict


@router.get(
    "/search",
    response_model=StockResponse,
    responses={
        200: {"description": "Stock found successfully"},
        401: {"description": "Authentication required", "model": ErrorResponse},
        404: {"description": "Stock not found", "model": ErrorResponse},
        429: {"description": "Rate limit exceeded", "model": ErrorResponse},
        503: {"description": "External service unavailable", "model": ErrorResponse},
    },
    summary="Search stock by identifier",
    description="""
    Search for stock using ISIN, WKN, Symbol, or company name.
    
    **Tier Features:**
    - Anonymous: Basic search, 10 requests/minute
    - Free (logged in): Search history tracking, 30 requests/minute
    - Paid: Full details + ML predictions link, 100 requests/minute
    """,
)
async def search_stock(
    request: Request,
    query: str = Query(
        ...,
        min_length=1,
        max_length=100,
        description="ISIN, WKN, Symbol, or company name",
        examples=["AAPL", "US0378331005", "865985", "Apple"],
    ),
    service: StockSearchService = Depends(get_stock_service),
    user: Optional[User] = Depends(get_current_user),
):
    """
    Search for stock by any identifier.

    Supports:
    - ISIN (12 characters, e.g., US0378331005)
    - WKN (6 characters, e.g., 865985)
    - Symbol (e.g., AAPL, MSFT)
    - Company name (e.g., Apple, Microsoft)
    """
    # Determine user tier and ID for rate limiting
    tier = user.tier if user else "anonymous"
    user_id = user.id if user else request.client.host

    # Apply tier-based rate limiting
    try:
        await rate_limiter.check_rate_limit(user_id, tier)
    except HTTPException:
        logger.warning("Rate limit exceeded", user_id=user_id, tier=tier, query=query)
        raise

    try:
        # Search with optional user ID for history tracking
        stock = await service.search(query, user_id=user.id if user else None)

        # Determine cache source
        cache_source = "api"
        if stock.cache_age_seconds:
            cache_source = "redis" if stock.cache_age_seconds < 60 else "postgresql"

        # Build response data
        response_data = stock.to_dict()

        # Enhance response for paid users with ML predictions link
        if user and user.tier == "paid":
            response_data["ml_predictions_available"] = True
            response_data["ml_predictions_url"] = f"/api/predictions/{stock.identifier.symbol}"

        return StockResponse(
            success=True,
            data=response_data,
            message="Stock found successfully",
            cache_source=cache_source,
            user_tier=tier,
        )

    except ValidationException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "success": False,
                "error": "validation_error",
                "message": e.message,
                "details": e.details,
            },
        )

    except StockNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "success": False,
                "error": "not_found",
                "message": e.message,
                "details": e.details,
            },
        )

    except RateLimitExceededException as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "success": False,
                "error": "rate_limit_exceeded",
                "message": e.message,
                "details": e.details,
            },
            headers={"Retry-After": str(e.details.get("retry_after", 60))},
        )

    except CircuitBreakerOpenException as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "success": False,
                "error": "service_unavailable",
                "message": e.message,
                "details": e.details,
            },
            headers={"Retry-After": str(e.details.get("retry_after", 60))},
        )

    except Exception as e:
        logger.error(f"Unexpected error during search: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "error": "internal_error",
                "message": "An unexpected error occurred",
                "details": {},
            },
        )


@router.get(
    "/search/batch",
    response_model=dict,
    responses={
        200: {"description": "Batch search results"},
        400: {"description": "Invalid request", "model": ErrorResponse},
        401: {"description": "Authentication required", "model": ErrorResponse},
        403: {"description": "Tier limit exceeded", "model": ErrorResponse},
    },
    summary="Batch search multiple stocks",
    description="""
    Search multiple stocks at once for efficiency.
    
    **Requires authentication.**
    - Free tier: Maximum 5 symbols per batch
    - Paid tier: Maximum 10 symbols per batch
    """,
)
async def batch_search(
    symbols: str = Query(
        ...,
        description="Comma-separated symbols (e.g., AAPL,MSFT,GOOGL)",
        examples=["AAPL,MSFT,GOOGL"],
    ),
    user: User = Depends(require_authentication),
    service: StockSearchService = Depends(get_stock_service),
):
    """
    Batch search multiple stocks at once.

    Requires authentication. Free tier: max 5, Paid tier: max 10.
    """
    # Parse and validate symbols
    symbol_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]

    if not symbol_list:
        raise HTTPException(status_code=400, detail="No symbols provided")

    # Apply tier-based limits
    max_batch = 10 if user.tier == "paid" else 5
    if len(symbol_list) > max_batch:
        raise HTTPException(
            status_code=403,
            detail=f"{user.tier.title()} tier limited to {max_batch} symbols per batch. Upgrade for more.",
        )

    try:
        # Perform batch search
        results = await service.batch_search(symbol_list, user_id=user.id)

        return {
            "success": True,
            "count": len(results),
            "requested": len(symbol_list),
            "results": [stock.to_dict() for stock in results],
            "tier": user.tier,
        }

    except Exception as e:
        logger.error(f"Batch search error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Batch search failed")


@router.get(
    "/search/history",
    response_model=dict,
    responses={
        200: {"description": "Search history"},
        401: {"description": "Authentication required", "model": ErrorResponse},
    },
    summary="Get user search history",
    description="Retrieve the authenticated user's recent search history.",
)
async def get_search_history(
    limit: int = Query(10, ge=1, le=50, description="Maximum number of results"),
    user: User = Depends(require_authentication),
    service: StockSearchService = Depends(get_stock_service),
):
    """
    Get user's search history.

    Requires authentication.
    """
    try:
        history = await service.get_user_search_history(user.id, limit)

        return {
            "success": True,
            "count": len(history),
            "history": history,
            "user_tier": user.tier,
        }

    except Exception as e:
        logger.error(f"Error fetching search history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve search history")


@router.post(
    "/favorites/{symbol}",
    response_model=dict,
    responses={
        201: {"description": "Added to favorites"},
        400: {"description": "Invalid symbol", "model": ErrorResponse},
        401: {"description": "Authentication required", "model": ErrorResponse},
        403: {"description": "Favorites limit exceeded", "model": ErrorResponse},
    },
    summary="Add stock to favorites",
    description="""
    Add a stock to your favorites for quick access.
    
    **Requires authentication.**
    - Free tier: Maximum 5 favorites
    - Paid tier: Maximum 20 favorites
    """,
    status_code=status.HTTP_201_CREATED,
)
async def add_to_favorites(
    symbol: str,
    user: User = Depends(require_authentication),
    service: StockSearchService = Depends(get_stock_service),
):
    """
    Add stock to favorites (quick access).

    Requires authentication. Free: 5 max, Paid: 20 max.
    """
    symbol = symbol.upper().strip()

    try:
        await service.add_to_favorites(user.id, symbol, user.tier)

        return {
            "success": True,
            "message": f"{symbol} added to favorites",
            "symbol": symbol,
            "tier": user.tier,
        }

    except ValidationException as e:
        raise HTTPException(status_code=403, detail=e.message)
    except Exception as e:
        logger.error(f"Error adding to favorites: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to add to favorites")


@router.delete(
    "/favorites/{symbol}",
    response_model=dict,
    responses={
        200: {"description": "Removed from favorites"},
        401: {"description": "Authentication required", "model": ErrorResponse},
        404: {"description": "Symbol not in favorites", "model": ErrorResponse},
    },
    summary="Remove stock from favorites",
    description="Remove a stock from your favorites list.",
)
async def remove_from_favorites(
    symbol: str,
    user: User = Depends(require_authentication),
    service: StockSearchService = Depends(get_stock_service),
):
    """Remove stock from favorites."""
    symbol = symbol.upper().strip()

    try:
        await service.remove_from_favorites(user.id, symbol)

        return {
            "success": True,
            "message": f"{symbol} removed from favorites",
            "symbol": symbol,
        }

    except Exception as e:
        logger.error(f"Error removing from favorites: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to remove from favorites")


@router.get(
    "/favorites",
    response_model=dict,
    responses={
        200: {"description": "User favorites"},
        401: {"description": "Authentication required", "model": ErrorResponse},
    },
    summary="Get user favorites",
    description="Retrieve all stocks in the authenticated user's favorites list with current prices.",
)
async def get_favorites(
    user: User = Depends(require_authentication),
    service: StockSearchService = Depends(get_stock_service),
):
    """Get user's favorite stocks with current prices."""
    try:
        favorites = await service.get_favorites(user.id)

        return {
            "success": True,
            "count": len(favorites),
            "favorites": [stock.to_dict() for stock in favorites],
            "tier": user.tier,
            "max_favorites": 20 if user.tier == "paid" else 5,
        }

    except Exception as e:
        logger.error(f"Error fetching favorites: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve favorites")


@router.post(
    "/search/name",
    response_model=dict,
    responses={
        200: {"description": "Search results"},
        400: {"description": "Invalid request", "model": ErrorResponse},
    },
    summary="Search stocks by company name",
    description="Fuzzy search for stocks by company name, returns multiple results",
)
async def search_by_name(
    request: SearchByNameRequest,
    service: StockSearchService = Depends(get_stock_service),
):
    """
    Search stocks by company name.

    Performs fuzzy matching and returns up to `limit` results,
    sorted by relevance.
    """
    try:
        stocks = await service.search_by_name(request.name, request.limit)

        return {
            "success": True,
            "count": len(stocks),
            "results": [stock.to_dict() for stock in stocks],
            "message": f"Found {len(stocks)} matching stocks",
        }

    except ValidationException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "success": False,
                "error": "validation_error",
                "message": e.message,
                "details": e.details,
            },
        )

    except Exception as e:
        logger.error(f"Unexpected error during name search: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "error": "internal_error",
                "message": "An unexpected error occurred",
                "details": {},
            },
        )


@router.get(
    "/suggestions",
    response_model=dict,
    responses={
        200: {"description": "Autocomplete suggestions"},
        400: {"description": "Invalid request", "model": ErrorResponse},
    },
    summary="Get autocomplete suggestions",
    description="Get stock autocomplete suggestions as user types (min 2 characters)",
)
async def get_suggestions(
    query: str = Query(
        ...,
        min_length=2,
        max_length=100,
        description="Partial stock name, symbol, or ISIN",
        examples=["App", "MSFT", "DE000"],
    ),
    limit: int = Query(
        default=8,
        ge=1,
        le=15,
        description="Maximum number of suggestions",
    ),
    service: StockSearchService = Depends(get_stock_service),
):
    """
    Get autocomplete suggestions for stock search.

    Returns quick suggestions based on partial input to provide
    a Yahoo Finance-like autocomplete experience.
    Optimized for speed - uses cache-first strategy.
    """
    try:
        if len(query.strip()) < 2:
            return {
                "success": True,
                "suggestions": [],
                "count": 0,
            }

        stocks = await service.search_by_name(query, limit=limit)

        suggestions = [
            {
                "symbol": stock.identifier.symbol,
                "name": stock.identifier.name,
                "exchange": stock.metadata.exchange or "N/A",
                "price": float(stock.price.current) if stock.price.current else None,
                "currency": stock.price.currency,
                "query": stock.identifier.symbol,
            }
            for stock in stocks
        ]

        return {
            "success": True,
            "suggestions": suggestions,
            "count": len(suggestions),
        }

    except ValidationException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "success": False,
                "error": "validation_error",
                "message": e.message,
            },
        )

    except Exception as e:
        logger.error(f"Error getting suggestions: {e}", exc_info=True)
        return {
            "success": True,
            "suggestions": [],
            "count": 0,
        }


@router.get(
    "/stats/cache",
    response_model=CacheStatsResponse,
    summary="Get cache statistics",
    description="Retrieve statistics from all cache layers and external API status",
)
async def get_cache_stats(service: StockSearchService = Depends(get_stock_service)):
    """Get cache and API health statistics."""
    try:
        stats = await service.get_cache_statistics()
        return stats
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "error": "internal_error",
                "message": "Failed to retrieve cache statistics",
            },
        )


@router.get(
    "/stats/rate-limit",
    response_model=dict,
    summary="Get rate limiter statistics",
    description="Get statistics about rate limiting (for monitoring)",
)
async def get_rate_limit_stats():
    """Get rate limiter statistics."""
    try:
        stats = rate_limiter.get_stats()
        return {"success": True, "stats": stats}
    except Exception as e:
        logger.error(f"Error getting rate limit stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve rate limit statistics")
