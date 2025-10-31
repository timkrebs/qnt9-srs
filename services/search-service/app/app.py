"""
Search Service - Main FastAPI Application.

Provides stock search functionality using ISIN, WKN, or symbol codes
with caching, rate limiting, and multiple API source fallback.
"""

import logging
import time
from contextlib import asynccontextmanager
from typing import Any, Dict

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from .api_clients import StockAPIClient
from .cache import CacheManager
from .database import get_db, init_db
from .validators import (
    ErrorResponse,
    SearchQuery,
    StockData,
    StockSearchResponse,
    detect_query_type,
    is_valid_isin,
    is_valid_wkn,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Application metadata constants
APP_TITLE = "QNT9 Stock Search Service"
APP_DESCRIPTION = "Stock search microservice supporting ISIN, WKN, and symbol lookups"
APP_VERSION = "1.0.0"

# API response time requirement
MAX_RESPONSE_TIME_MS = 2000

# Cache TTL
CACHE_TTL_MINUTES = 5


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler for startup and shutdown events.

    Startup:
        - Initializes database tables
        - Logs service start

    Shutdown:
        - Logs service shutdown

    Args:
        app: FastAPI application instance

    Yields:
        Control to application runtime

    Raises:
        Exception: If database initialization fails
    """
    # Startup
    logger.info("Starting Search Service...")
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down Search Service...")


# Initialize FastAPI app
app = FastAPI(
    title=APP_TITLE,
    description=APP_DESCRIPTION,
    version=APP_VERSION,
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize API client (singleton)
stock_api_client = StockAPIClient()


@app.get("/", tags=["Health"])
async def root() -> Dict[str, str]:
    """
    Root endpoint - service health check.

    Returns:
        Dictionary with service information
    """
    return {
        "service": APP_TITLE,
        "status": "operational",
        "version": APP_VERSION,
    }


@app.get("/health", tags=["Health"])
async def health_check() -> Dict[str, Any]:
    """
    Detailed health check endpoint.

    Returns:
        Dictionary with health status and timestamp
    """
    return {
        "status": "healthy",
        "service": "search-service",
        "timestamp": time.time(),
    }


@app.get(
    "/api/stocks/search",
    response_model=StockSearchResponse,
    responses={
        200: {"description": "Stock found successfully"},
        400: {"model": ErrorResponse, "description": "Invalid input"},
        404: {"model": ErrorResponse, "description": "Stock not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    tags=["Stock Search"],
)
async def search_stock(
    query: str = Query(
        ...,
        min_length=1,
        max_length=20,
        description="ISIN, WKN, or stock symbol to search",
        examples=["US0378331005"],
    ),
    db: Session = Depends(get_db),
) -> StockSearchResponse:
    """
    Search for stock information by ISIN, WKN, or symbol.

    This endpoint provides comprehensive stock data with automatic query type
    detection, validation, and caching.

    Query Types:
        - ISIN: 12-character alphanumeric (e.g., US0378331005 for Apple)
        - WKN: 6-character alphanumeric (e.g., 865985 for Apple)
        - Symbol: Standard ticker symbol (e.g., AAPL)

    Features:
        - Automatic query type detection
        - Input validation with regex and checksum verification
        - 5-minute caching to reduce API calls
        - Response time <2 seconds
        - Suggestions for similar stocks if not found

    Data Sources:
        - Primary: Yahoo Finance API
        - Fallback: Alpha Vantage API

    Args:
        query: Search query (ISIN, WKN, or symbol)
        db: Database session dependency

    Returns:
        StockSearchResponse with stock data or error message

    Raises:
        HTTPException: For validation errors or internal errors
    """
    start_time = time.time()

    try:
        # Validate query format using Pydantic model
        validated_query = _validate_search_query(query)
        query = validated_query.query

        # Detect and validate query type
        query_type = detect_query_type(query)
        logger.info(f"Search request: {query} (type: {query_type})")

        _validate_query_format(query, query_type)

        # Initialize cache manager
        cache_manager = CacheManager(db)

        # Try cache first
        cached_data = cache_manager.get_cached_stock(query)
        if cached_data:
            return _build_cached_response(
                cached_data, query_type, start_time, cache_manager, query
            )

        # Cache miss - fetch from external API
        logger.info(f"Cache miss - fetching from external API for {query}")
        stock_data = stock_api_client.search_stock(query, query_type)

        if not stock_data:
            return _build_not_found_response(
                query, query_type, start_time, cache_manager
            )

        # Save to cache and build response
        cache_manager.save_to_cache(stock_data, query)
        cache_manager.record_search(query, found=True)

        return _build_success_response(stock_data, query_type, start_time)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing search request: {e}", exc_info=True)
        response_time_ms = int((time.time() - start_time) * 1000)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "internal_error",
                "message": "An error occurred while processing your request. Please try again later.",
                "response_time_ms": response_time_ms,
            },
        )


def _validate_search_query(query: str) -> SearchQuery:
    """
    Validate search query using Pydantic model.

    Args:
        query: Raw query string

    Returns:
        Validated SearchQuery object

    Raises:
        HTTPException: If validation fails
    """
    try:
        return SearchQuery(query=query)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "validation_error",
                "message": str(e),
                "query": query,
            },
        )


def _validate_query_format(query: str, query_type: str) -> None:
    """
    Validate query format based on detected type.

    Args:
        query: Query string
        query_type: Detected query type

    Raises:
        HTTPException: If format validation fails
    """
    if query_type == "isin" and not is_valid_isin(query):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "validation_error",
                "message": "Invalid ISIN format. ISIN must be 12 characters with valid checksum.",
                "query": query,
            },
        )

    if query_type == "wkn" and not is_valid_wkn(query):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "validation_error",
                "message": "Invalid WKN format. WKN must be exactly 6 alphanumeric characters.",
                "query": query,
            },
        )


def _build_cached_response(
    cached_data: Dict[str, Any],
    query_type: str,
    start_time: float,
    cache_manager: CacheManager,
    query: str,
) -> StockSearchResponse:
    """
    Build response from cached data.

    Args:
        cached_data: Cached stock data
        query_type: Type of query
        start_time: Request start time
        cache_manager: Cache manager instance
        query: Original query

    Returns:
        StockSearchResponse with cached data
    """
    response_time_ms = int((time.time() - start_time) * 1000)
    cache_manager.record_search(query, found=True)

    return StockSearchResponse(
        success=True,
        data=StockData(**cached_data),
        message="Data retrieved from cache",
        query_type=query_type,
        response_time_ms=response_time_ms,
    )


def _build_not_found_response(
    query: str,
    query_type: str,
    start_time: float,
    cache_manager: CacheManager,
) -> StockSearchResponse:
    """
    Build response for stock not found scenario.

    Args:
        query: Search query
        query_type: Type of query
        start_time: Request start time
        cache_manager: Cache manager instance

    Returns:
        StockSearchResponse with not found message and suggestions
    """
    cache_manager.record_search(query, found=False)
    suggestions = cache_manager.get_suggestions(query[:3] if len(query) > 3 else query)
    response_time_ms = int((time.time() - start_time) * 1000)

    return StockSearchResponse(
        success=False,
        data=None,
        message=f"Stock not found for {query_type.upper()} '{query}'. "
        f"Please verify the code and try again.",
        suggestions=suggestions if suggestions else None,
        query_type=query_type,
        response_time_ms=response_time_ms,
    )


def _build_success_response(
    stock_data: Dict[str, Any],
    query_type: str,
    start_time: float,
) -> StockSearchResponse:
    """
    Build successful response with fresh data.

    Args:
        stock_data: Stock data from API
        query_type: Type of query
        start_time: Request start time

    Returns:
        StockSearchResponse with fresh stock data
    """
    stock_data["cached"] = False
    stock_data["cache_age_seconds"] = 0
    response_time_ms = int((time.time() - start_time) * 1000)

    logger.info(
        f"Stock found: {stock_data.get('symbol')} - {stock_data.get('name')} "
        f"(response time: {response_time_ms}ms)"
    )

    return StockSearchResponse(
        success=True,
        data=StockData(**stock_data),
        message="Data retrieved from external API",
        query_type=query_type,
        response_time_ms=response_time_ms,
    )


@app.get("/api/stocks/suggestions", tags=["Stock Search"])
async def get_suggestions(
    query: str = Query(
        ...,
        min_length=1,
        max_length=20,
        description="Partial query for autocomplete suggestions",
    ),
    limit: int = Query(5, ge=1, le=20, description="Maximum number of suggestions"),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Get autocomplete suggestions based on search history.

    Returns popular search queries matching the input prefix,
    sorted by search frequency.

    Args:
        query: Partial query string for suggestions
        limit: Maximum number of suggestions to return
        db: Database session dependency

    Returns:
        Dictionary with query, suggestions list, and count

    Raises:
        HTTPException: If suggestion retrieval fails
    """
    try:
        cache_manager = CacheManager(db)
        suggestions = cache_manager.get_suggestions(query.strip().upper(), limit=limit)

        return {
            "query": query,
            "suggestions": suggestions,
            "count": len(suggestions),
        }

    except Exception as e:
        logger.error(f"Error getting suggestions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve suggestions",
        )


@app.get("/api/cache/stats", tags=["Cache Management"])
async def get_cache_stats(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Get cache statistics for monitoring and debugging.

    Provides metrics on cache performance and storage usage.

    Args:
        db: Database session dependency

    Returns:
        Dictionary with cache statistics and TTL configuration

    Raises:
        HTTPException: If stats retrieval fails
    """
    try:
        cache_manager = CacheManager(db)
        stats = cache_manager.get_cache_stats()

        return {
            "cache_statistics": stats,
            "ttl_minutes": CACHE_TTL_MINUTES,
            "timestamp": time.time(),
        }

    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve cache statistics",
        )


@app.post("/api/cache/cleanup", tags=["Cache Management"])
async def cleanup_cache(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Manually trigger cache cleanup to remove expired entries.

    This endpoint is useful for maintenance and testing purposes.
    In production, cleanup should also run on a scheduled basis.

    Args:
        db: Database session dependency

    Returns:
        Dictionary with cleanup results

    Raises:
        HTTPException: If cleanup fails
    """
    try:
        cache_manager = CacheManager(db)
        deleted = cache_manager.cleanup_expired()

        return {
            "success": True,
            "deleted_entries": deleted,
            "message": f"Removed {deleted} expired cache entries",
        }

    except Exception as e:
        logger.error(f"Error cleaning up cache: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cleanup cache",
        )


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """
    Global exception handler for unhandled errors.

    Catches any unhandled exceptions and returns a standardized error response.

    Args:
        request: FastAPI request object
        exc: Exception that was raised

    Returns:
        JSONResponse with error details
    """
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "internal_server_error",
            "message": "An unexpected error occurred. Please try again later.",
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
