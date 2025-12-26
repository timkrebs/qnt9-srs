"""
Legacy API router for backwards compatibility.

Provides old endpoints (/api/stocks/*) that redirect to new v2 endpoints.
This ensures existing clients continue to work while migrating to v2.
"""

import logging
import time

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..dependencies import get_stock_service
from ..domain.entities import IdentifierType, StockIdentifier
from ..domain.exceptions import StockNotFoundException, ValidationException
from ..services.stock_service import StockSearchService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/stocks", tags=["legacy"])


@router.get(
    "/search",
    summary="[LEGACY] Search stock by identifier",
    description="Legacy endpoint. Use /api/v1/search instead.",
    deprecated=True,
)
async def legacy_search_stock(
    query: str = Query(
        ...,
        min_length=1,
        max_length=100,
        description="ISIN, WKN, Symbol, or company name",
    ),
    service: StockSearchService = Depends(get_stock_service),
):
    """
    Legacy search endpoint for backwards compatibility.

    Returns the old API format expected by frontend-service.
    This endpoint is deprecated. Please use /api/v1/search instead.
    """
    start_time = time.time()

    try:
        # Detect query type for response
        query_type = StockIdentifier.detect_type(query.upper())

        # Perform search
        stock = await service.search(query)

        # Calculate response time
        response_time_ms = int((time.time() - start_time) * 1000)

        # Build stock data in old format with complete company information
        stock_data = {
            # Identifiers
            "symbol": stock.identifier.symbol,
            "name": stock.identifier.name,
            "isin": stock.identifier.isin,
            "wkn": stock.identifier.wkn,
            # Price data
            "current_price": float(stock.price.current) if stock.price else None,
            "currency": stock.price.currency if stock.price else None,
            "change_percent": (
                float(stock.price.change_percent)
                if stock.price and stock.price.change_percent
                else None
            ),
            "change_absolute": (
                float(stock.price.change_absolute)
                if stock.price and stock.price.change_absolute
                else None
            ),
            "previous_close": (
                float(stock.price.previous_close)
                if stock.price and stock.price.previous_close
                else None
            ),
            "open_price": (
                float(stock.price.open_price) if stock.price and stock.price.open_price else None
            ),
            "day_high": (
                float(stock.price.day_high) if stock.price and stock.price.day_high else None
            ),
            "day_low": float(stock.price.day_low) if stock.price and stock.price.day_low else None,
            "week_52_high": (
                float(stock.price.week_52_high)
                if stock.price and stock.price.week_52_high
                else None
            ),
            "week_52_low": (
                float(stock.price.week_52_low) if stock.price and stock.price.week_52_low else None
            ),
            "volume": stock.price.volume if stock.price else None,
            "avg_volume": stock.price.avg_volume if stock.price else None,
            # Company metadata
            "exchange": stock.metadata.exchange if stock.metadata else None,
            "sector": stock.metadata.sector if stock.metadata else None,
            "industry": stock.metadata.industry if stock.metadata else None,
            "market_cap": (
                float(stock.metadata.market_cap)
                if stock.metadata and stock.metadata.market_cap
                else None
            ),
            "pe_ratio": (
                float(stock.metadata.pe_ratio)
                if stock.metadata and stock.metadata.pe_ratio
                else None
            ),
            "dividend_yield": (
                float(stock.metadata.dividend_yield)
                if stock.metadata and stock.metadata.dividend_yield
                else None
            ),
            "beta": float(stock.metadata.beta) if stock.metadata and stock.metadata.beta else None,
            # Company information
            "description": stock.metadata.description if stock.metadata else None,
            "employees": stock.metadata.employees if stock.metadata else None,
            "founded": stock.metadata.founded if stock.metadata else None,
            "headquarters": stock.metadata.headquarters if stock.metadata else None,
            "website": stock.metadata.website if stock.metadata else None,
            # Cache info
            "cached": stock.cache_age_seconds is not None and stock.cache_age_seconds > 0,
            "cache_age_seconds": stock.cache_age_seconds or 0,
        }

        # Return in old format matching StockSearchResponse
        return {
            "success": True,
            "data": stock_data,
            "message": "Stock found successfully",
            "query_type": query_type.value,
            "response_time_ms": response_time_ms,
        }

    except StockNotFoundException as e:
        response_time_ms = int((time.time() - start_time) * 1000)

        # Try to detect query type even on failure
        try:
            query_type = StockIdentifier.detect_type(query.upper())
        except Exception:
            query_type = IdentifierType.NAME

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "success": False,
                "error": "stock_not_found",
                "message": e.message,
                "query": query,
                "query_type": query_type.value,
                "response_time_ms": response_time_ms,
            },
        )

    except ValidationException as e:
        response_time_ms = int((time.time() - start_time) * 1000)

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "success": False,
                "error": "validation_error",
                "message": e.message,
                "details": e.details,
                "response_time_ms": response_time_ms,
            },
        )

    except Exception as e:
        response_time_ms = int((time.time() - start_time) * 1000)
        logger.error(f"Unexpected error in legacy search: {e}", exc_info=True)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "error": "internal_error",
                "message": "An unexpected error occurred",
                "response_time_ms": response_time_ms,
            },
        )


@router.get(
    "/suggestions",
    summary="[LEGACY] Get search suggestions",
    description="Legacy endpoint. Use /api/v1/search/name instead.",
    deprecated=True,
)
async def legacy_get_suggestions(
    query: str = Query(..., min_length=1, description="Partial search query"),
    limit: int = Query(5, ge=1, le=20, description="Maximum number of suggestions"),
    service: StockSearchService = Depends(get_stock_service),
):
    """
    Legacy suggestions endpoint for backwards compatibility.

    This endpoint is deprecated. Please use /api/v1/search/name instead.
    """
    try:
        stocks = await service.search_by_name(query, limit)

        # Return in old format
        return [
            {
                "symbol": stock.identifier.symbol,
                "name": stock.identifier.name,
                "isin": stock.identifier.isin,
                "wkn": stock.identifier.wkn,
                "exchange": stock.metadata.exchange if stock.metadata else None,
            }
            for stock in stocks
        ]

    except ValidationException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "validation_error", "message": e.message},
        )

    except Exception as e:
        logger.error(f"Unexpected error in legacy suggestions: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "internal_error",
                "message": "An unexpected error occurred",
            },
        )


@router.post(
    "/search/name",
    summary="[LEGACY] Search by company name",
    description="Legacy endpoint. Use /api/v1/search/name instead.",
    deprecated=True,
)
async def legacy_search_by_name(
    query: str = Query(..., min_length=3, description="Company name"),
    limit: int = Query(10, ge=1, le=50, description="Maximum results"),
    service: StockSearchService = Depends(get_stock_service),
):
    """
    Legacy name search endpoint for backwards compatibility.

    This endpoint is deprecated. Please use POST /api/v1/search/name instead.
    """
    try:
        stocks = await service.search_by_name(query, limit)

        # Return in old format
        return {
            "count": len(stocks),
            "results": [
                {
                    "symbol": stock.identifier.symbol,
                    "name": stock.identifier.name,
                    "isin": stock.identifier.isin,
                    "wkn": stock.identifier.wkn,
                    "current_price": stock.price.current if stock.price else None,
                    "currency": stock.price.currency if stock.price else None,
                    "exchange": stock.metadata.exchange if stock.metadata else None,
                }
                for stock in stocks
            ],
        }

    except ValidationException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "validation_error", "message": e.message},
        )

    except Exception as e:
        logger.error(f"Unexpected error in legacy name search: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "internal_error",
                "message": "An unexpected error occurred",
            },
        )
