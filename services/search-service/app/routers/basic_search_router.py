"""
Basic search router conforming to technical specification.

Provides a simplified search endpoint matching the spec exactly:
GET /api/v1/search?q={query}&limit={n}
"""

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..dependencies import get_stock_service
from ..search.relevance_scorer import SearchMatch
from ..services.stock_service import StockSearchService
from .spec_models import ErrorResponse, SearchResponse, SearchResultItem

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["search-spec"])


@router.get(
    "/search",
    response_model=SearchResponse,
    responses={
        200: {
            "description": "Search results",
            "content": {
                "application/json": {
                    "example": {
                        "results": [
                            {
                                "symbol": "AAPL",
                                "name": "Apple Inc.",
                                "exchange": "NASDAQ",
                                "type": "stock",
                                "match_score": 1.0,
                            }
                        ],
                        "query": "aapl",
                        "total_matches": 1,
                    }
                }
            },
        },
        400: {"description": "Invalid request", "model": ErrorResponse},
        404: {"description": "No results found", "model": ErrorResponse},
    },
    summary="Search stocks by symbol or name",
    description="""
    Search for stocks by symbol, company name, or partial matches.
    
    **Request Parameters:**
    - `q`: Search query (min 1 character, max 50)
    - `limit`: Maximum results (default: 10, range: 1-50)
    
    **Response Format:**
    Returns ranked list of matching stocks with relevance scores.
    
    **Search Capabilities:**
    - Exact symbol match (score: 1.0)
    - Symbol prefix match (score: 0.8)
    - Symbol contains query (score: 0.6)
    - Company name starts with query (score: 0.5)
    - Company name contains query (score: 0.3)
    
    **Performance:**
    - Typical response time: <100ms for cached results
    - Case-insensitive matching
    """,
)
async def search_stocks_spec(
    q: str = Query(
        ...,
        min_length=1,
        max_length=50,
        description="Search query (symbol or company name)",
        examples=["AAPL", "Apple", "MSFT", "Microsoft"],
    ),
    limit: int = Query(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of results to return",
    ),
    service: StockSearchService = Depends(get_stock_service),
) -> SearchResponse:
    """
    Search stocks by symbol or company name.

    Implements the technical specification search endpoint with
    standardized ranking and response format.

    Args:
        q: Search query string
        limit: Maximum number of results
        service: Stock search service dependency

    Returns:
        SearchResponse with results, query, and total_matches

    Raises:
        HTTPException: 400 for invalid query, 404 if no results found
    """
    try:
        query_normalized = q.strip().upper()

        if not query_normalized:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "invalid_query",
                    "message": "Search query cannot be empty",
                    "details": {},
                },
            )

        results = await service.intelligent_search(query_normalized, limit=limit)

        if not results:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "not_found",
                    "message": f"No results found for query: {q}",
                    "details": {"query": q},
                },
            )

        search_items = _convert_to_spec_format(results)

        return SearchResponse(
            results=search_items, query=q, total_matches=len(search_items)
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error("Unexpected error in search: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "internal_error",
                "message": "An unexpected error occurred during search",
                "details": {},
            },
        )


def _convert_to_spec_format(matches: List[SearchMatch]) -> List[SearchResultItem]:
    """
    Convert SearchMatch objects to spec-compliant SearchResultItem format.

    Args:
        matches: List of SearchMatch objects from intelligent_search

    Returns:
        List of SearchResultItem objects with proper match_score
    """
    items = []

    for match in matches:
        stock = match.stock
        identifier = stock.identifier
        metadata = stock.metadata

        item = SearchResultItem(
            symbol=identifier.symbol,
            name=metadata.name,
            exchange=metadata.exchange or "UNKNOWN",
            type="stock",
            match_score=match.get_spec_match_score(),
        )

        items.append(item)

    return items
