"""
Stock search API router.

Handles all stock search endpoints with proper validation and error handling.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from ..dependencies import get_stock_service
from ..domain.exceptions import (
    CircuitBreakerOpenException,
    RateLimitExceededException,
    StockNotFoundException,
    ValidationException,
)
from ..services.stock_service import StockSearchService

logger = logging.getLogger(__name__)

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


# Dependency injection is handled by shared dependencies module
# No need for placeholder - import from dependencies.py handles it


@router.get(
    "/search",
    response_model=StockResponse,
    responses={
        200: {"description": "Stock found successfully"},
        404: {"description": "Stock not found", "model": ErrorResponse},
        429: {"description": "Rate limit exceeded", "model": ErrorResponse},
        503: {"description": "External service unavailable", "model": ErrorResponse},
    },
    summary="Search stock by identifier",
    description="Search for stock using ISIN, WKN, Symbol, or company name",
)
async def search_stock(
    query: str = Query(
        ...,
        min_length=1,
        max_length=100,
        description="ISIN, WKN, Symbol, or company name",
        examples=["AAPL", "US0378331005", "865985", "Apple"],
    ),
    service: StockSearchService = Depends(get_stock_service),
):
    """
    Search for stock by any identifier.

    Supports:
    - ISIN (12 characters, e.g., US0378331005)
    - WKN (6 characters, e.g., 865985)
    - Symbol (e.g., AAPL, MSFT)
    - Company name (e.g., Apple, Microsoft)
    """
    try:
        stock = await service.search(query)

        # Determine cache source
        cache_source = "api"
        if stock.cache_age_seconds:
            cache_source = "redis" if stock.cache_age_seconds < 60 else "postgresql"

        return StockResponse(
            success=True,
            data=stock.to_dict(),
            message="Stock found successfully",
            cache_source=cache_source,
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
