"""
Search Service - Main FastAPI Application
Provides stock search functionality using ISIN, WKN, or symbol codes
"""

import logging
import time
from contextlib import asynccontextmanager

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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
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
    title="QNT9 Stock Search Service",
    description="Stock search microservice supporting ISIN, WKN, and symbol lookups",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize API client (singleton)
stock_api_client = StockAPIClient()


@app.get("/", tags=["Health"])
async def root():
    """Root endpoint - service health check"""
    return {
        "service": "QNT9 Stock Search Service",
        "status": "operational",
        "version": "1.0.0",
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Detailed health check endpoint"""
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
        example="US0378331005",
    ),
    db: Session = Depends(get_db),
) -> StockSearchResponse:
    """
    Search for stock information by ISIN, WKN, or symbol

    **Query Types:**
    - **ISIN**: 12-character alphanumeric (e.g., US0378331005 for Apple)
    - **WKN**: 6-character alphanumeric (e.g., 865985 for Apple)
    - **Symbol**: Standard ticker symbol (e.g., AAPL)

    **Features:**
    - Automatic query type detection
    - Input validation with regex
    - 5-minute caching to reduce API calls
    - Response time <2 seconds
    - Suggestions for similar stocks if not found

    **Data Sources:**
    - Primary: Yahoo Finance API
    - Fallback: Alpha Vantage API
    """
    start_time = time.time()

    try:
        # Validate query format using Pydantic model
        try:
            validated_query = SearchQuery(query=query)
            query = validated_query.query  # Get normalized query
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "validation_error",
                    "message": str(e),
                    "query": query,
                },
            )

        # Detect query type
        query_type = detect_query_type(query)
        logger.info(f"Search request: {query} (type: {query_type})")

        # Validate format
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

        # Initialize cache manager
        cache_manager = CacheManager(db)

        # Try to get from cache first
        cached_data = cache_manager.get_cached_stock(query)
        if cached_data:
            response_time_ms = int((time.time() - start_time) * 1000)

            # Record successful search
            cache_manager.record_search(query, found=True)

            return StockSearchResponse(
                success=True,
                data=StockData(**cached_data),
                message="Data retrieved from cache",
                query_type=query_type,
                response_time_ms=response_time_ms,
            )

        # Not in cache - fetch from external API
        logger.info(f"Cache miss - fetching from external API for {query}")

        stock_data = stock_api_client.search_stock(query, query_type)

        if not stock_data:
            # Stock not found
            cache_manager.record_search(query, found=False)

            # Get suggestions
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

        # Save to cache
        cache_manager.save_to_cache(stock_data, query)
        cache_manager.record_search(query, found=True)

        # Add cache metadata
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
):
    """
    Get autocomplete suggestions based on search history

    Returns popular search queries matching the input prefix
    """
    try:
        cache_manager = CacheManager(db)
        suggestions = cache_manager.get_suggestions(query.strip().upper(), limit=limit)

        return {"query": query, "suggestions": suggestions, "count": len(suggestions)}

    except Exception as e:
        logger.error(f"Error getting suggestions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve suggestions",
        )


@app.get("/api/cache/stats", tags=["Cache Management"])
async def get_cache_stats(db: Session = Depends(get_db)):
    """
    Get cache statistics (for monitoring/debugging)
    """
    try:
        cache_manager = CacheManager(db)
        stats = cache_manager.get_cache_stats()

        return {
            "cache_statistics": stats,
            "ttl_minutes": 5,
            "timestamp": time.time(),
        }

    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve cache statistics",
        )


@app.post("/api/cache/cleanup", tags=["Cache Management"])
async def cleanup_cache(db: Session = Depends(get_db)):
    """
    Manually trigger cache cleanup (remove expired entries)
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
    """Global exception handler for unhandled errors"""
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
