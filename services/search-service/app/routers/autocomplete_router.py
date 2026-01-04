"""
Autocomplete router for fast symbol search.

Provides sub-100ms autocomplete using Meilisearch with
typo tolerance and relevance ranking.
"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from ..core.auth import UserContext, get_current_user_optional
from ..core.meilisearch_client import get_meilisearch_manager
from ..core.metrics_enhanced import SearchTimer, get_metrics_tracker
from ..services.meilisearch_sync_service import get_sync_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/autocomplete", tags=["Autocomplete"])


class AutocompleteResult(BaseModel):
    """Single autocomplete result."""

    symbol: str = Field(description="Stock symbol")
    name: str = Field(description="Company name")
    isin: str | None = Field(None, description="ISIN code if available")
    wkn: str | None = Field(None, description="WKN code if available")
    exchange: str | None = Field(None, description="Stock exchange")
    currency: str | None = Field(None, description="Currency")
    priority: int = Field(0, description="Priority score for ranking")


class AutocompleteResponse(BaseModel):
    """Autocomplete API response."""

    query: str = Field(description="Search query")
    results: list[AutocompleteResult] = Field(description="Matching stocks")
    total: int = Field(description="Total results found")
    latency_ms: float = Field(description="Search latency in milliseconds")


class SyncStatus(BaseModel):
    """Meilisearch sync status."""

    meilisearch_status: str = Field(description="Meilisearch health status")
    meilisearch_version: str | None = Field(None, description="Meilisearch version")
    index_documents: int = Field(description="Number of documents in index")
    is_indexing: bool = Field(description="Whether index is currently updating")


@router.get(
    "",
    response_model=AutocompleteResponse,
    summary="Fast autocomplete search",
    description="Sub-100ms autocomplete with typo tolerance",
)
async def autocomplete_search(
    q: str = Query(
        ...,
        min_length=1,
        max_length=100,
        description="Search query (min 1 character)",
    ),
    limit: int = Query(
        10,
        ge=1,
        le=50,
        description="Maximum results (1-50)",
    ),
    exchange: str | None = Query(
        None,
        description="Filter by exchange (e.g., NASDAQ, NYSE)",
    ),
    user: UserContext = get_current_user_optional,
) -> AutocompleteResponse:
    """
    Fast autocomplete search for stocks.

    Features:
    - Sub-100ms response time
    - Typo tolerance
    - Relevance ranking
    - Filter by exchange

    Args:
        q: Search query
        limit: Maximum results
        exchange: Optional exchange filter
        user: Current user context

    Returns:
        Autocomplete results with latency info
    """
    tier = user.get("tier", "anonymous") if user else "anonymous"

    with SearchTimer("autocomplete", "symbol", tier) as timer:
        try:
            meilisearch = get_meilisearch_manager()

            filter_expr = None
            if exchange:
                filter_expr = f"exchange = {exchange}"

            import time

            start = time.time()

            hits = await meilisearch.search_autocomplete(
                query=q,
                limit=limit,
                filters=filter_expr,
            )

            latency_ms = (time.time() - start) * 1000

            results = [
                AutocompleteResult(
                    symbol=hit.get("symbol", ""),
                    name=hit.get("name", ""),
                    isin=hit.get("isin"),
                    wkn=hit.get("wkn"),
                    exchange=hit.get("exchange"),
                    currency=hit.get("currency"),
                    priority=hit.get("priority", 0),
                )
                for hit in hits
            ]

            timer.result_count = len(results)
            timer.cache_layer = "meilisearch"

            tracker = get_metrics_tracker()
            tracker.track_external_api_call(
                "meilisearch",
                latency_ms / 1000,
                success=True,
            )

            logger.info(
                "Autocomplete query '%s' returned %d results in %.2fms",
                q,
                len(results),
                latency_ms,
            )

            return AutocompleteResponse(
                query=q,
                results=results,
                total=len(results),
                latency_ms=latency_ms,
            )

        except Exception as e:
            logger.error("Autocomplete search failed: %s", e)
            timer.result_status = "error"

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Autocomplete search failed: {str(e)}",
            )


@router.post(
    "/sync",
    response_model=dict[str, Any],
    summary="Trigger index synchronization",
    description="Sync PostgreSQL symbols to Meilisearch index",
)
async def trigger_sync(
    full: bool = Query(
        False,
        description="Full sync (true) or incremental (false)",
    ),
    user: UserContext = get_current_user_optional,
) -> dict[str, Any]:
    """
    Trigger Meilisearch index synchronization.

    Args:
        full: Whether to perform full sync
        user: Current user context

    Returns:
        Sync result statistics
    """
    tier = user.get("tier", "anonymous") if user else "anonymous"

    if tier not in ["paid", "enterprise"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Index sync requires paid or enterprise tier",
        )

    try:
        sync_service = get_sync_service()

        if full:
            logger.info("Starting full index sync")
            result = await sync_service.full_sync()
        else:
            logger.info("Starting incremental index sync")
            from datetime import datetime, timedelta, timezone

            since = datetime.now(timezone.utc) - timedelta(hours=1)
            result = await sync_service.incremental_sync(since)

        return result

    except Exception as e:
        logger.error("Index sync failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Index sync failed: {str(e)}",
        )


@router.get(
    "/status",
    response_model=SyncStatus,
    summary="Get sync status",
    description="Check Meilisearch index status",
)
async def get_status() -> SyncStatus:
    """
    Get Meilisearch index status.

    Returns:
        Index status and statistics
    """
    try:
        sync_service = get_sync_service()
        status_info = await sync_service.get_sync_status()

        return SyncStatus(**status_info)

    except Exception as e:
        logger.error("Failed to get sync status: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get status: {str(e)}",
        )
