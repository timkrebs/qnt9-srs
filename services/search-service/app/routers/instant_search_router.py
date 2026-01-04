"""
Instant search router for ultra-fast autocomplete.

Optimized endpoint for real-time search suggestions with aggressive caching
and minimal response payload for best performance.
"""

import time
from typing import List, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from ..core.auth import User, get_current_user
from ..core.rate_limiter import rate_limiter
from ..dependencies import get_stock_service
from ..domain.exceptions import ValidationException
from ..services.stock_service import StockSearchService

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/search", tags=["instant-search"])


class InstantSearchResult(BaseModel):
    """Instant search result item."""

    symbol: str = Field(..., description="Stock symbol")
    name: str = Field(..., description="Company name")
    exchange: Optional[str] = Field(None, description="Exchange code")
    price: Optional[float] = Field(None, description="Current price")
    change_percent: Optional[float] = Field(None, description="Price change percentage")
    relevance_score: float = Field(..., description="Relevance score (0-100)")
    match_type: str = Field(
        ..., description="Match type: exact, prefix, fuzzy, contains"
    )


class InstantSearchResponse(BaseModel):
    """Instant search response."""

    success: bool = True
    query: str = Field(..., description="Original query")
    results: List[InstantSearchResult] = Field(default_factory=list)
    count: int = Field(..., description="Number of results")
    latency_ms: float = Field(..., description="Search latency in milliseconds")


@router.get(
    "/instant",
    response_model=InstantSearchResponse,
    responses={
        200: {"description": "Search successful"},
        400: {"description": "Invalid query"},
        429: {"description": "Rate limit exceeded"},
    },
    summary="Instant search for autocomplete",
    description="""
    Ultra-fast search endpoint optimized for autocomplete functionality.
    
    Features:
    - Fuzzy matching for typos
    - Intelligent relevance ranking
    - Aggressive caching (60s)
    - Minimal response payload
    - <100ms p95 latency target
    
    Best Practices:
    - Debounce client requests (250-300ms)
    - Start searching at 2+ characters
    - Cache results client-side
    - Use for autocomplete/typeahead only
    """,
)
async def instant_search(
    request: Request,
    q: str = Query(
        ...,
        min_length=1,
        max_length=50,
        description="Search query (1-50 characters)",
        examples=["AAPL", "app", "micro"],
    ),
    limit: int = Query(
        default=10,
        ge=1,
        le=20,
        description="Maximum results (1-20, default 10)",
    ),
    service: StockSearchService = Depends(get_stock_service),
    user: Optional[User] = Depends(get_current_user),
):
    """
    Perform instant search for autocomplete.

    Optimized for speed with intelligent ranking and fuzzy matching.
    """
    start_time = time.time()

    # Determine user tier and ID for rate limiting
    tier = user.tier if user else "anonymous"
    user_id = user.id if user else request.client.host

    # Apply tier-based rate limiting
    try:
        await rate_limiter.check_rate_limit(user_id, tier)
    except HTTPException:
        logger.warning("Rate limit exceeded", user_id=user_id, tier=tier, query=q)
        raise

    try:
        # Perform intelligent search
        matches = await service.intelligent_search(
            query=q,
            limit=limit,
            user_id=user.id if user else None,
            include_fuzzy=len(q) >= 2,  # Only fuzzy match for 2+ characters
        )

        # Convert to response format
        results = []
        for match in matches:
            stock = match.stock
            result = InstantSearchResult(
                symbol=stock.identifier.symbol or "",
                name=stock.identifier.name or "",
                exchange=stock.metadata.exchange,
                price=float(stock.price.current) if stock.price.current else None,
                change_percent=(
                    float(stock.price.change_percent)
                    if stock.price.change_percent
                    else None
                ),
                relevance_score=round(match.score, 2),
                match_type=match.match_type,
            )
            results.append(result)

        latency_ms = (time.time() - start_time) * 1000

        logger.info(
            "Instant search completed",
            query=q,
            results=len(results),
            latency_ms=round(latency_ms, 1),
            tier=tier,
        )

        response = InstantSearchResponse(
            query=q,
            results=results,
            count=len(results),
            latency_ms=round(latency_ms, 2),
        )

        # Add aggressive caching headers (60s)
        return JSONResponse(
            content=response.model_dump(),
            headers={
                "Cache-Control": "public, max-age=60",
                "X-Search-Latency-Ms": str(round(latency_ms, 2)),
                "X-Result-Count": str(len(results)),
            },
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

    except Exception as e:
        logger.error("Instant search error", error=str(e), query=q)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "error": "internal_error",
                "message": "An error occurred during search",
            },
        )


@router.get(
    "/suggestions",
    responses={
        200: {"description": "Suggestions retrieved"},
        400: {"description": "Invalid query"},
        429: {"description": "Rate limit exceeded"},
    },
    summary="Get search suggestions",
    description="""
    Get lightweight autocomplete suggestions for partial queries.
    
    Minimal response payload optimized for typeahead functionality.
    Returns only symbol, name, and relevance score.
    """,
)
async def get_suggestions(
    request: Request,
    q: str = Query(
        ...,
        min_length=1,
        max_length=50,
        description="Search query",
        examples=["app", "mic", "goo"],
    ),
    limit: int = Query(
        default=5,
        ge=1,
        le=10,
        description="Maximum suggestions (1-10, default 5)",
    ),
    service: StockSearchService = Depends(get_stock_service),
    user: Optional[User] = Depends(get_current_user),
):
    """
    Get autocomplete suggestions.

    Lightweight endpoint for typeahead with minimal metadata.
    """
    start_time = time.time()

    # Determine user tier and ID for rate limiting
    tier = user.tier if user else "anonymous"
    user_id = user.id if user else request.client.host

    # Apply tier-based rate limiting
    try:
        await rate_limiter.check_rate_limit(user_id, tier)
    except HTTPException:
        logger.warning("Rate limit exceeded", user_id=user_id, tier=tier, query=q)
        raise

    try:
        # Get suggestions
        suggestions = await service.get_search_suggestions(
            query=q, limit=limit, user_id=user.id if user else None
        )

        latency_ms = (time.time() - start_time) * 1000

        logger.info(
            "Suggestions completed",
            query=q,
            results=len(suggestions),
            latency_ms=round(latency_ms, 1),
        )

        # Return with caching headers
        return JSONResponse(
            content={
                "success": True,
                "query": q,
                "suggestions": suggestions,
                "count": len(suggestions),
                "latency_ms": round(latency_ms, 2),
            },
            headers={
                "Cache-Control": "public, max-age=60",
                "X-Search-Latency-Ms": str(round(latency_ms, 2)),
            },
        )

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
        logger.error("Suggestions error", error=str(e), query=q)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "error": "internal_error",
                "message": "An error occurred while getting suggestions",
            },
        )
