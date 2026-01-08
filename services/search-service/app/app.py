"""
Search Service - Main FastAPI Application.

Provides stock search functionality using ISIN, WKN, or symbol codes
with caching, rate limiting, and multiple API source fallback.
"""

import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from .cache import CacheManager
from .database import get_db, init_db
from .infrastructure.yahoo_finance_client import \
    YahooFinanceClient as StockAPIClient
from .metrics import metrics_endpoint, track_request_metrics
from .metrics_middleware import PrometheusMiddleware
from .shutdown_handler import setup_graceful_shutdown
from .tracing import configure_opentelemetry, instrument_fastapi
from .validators import (MAX_NAME_SEARCH_RESULTS, ErrorResponse,
                         NameSearchQuery, NameSearchResponse, PriceChange,
                         PricePoint, SearchQuery, StockData, StockReportData,
                         StockReportResponse, StockSearchResponse, WeekRange52,
                         detect_query_type, is_valid_isin, is_valid_wkn)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Application metadata constants
APP_TITLE = "Finio Stock Search Service"
APP_DESCRIPTION = "Stock search microservice supporting ISIN, WKN, and symbol lookups"
APP_VERSION = "1.0.0"

# API response time requirement
MAX_RESPONSE_TIME_MS = 2000

# Cache TTL
CACHE_TTL_MINUTES = 5

# Configure OpenTelemetry tracing
configure_opentelemetry(
    service_name="search-service",
    service_version="1.0.0",
    enable_tracing=True,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler for startup and shutdown events.

    Startup:
        - Initializes database tables
        - Initializes Redis connection pool
        - Logs service start

    Shutdown:
        - Closes Redis connections
        - Logs service shutdown

    Args:
        app: FastAPI application instance

    Yields:
        Control to application runtime

    Raises:
        Exception: If database or Redis initialization fails
    """
    # Startup
    logger.info("Starting Search Service...")

    # Initialize database
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

    # Initialize Redis connection manager
    try:
        from .core.redis_manager import get_redis_manager

        redis_manager = get_redis_manager()
        await redis_manager.initialize()
        app.state.redis_manager = redis_manager
        logger.info("Redis connection pool initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Redis: {e}")
        raise

    # Initialize StockSearchService and register with container
    try:
        from .database import SessionLocal
        from .repositories.postgres_repository import (
            PostgresStockRepository,
            PostgresSearchHistoryRepository,
        )
        from .repositories.redis_repository import RedisStockRepository
        from .infrastructure.yahoo_finance_client import YahooFinanceClient
        from .services.stock_service import StockSearchService
        from .dependencies import get_service_container

        # Get database session
        db = SessionLocal()

        # Get Redis client
        redis_client = await redis_manager.get_client()

        # Create repositories
        postgres_repo = PostgresStockRepository(db)
        redis_repo = RedisStockRepository(redis_client)
        history_repo = PostgresSearchHistoryRepository(db)

        # Create API client
        api_client = YahooFinanceClient()

        # Create and register service
        stock_service = StockSearchService(
            redis_repo=redis_repo,
            postgres_repo=postgres_repo,
            api_client=api_client,
            history_repo=history_repo,
        )
        get_service_container().register_stock_service(stock_service)

        # Store db session for cleanup
        app.state.db_session = db

        logger.info("StockSearchService initialized and registered successfully")
    except Exception as e:
        logger.error(f"Failed to initialize StockSearchService: {e}")
        # Don't raise - allow service to start, but search_router will return 503

    # Setup graceful shutdown handlers
    async def cleanup_redis():
        """Clean up Redis connections."""
        if hasattr(app.state, "redis_manager"):
            await app.state.redis_manager.close()
            logger.info("Redis connections closed")

    shutdown_handler = setup_graceful_shutdown(
        service_name="search-service", cleanup_callbacks=[cleanup_redis]
    )
    app.state.shutdown_handler = shutdown_handler
    app.state.is_shutting_down = False

    logger.info("Graceful shutdown handlers configured")

    yield

    # Shutdown
    logger.info("Shutting down Search Service...")
    app.state.is_shutting_down = True

    # Cleanup Redis
    await cleanup_redis()


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

# Configure security middleware
from .core.security import configure_security_middleware

configure_security_middleware(app)

# Add Prometheus metrics middleware
app.add_middleware(PrometheusMiddleware, track_func=track_request_metrics)

# Instrument FastAPI with OpenTelemetry
instrument_fastapi(app, excluded_urls="/health,/metrics,/")


# Middleware to handle shutdown state
@app.middleware("http")
async def shutdown_middleware(request: Request, call_next):
    """
    Reject new requests during graceful shutdown.

    Returns 503 Service Unavailable if service is shutting down.
    """
    if (
        hasattr(request.app.state, "is_shutting_down")
        and request.app.state.is_shutting_down
    ):
        # Allow health checks during shutdown for monitoring
        if request.url.path in ["/health", "/metrics", "/"]:
            return await call_next(request)

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service is shutting down",
        )

    return await call_next(request)


# Initialize API client (singleton)
stock_api_client = StockAPIClient()


@app.get("/metrics", include_in_schema=False)
async def metrics():
    """Prometheus metrics endpoint."""
    return await metrics_endpoint()


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


@app.get("/search", tags=["Search"])
async def simple_search(
    q: str = Query(
        ..., min_length=1, max_length=50, description="Search query (symbol or name)"
    ),
    limit: int = Query(default=10, ge=1, le=50, description="Maximum results"),
) -> Dict[str, Any]:
    """
    Simple search endpoint for frontend compatibility.
    
    Searches for stocks by symbol or name and returns basic results.
    This is a simplified endpoint that returns mock data for testing.
    """
    query_upper = q.upper()
    
    # Mock stock database for testing
    mock_stocks = [
        {"symbol": "AAPL", "name": "Apple Inc.", "exchange": "NASDAQ"},
        {"symbol": "MSFT", "name": "Microsoft Corporation", "exchange": "NASDAQ"},
        {"symbol": "GOOGL", "name": "Alphabet Inc.", "exchange": "NASDAQ"},
        {"symbol": "AMZN", "name": "Amazon.com Inc.", "exchange": "NASDAQ"},
        {"symbol": "TSLA", "name": "Tesla Inc.", "exchange": "NASDAQ"},
        {"symbol": "META", "name": "Meta Platforms Inc.", "exchange": "NASDAQ"},
        {"symbol": "NVDA", "name": "NVIDIA Corporation", "exchange": "NASDAQ"},
        {"symbol": "JPM", "name": "JPMorgan Chase & Co.", "exchange": "NYSE"},
        {"symbol": "V", "name": "Visa Inc.", "exchange": "NYSE"},
        {"symbol": "WMT", "name": "Walmart Inc.", "exchange": "NYSE"},
    ]
    
    # Simple search: match symbol or name
    results = []
    for stock in mock_stocks:
        score = 0.0
        if query_upper == stock["symbol"]:
            score = 1.0  # Exact symbol match
        elif stock["symbol"].startswith(query_upper):
            score = 0.8  # Symbol prefix match
        elif query_upper in stock["symbol"]:
            score = 0.6  # Symbol contains
        elif query_upper in stock["name"].upper():
            score = 0.5  # Name contains
        
        if score > 0:
            results.append({
                "symbol": stock["symbol"],
                "name": stock["name"],
                "exchange": stock["exchange"],
                "type": "stock",
                "match_score": score
            })
    
    # Sort by score descending
    results.sort(key=lambda x: x["match_score"], reverse=True)
    
    # Limit results
    results = results[:limit]
    
    logger.info(f"Search query: {q}, found {len(results)} results")
    
    return {
        "results": results,
        "query": q,
        "total_matches": len(results)
    }


def _is_potential_company_name(query: str) -> bool:
    """
    Check if query looks like a company name rather than an identifier.

    A query is considered a potential company name if:
    - Length >= 3 characters
    - Contains at least one letter
    - Contains spaces, lowercase letters, or is longer than 5 chars
    - Is not a valid ISIN format (12 chars starting with 2 letters)

    Args:
        query: Search query string

    Returns:
        True if query looks like a company name, False otherwise

    Examples:
        >>> _is_potential_company_name("Amazon")  # True - 6 chars, mixed case
        >>> _is_potential_company_name("Apple Inc")  # True - has space
        >>> _is_potential_company_name("microsoft")  # True - lowercase
        >>> _is_potential_company_name("AAPL")  # False - short symbol
        >>> _is_potential_company_name("US0378331005")  # False - ISIN format
    """
    if len(query) < 3:
        return False

    # Must contain at least one letter
    if not any(c.isalpha() for c in query):
        return False

    # Strong indicators of company name:
    # 1. Contains spaces (e.g., "Apple Inc", "Deutsche Bank")
    if " " in query:
        return True

    # 2. Contains lowercase letters (e.g., "Amazon", "Microsoft")
    if any(c.islower() for c in query):
        return True

    # 3. Longer than typical symbols/WKNs (>5 chars) and all letters
    #    (e.g., "AMAZON", "MICROSOFT", "GOOGLE")
    if len(query) > 5 and query.isalpha():
        return True

    # If it matches ISIN format exactly (12 chars, starts with 2 letters), not a name
    if len(query) == 12 and query[:2].isalpha() and query[2:].isalnum():
        return False

    # Short all-uppercase strings without numbers are likely symbols, not names
    # (e.g., "AAPL", "MSFT", "TSLA")
    if query.isupper() and len(query) <= 5 and query.isalpha():
        return False

    # WKN format (exactly 6 alphanumeric, all uppercase, with at least one digit)
    # is not a company name
    if (
        len(query) == 6
        and query.isalnum()
        and query.isupper()
        and any(c.isdigit() for c in query)
    ):
        return False

    # Default to False for edge cases
    return False


async def _try_name_search_fallback(
    query: str, cache_manager: "CacheManager", db: Session
) -> Optional[Dict[str, Any]]:
    """
    Try to find stock by company name as fallback.

    Searches for the company name and returns the first (best) result
    if found. This allows the main search endpoint to work with company
    names transparently.

    Args:
        query: Company name query
        cache_manager: Cache manager instance
        db: Database session

    Returns:
        Stock data dict if found, None otherwise
    """
    try:
        # Normalize query for name search
        normalized_query = query.strip()

        # Search cache first
        results = cache_manager.search_by_name(normalized_query, limit=1)

        # Fallback to external API if no cache results
        if not results:
            results = _search_external_api_and_cache(normalized_query, 1, cache_manager)

        if results:
            # Return first result as stock data
            best_match = results[0]
            logger.info(
                f"Name search fallback found: {best_match.get('name')} ({best_match.get('symbol')})"
            )
            return best_match

        return None

    except Exception as e:
        logger.warning(f"Name search fallback failed for '{query}': {e}")
        return None


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
        max_length=100,
        description="ISIN, WKN, stock symbol, or company name to search",
        examples=["US0378331005", "AAPL", "Apple"],
    ),
    db: Session = Depends(get_db),
) -> StockSearchResponse:
    """
    Search for stock information by ISIN, WKN, symbol, or company name.

    This endpoint provides comprehensive stock data with automatic query type
    detection, validation, and caching. Supports both identifier-based search
    (ISIN, WKN, Symbol) and company name search with fallback.

    Query Types:
        - ISIN: 12-character alphanumeric (e.g., US0378331005 for Apple)
        - WKN: 6-character alphanumeric (e.g., 865985 for Apple)
        - Symbol: Standard ticker symbol (e.g., AAPL)
        - Company Name: Full or partial company name (e.g., "Apple", "Microsoft")

    Features:
        - Automatic query type detection
        - Intelligent fallback to name search if identifier search fails
        - Input validation with regex and checksum verification
        - 5-minute caching to reduce API calls
        - Response time <2 seconds
        - Suggestions for similar stocks if not found

    Search Flow:
        1. Try identifier-based search (ISIN/WKN/Symbol)
        2. If not found and query looks like a name (>2 chars, has letters),
           automatically fallback to company name search
        3. Return first result from name search if found

    Data Sources:
        - Primary: Yahoo Finance API
        - Fallback: Alpha Vantage API

    Args:
        query: Search query (ISIN, WKN, symbol, or company name)
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
        original_query = query
        query = validated_query.query

        # Initialize cache manager first
        cache_manager = CacheManager(db)

        # Detect and validate query type first
        query_type = detect_query_type(query)
        logger.info(f"Search request: {query} (type: {query_type})")

        # For symbol queries, check if it could be a company name
        # This enables search-as-you-type for company names
        if query_type == "symbol" and _is_potential_company_name(original_query):
            logger.info(
                f"Symbol query looks like company name, using universal search: {original_query}"
            )

            # Try comprehensive search with multiple results
            search_results = _search_external_api_and_cache(
                original_query, limit=5, cache_manager=cache_manager
            )

            if search_results:
                # Get the best match symbol
                best_result = search_results[0]
                symbol = best_result["symbol"]
                response_query_type = "name"  # For response only

                logger.info(
                    f"Name search found symbol: {symbol}, fetching complete data..."
                )

                # Fetch complete stock data for the symbol (not just search result)
                stock_data = stock_api_client.search_stock(symbol, query_type="symbol")

                if stock_data:
                    # Save to cache for future lookups
                    cache_manager.save_to_cache(stock_data, symbol)
                    cache_manager.record_search(original_query, found=True)

                    return _build_success_response(
                        stock_data, response_query_type, start_time
                    )
                else:
                    # Fallback to basic search result if full data fetch fails
                    logger.warning(
                        f"Could not fetch full data for {symbol}, using search result"
                    )
                    stock_data = {
                        "symbol": best_result["symbol"],
                        "name": best_result["name"],
                        "isin": best_result.get("isin"),
                        "wkn": best_result.get("wkn"),
                        "current_price": best_result.get("current_price"),
                        "currency": best_result.get("currency"),
                        "exchange": best_result.get("exchange", ""),
                        "source": "yahoo_search",
                        "cached": False,
                    }

                    cache_manager.save_to_cache(stock_data, stock_data["symbol"])
                    cache_manager.record_search(original_query, found=True)

                    return _build_success_response(stock_data, query_type, start_time)

        # Standard identifier-based search (ISIN, WKN, or known symbols)
        _validate_query_format(query, query_type)

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


@app.get(
    "/api/stocks/search/name",
    response_model=NameSearchResponse,
    responses={
        200: {"description": "Search completed successfully"},
        400: {"model": ErrorResponse, "description": "Invalid input"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    tags=["Stock Search"],
)
async def search_stock_by_name(
    query: str = Query(
        ...,
        min_length=3,
        max_length=100,
        description="Company name to search (minimum 3 characters)",
        examples=["Apple"],
    ),
    limit: int = Query(
        default=MAX_NAME_SEARCH_RESULTS,
        ge=1,
        le=50,
        description="Maximum number of results to return",
    ),
    db: Session = Depends(get_db),
) -> NameSearchResponse:
    """
    Search for stocks by company name using fuzzy matching.

    This endpoint provides company name search with partial matching,
    relevance ranking, and caching for popular searches.

    Features:
        - Fuzzy matching with partial name support
        - Relevance-based result ranking
        - Returns top 10 results by default
        - Minimum 3 character query length
        - Cache-based search for fast response times
        - Fallback to external API if no cached results
        - Target response time <1 second

    Search Algorithm:
        1. Check cache for matching company names
        2. If no cache results, search Yahoo Finance API
        3. Cache API results for future searches
        4. Rank results by relevance score
        5. Return top N results sorted by score

    Args:
        query: Company name search string (min 3 characters)
        limit: Maximum number of results (default: 10, max: 50)
        db: Database session dependency

    Returns:
        NameSearchResponse with list of matching stocks

    Raises:
        HTTPException: For validation errors or internal errors
    """
    start_time = time.time()

    try:
        # Validate and normalize query
        validated_query = NameSearchQuery(query=query)
        normalized_query = validated_query.query

        # Search cache first
        cache_manager = CacheManager(db)
        results = cache_manager.search_by_name(normalized_query, limit=limit)

        # Fallback to external API if no cache results
        if not results:
            results = _search_external_api_and_cache(
                normalized_query, limit, cache_manager
            )

        # Build and return response
        return _build_name_search_response(
            results, normalized_query, start_time, cache_manager
        )

    except ValueError as e:
        logger.warning(f"Validation error for name search '{query}': {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    except Exception as e:
        logger.error(f"Error in name search for '{query}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while searching for stocks",
        )


@app.get(
    "/api/stocks/{identifier}/report",
    response_model=StockReportResponse,
    responses={
        200: {"description": "Stock report retrieved successfully"},
        400: {"model": ErrorResponse, "description": "Invalid ISIN or symbol"},
        404: {"model": ErrorResponse, "description": "Stock not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    tags=["Stock Reports"],
)
async def get_stock_report(
    identifier: str,
    db: Session = Depends(get_db),
) -> StockReportResponse:
    """
    Get comprehensive stock report with historical data and key metrics.

    This endpoint provides a complete stock report including:
    - Basic stock information (name, ISIN, WKN, symbol)
    - Current price with currency
    - 1-day price change (absolute, percentage, direction)
    - 52-week high and low prices
    - Market capitalization
    - 7-day price history for charting
    - Exchange information
    - Last updated timestamp

    The endpoint accepts either ISIN or stock symbol as identifier.
    Data is cached for 5 minutes to reduce API calls and improve response time.

    Features:
        - Target response time: <2 seconds
        - Automatic caching with TTL
        - Fallback to cached data if fresh data unavailable
        - Warning message when serving cached data
        - Support for ISIN and symbol identifiers

    Args:
        identifier: Stock ISIN (12 chars) or symbol (e.g., AAPL)
        db: Database session dependency

    Returns:
        StockReportResponse with comprehensive stock data

    Raises:
        HTTPException: For validation errors, not found, or internal errors

    Example Response:
        {
            "success": true,
            "data": {
                "symbol": "AAPL",
                "name": "Apple Inc.",
                "isin": "US0378331005",
                "current_price": 175.50,
                "currency": "USD",
                "price_change_1d": {"absolute": 2.5, "percentage": 1.44, "direction": "up"},
                "week_52_range": {"high": 199.62, "low": 164.08},
                "price_history_7d": [...]
            },
            "response_time_ms": 156
        }
    """
    start_time = time.time()

    try:
        # Normalize identifier
        identifier = identifier.strip().upper()

        # Detect if it's ISIN or symbol
        query_type = detect_query_type(identifier)

        logger.info(f"Stock report request for {identifier} (type: {query_type})")

        # Initialize cache manager
        cache_manager = CacheManager(db)

        # If identifier is ISIN, we need to find the symbol first
        symbol: str = identifier
        if query_type == "isin":
            resolved_symbol = _get_symbol_from_isin(identifier, cache_manager)
            if not resolved_symbol:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={
                        "error": "stock_not_found",
                        "message": f"No stock found for ISIN {identifier}",
                    },
                )
            symbol = resolved_symbol

        # Try cache first
        cached_report = cache_manager.get_cached_report(symbol)
        if cached_report:
            return _build_cached_report_response(cached_report, start_time)

        # Cache miss - fetch from external API
        logger.info(f"Report cache miss - fetching from API for {symbol}")
        report_data = stock_api_client.get_stock_report_data(symbol)

        if not report_data:
            # Try to return stale cache data if available
            stale_data = _get_stale_cached_report(symbol, cache_manager)
            if stale_data:
                return _build_stale_cache_response(stale_data, start_time)

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "stock_not_found",
                    "message": f"No stock data found for {identifier}",
                },
            )

        # Validate that we have the minimum required data
        _validate_report_data(report_data)

        # Cache the report data
        cache_manager.cache_report_data(report_data)

        # Build and return response
        return _build_report_response(report_data, start_time)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error fetching stock report for {identifier}: {e}", exc_info=True
        )
        response_time_ms = int((time.time() - start_time) * 1000)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "internal_error",
                "message": "An error occurred while fetching stock report",
                "response_time_ms": response_time_ms,
            },
        )


def _get_symbol_from_isin(isin: str, cache_manager: CacheManager) -> Optional[str]:
    """
    Get stock symbol from ISIN using cache or API.

    Args:
        isin: ISIN code
        cache_manager: Cache manager instance

    Returns:
        Stock symbol or None if not found
    """
    # Try cache first
    cached_stock = cache_manager.get_cached_stock(isin)
    if cached_stock:
        return cached_stock.get("symbol")

    # Try API
    stock_data = stock_api_client.search_stock(isin, query_type="isin")
    if stock_data:
        # Cache for future use
        cache_manager.save_to_cache(stock_data, isin)
        return stock_data.get("symbol")

    return None


def _validate_report_data(report_data: Dict[str, Any]) -> None:
    """
    Validate that report data contains minimum required fields.

    Args:
        report_data: Report data dictionary

    Raises:
        ValueError: If required data is missing
    """
    basic_info = report_data.get("basic_info", {})

    required_fields = ["symbol", "name", "current_price", "currency", "exchange"]
    missing_fields = [field for field in required_fields if not basic_info.get(field)]

    if missing_fields:
        raise ValueError(f"Missing required report fields: {', '.join(missing_fields)}")


def _build_report_response(
    report_data: Dict[str, Any], start_time: float
) -> StockReportResponse:
    """
    Build stock report response from fetched data.

    Args:
        report_data: Complete report data from API
        start_time: Request start timestamp

    Returns:
        StockReportResponse with formatted data
    """
    basic_info = report_data["basic_info"]
    price_change = report_data.get("price_change_1d")
    week_52_range = report_data.get("week_52_range")
    price_history = report_data.get("price_history_7d", [])

    # Build price change object
    price_change_obj = None
    if price_change:
        price_change_obj = PriceChange(
            absolute=price_change["absolute"],
            percentage=price_change["percentage"],
            direction=price_change["direction"],
        )

    # Build 52-week range object
    week_52_range_obj = None
    if week_52_range:
        week_52_range_obj = WeekRange52(
            high=week_52_range["high"],
            low=week_52_range["low"],
            high_date=week_52_range.get("high_date"),
            low_date=week_52_range.get("low_date"),
        )

    # Build price history
    price_points = [
        PricePoint(
            timestamp=point["timestamp"],
            price=point["price"],
            volume=point.get("volume"),
        )
        for point in price_history
    ]

    # Create report data object
    report = StockReportData(
        symbol=basic_info["symbol"],
        name=basic_info["name"],
        isin=basic_info.get("isin"),
        wkn=basic_info.get("wkn"),
        current_price=basic_info["current_price"],
        currency=basic_info.get("currency", "USD"),
        exchange=basic_info.get("exchange", ""),
        price_change_1d=price_change_obj
        or PriceChange(absolute=0.0, percentage=0.0, direction="neutral"),
        week_52_range=week_52_range_obj or WeekRange52(high=0.0, low=0.0),
        market_cap=basic_info.get("market_cap"),
        sector=basic_info.get("sector"),
        industry=basic_info.get("industry"),
        price_history_7d=price_points,
        last_updated=datetime.now(timezone.utc).isoformat(),
        data_source=basic_info.get("source", "yahoo"),
        cached=False,
        cache_timestamp=None,
    )

    response_time_ms = int((time.time() - start_time) * 1000)

    return StockReportResponse(
        success=True,
        data=report,
        message=None,
        response_time_ms=response_time_ms,
    )


def _build_cached_report_response(
    cached_data: Dict[str, Any], start_time: float
) -> StockReportResponse:
    """
    Build stock report response from cached data.

    Args:
        cached_data: Cached report data
        start_time: Request start timestamp

    Returns:
        StockReportResponse with cached data
    """
    # Build price change object
    price_change_data = cached_data.get("price_change_1d")
    price_change_obj = None
    if price_change_data:
        price_change_obj = PriceChange(
            absolute=price_change_data["absolute"],
            percentage=price_change_data["percentage"],
            direction=price_change_data["direction"],
        )

    # Build 52-week range object
    week_52_data = cached_data.get("week_52_range")
    week_52_range_obj = None
    if week_52_data:
        week_52_range_obj = WeekRange52(
            high=week_52_data["high"],
            low=week_52_data["low"],
            high_date=week_52_data.get("high_date"),
            low_date=week_52_data.get("low_date"),
        )

    # Build price history
    price_history = cached_data.get("price_history_7d", [])
    price_points = [
        PricePoint(
            timestamp=point["timestamp"],
            price=point["price"],
            volume=point.get("volume"),
        )
        for point in price_history
    ]

    # Create report data object
    report = StockReportData(
        symbol=cached_data["symbol"],
        name=cached_data["name"],
        isin=cached_data.get("isin"),
        wkn=cached_data.get("wkn"),
        current_price=cached_data["current_price"],
        currency=cached_data["currency"],
        exchange=cached_data["exchange"],
        price_change_1d=price_change_obj
        or PriceChange(absolute=0.0, percentage=0.0, direction="neutral"),
        week_52_range=week_52_range_obj or WeekRange52(high=0.0, low=0.0),
        market_cap=cached_data.get("market_cap"),
        sector=cached_data.get("sector"),
        industry=cached_data.get("industry"),
        price_history_7d=price_points,
        last_updated=cached_data.get("cache_timestamp", ""),
        data_source=cached_data.get("data_source", "yahoo"),
        cached=True,
        cache_timestamp=cached_data.get("cache_timestamp"),
    )

    response_time_ms = int((time.time() - start_time) * 1000)

    return StockReportResponse(
        success=True,
        data=report,
        message=None,
        response_time_ms=response_time_ms,
    )


def _get_stale_cached_report(
    symbol: str, cache_manager: CacheManager
) -> Optional[Dict[str, Any]]:
    """
    Get stale (expired) cached report data as fallback.

    Args:
        symbol: Stock symbol
        cache_manager: Cache manager instance

    Returns:
        Stale cached data or None if not found
    """
    try:
        from .models import StockReportCache

        # Query without expiration filter to get stale data
        cache_entry = (
            cache_manager.db.query(StockReportCache)
            .filter(StockReportCache.symbol == symbol.upper())
            .order_by(StockReportCache.updated_at.desc())
            .first()
        )

        if cache_entry:
            logger.info(f"Using stale cache data for {symbol}")
            cache_age = int(
                (
                    datetime.now(timezone.utc).replace(tzinfo=None)
                    - cache_entry.created_at
                ).total_seconds()
            )
            return cache_manager._build_report_dict(cache_entry, cache_age)

        return None

    except Exception as e:
        logger.error(f"Error retrieving stale cache: {e}")
        return None


def _build_stale_cache_response(
    stale_data: Dict[str, Any], start_time: float
) -> StockReportResponse:
    """
    Build response using stale cached data with warning message.

    Args:
        stale_data: Stale cached report data
        start_time: Request start timestamp

    Returns:
        StockReportResponse with warning about cached data
    """
    response = _build_cached_report_response(stale_data, start_time)
    cache_timestamp = stale_data.get("cache_timestamp", "unknown")
    response.message = f"Showing cached data from {cache_timestamp}. Fresh data temporarily unavailable."

    return response


def _search_external_api_and_cache(
    query: str, limit: int, cache_manager: CacheManager
) -> list[Dict[str, Any]]:
    """
    Search external API and cache results.

    Args:
        query: Normalized company name query
        limit: Maximum number of results
        cache_manager: Cache manager instance

    Returns:
        List of stock search results with relevance scores
    """
    logger.info(f"No cache results for '{query}', searching API")

    api_results = stock_api_client.search_by_name(query, limit=limit)
    results = []

    for api_result in api_results:
        enriched_result = _enrich_and_cache_api_result(api_result, query, cache_manager)
        if enriched_result:
            results.append(enriched_result)

    # Sort by relevance and limit results
    results.sort(key=lambda x: x["relevance_score"], reverse=True)
    return results[:limit]


def _enrich_and_cache_api_result(
    api_result: Dict[str, Any], query: str, cache_manager: CacheManager
) -> Optional[Dict[str, Any]]:
    """
    Enrich API result with full stock data and cache it.

    Args:
        api_result: Basic search result from API
        query: Original search query for relevance calculation
        cache_manager: Cache manager instance

    Returns:
        Enriched result dictionary or None if enrichment fails
    """
    symbol = api_result.get("symbol")
    if not symbol:
        return None

    # Fetch full stock data
    full_data = stock_api_client.enrich_search_result(symbol)
    if not full_data:
        return None

    # Cache the enriched data
    cache_manager.save_to_cache(full_data, symbol)

    # Calculate relevance score
    company_name = api_result.get("name", "")
    relevance = cache_manager._calculate_relevance_score(query, company_name)

    return {
        "symbol": symbol,
        "name": company_name,
        "isin": full_data.get("isin"),
        "wkn": full_data.get("wkn"),
        "current_price": full_data.get("current_price"),
        "currency": full_data.get("currency"),
        "exchange": api_result.get("exchange"),
        "relevance_score": relevance,
    }


def _build_name_search_response(
    results: list[Dict[str, Any]],
    query: str,
    start_time: float,
    cache_manager: CacheManager,
) -> NameSearchResponse:
    """
    Build name search response with analytics.

    Args:
        results: List of search results
        query: Original search query
        start_time: Request start timestamp
        cache_manager: Cache manager instance

    Returns:
        Formatted NameSearchResponse
    """
    response_time = int((time.time() - start_time) * 1000)

    # Log search analytics
    logger.info(
        f"Name search for '{query}' returned {len(results)} results "
        f"in {response_time}ms"
    )

    # Record search in history
    cache_manager.record_search(query, found=len(results) > 0)

    return NameSearchResponse(
        success=True,
        results=results,
        total_results=len(results),
        message=None if results else "No stocks found matching your search",
        query=query,
        response_time_ms=response_time,
    )


@app.get(
    "/api/stocks/{symbol}/historical",
    responses={
        200: {"description": "Historical data retrieved successfully"},
        400: {"description": "Invalid symbol or parameters"},
        404: {"description": "Stock not found"},
        500: {"description": "Internal server error"},
    },
    tags=["Stock Data"],
)
async def get_historical_data(
    symbol: str,
    period: str = Query(
        default="1d",
        description="Time period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)",
        examples=["1d", "5d", "1mo", "3mo", "1y"],
    ),
    interval: str = Query(
        default="5m",
        description="Data interval (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)",
        examples=["5m", "15m", "1h", "1d"],
    ),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Get historical price data for a stock symbol.

    This endpoint provides historical OHLCV (Open, High, Low, Close, Volume) data
    for charting and technical analysis. Supports various time periods and intervals.

    Features:
        - Real-time data from Yahoo Finance
        - Multiple time periods (1 day to max history)
        - Various intervals (1 minute to 1 month)
        - OHLCV data format for professional charts
        - Caching for improved performance
        - Rate limiting to respect API limits

    Time Periods:
        - 1d, 5d: Intraday data
        - 1mo, 3mo, 6mo: Short-term history
        - 1y, 2y, 5y: Medium to long-term history
        - 10y, ytd, max: Extended history

    Intervals:
        - 1m, 2m, 5m, 15m, 30m: Intraday (limited to recent periods)
        - 1h, 90m: Hourly data
        - 1d: Daily data (default for longer periods)
        - 1wk, 1mo: Weekly/monthly aggregation

    Args:
        symbol: Stock ticker symbol (e.g., AAPL, MSFT, TSLA)
        period: Time period for historical data
        interval: Data granularity interval
        db: Database session dependency

    Returns:
        Dictionary with historical data points and metadata

    Raises:
        HTTPException: For validation errors, not found, or internal errors

    Example Response:
        {
            "success": true,
            "symbol": "AAPL",
            "period": "1d",
            "interval": "5m",
            "data": [
                {
                    "timestamp": "2024-01-01T09:30:00-05:00",
                    "open": 150.0,
                    "high": 152.0,
                    "low": 149.5,
                    "close": 151.5,
                    "volume": 1000000
                }
            ],
            "count": 78,
            "response_time_ms": 245
        }
    """
    start_time = time.time()

    try:
        # Validate and normalize symbol
        symbol = symbol.strip().upper()
        if not symbol or len(symbol) > 10:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "validation_error",
                    "message": "Invalid symbol format",
                    "symbol": symbol,
                },
            )

        # Validate period and interval combinations
        _validate_period_interval_combination(period, interval)

        logger.info(f"Historical data request: {symbol} ({period}, {interval})")

        # Initialize cache manager
        cache_manager = CacheManager(db)

        # Check cache for historical data (short TTL for real-time data)
        cache_key = f"hist_{symbol}_{period}_{interval}"
        cached_data = _get_cached_historical_data(cache_key, cache_manager)

        if cached_data:
            response_time_ms = int((time.time() - start_time) * 1000)
            return {
                "success": True,
                "symbol": symbol,
                "period": period,
                "interval": interval,
                "data": cached_data,
                "count": len(cached_data),
                "cached": True,
                "response_time_ms": response_time_ms,
            }

        # Fetch fresh data from Yahoo Finance
        historical_data = stock_api_client.get_historical_data_ohlcv(
            symbol, period=period, interval=interval
        )

        if not historical_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "data_not_found",
                    "message": f"No historical data found for symbol {symbol}",
                    "symbol": symbol,
                    "period": period,
                    "interval": interval,
                },
            )

        # Cache the data (short TTL for real-time data)
        _cache_historical_data(cache_key, historical_data, cache_manager)

        response_time_ms = int((time.time() - start_time) * 1000)

        logger.info(
            f"Historical data retrieved: {symbol} - {len(historical_data)} points "
            f"({period}, {interval}) in {response_time_ms}ms"
        )

        return {
            "success": True,
            "symbol": symbol,
            "period": period,
            "interval": interval,
            "data": historical_data,
            "count": len(historical_data),
            "cached": False,
            "response_time_ms": response_time_ms,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching historical data for {symbol}: {e}", exc_info=True)
        response_time_ms = int((time.time() - start_time) * 1000)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "internal_error",
                "message": "An error occurred while fetching historical data",
                "response_time_ms": response_time_ms,
            },
        )


def _validate_period_interval_combination(period: str, interval: str) -> None:
    """
    Validate that period and interval combination is supported by Yahoo Finance.

    Args:
        period: Time period string
        interval: Interval string

    Raises:
        HTTPException: If combination is invalid
    """
    valid_periods = {
        "1d",
        "5d",
        "1mo",
        "3mo",
        "6mo",
        "1y",
        "2y",
        "5y",
        "10y",
        "ytd",
        "max",
    }
    valid_intervals = {
        "1m",
        "2m",
        "5m",
        "15m",
        "30m",
        "60m",
        "90m",
        "1h",
        "1d",
        "5d",
        "1wk",
        "1mo",
        "3mo",
    }

    if period not in valid_periods:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "validation_error",
                "message": f"Invalid period '{period}'. Valid periods: {', '.join(sorted(valid_periods))}",
            },
        )

    if interval not in valid_intervals:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "validation_error",
                "message": f"Invalid interval '{interval}'. Valid intervals: {', '.join(sorted(valid_intervals))}",
            },
        )

    # Validate specific combinations (Yahoo Finance restrictions)
    intraday_intervals = {"1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h"}
    short_periods = {"1d", "5d"}

    if interval in intraday_intervals and period not in short_periods:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "validation_error",
                "message": f"Intraday intervals ({interval}) only supported for short periods (1d, 5d)",
            },
        )


def _get_cached_historical_data(
    cache_key: str, cache_manager: CacheManager
) -> Optional[list]:
    """
    Get cached historical data if available and not expired.

    Args:
        cache_key: Cache key for the data
        cache_manager: Cache manager instance

    Returns:
        Cached data list or None if not found/expired
    """
    try:
        # For historical data, use shorter cache TTL (2 minutes for real-time data)
        # This is implemented in the cache manager - for now return None to always fetch fresh
        return None
    except Exception as e:
        logger.warning(f"Error retrieving cached historical data: {e}")
        return None


def _cache_historical_data(
    cache_key: str, data: list, cache_manager: CacheManager
) -> None:
    """
    Cache historical data with appropriate TTL.

    Args:
        cache_key: Cache key for the data
        data: Historical data to cache
        cache_manager: Cache manager instance
    """
    try:
        # For now, we'll skip caching historical data to always get fresh data
        # In production, you might want to implement short-term caching
        pass
    except Exception as e:
        logger.warning(f"Error caching historical data: {e}")


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


# Register search routers using direct imports
# Note: Dynamic loading with importlib.util.spec_from_file_location breaks relative imports

# Load and register instant search router
try:
    from .routers.instant_search_router import router as instant_search_router
    app.include_router(instant_search_router)
    logger.info("Instant search router registered successfully")
except Exception as e:
    logger.error(f"Failed to register instant_search_router: {e}")

# Load and register autocomplete router  
try:
    from .routers.autocomplete_router import router as autocomplete_router
    app.include_router(autocomplete_router)
    logger.info("Autocomplete router registered successfully")
except Exception as e:
    logger.error(f"Failed to register autocomplete_router: {e}")


# Register additional routers - stock data endpoints
try:
    from .routers.stock_data_router import router as stock_data_router
    app.include_router(stock_data_router)
    logger.info("Stock data router registered successfully")
except Exception as e:
    logger.error(f"Failed to register stock data router: {e}")

# Register Massive API routers - ticker search, stock snapshots, charts, websocket
# Using direct imports since dynamic loading breaks relative imports

# Health router - CRITICAL for Traefik health checks
try:
    from .routers.health_router import router as health_router
    app.include_router(health_router)
    logger.info("health_router registered successfully")
except Exception as e:
    logger.error(f"Failed to register health_router: {e}")

try:
    from .routers.ticker_router import router as ticker_router
    app.include_router(ticker_router)
    logger.info("ticker_router registered successfully")
except Exception as e:
    logger.error(f"Failed to register ticker_router: {e}")

try:
    from .routers.stock_router import router as stock_router
    app.include_router(stock_router)
    logger.info("stock_router registered successfully")
except Exception as e:
    logger.error(f"Failed to register stock_router: {e}")

try:
    from .routers.chart_router import router as chart_router
    app.include_router(chart_router)
    logger.info("chart_router registered successfully")
except Exception as e:
    logger.error(f"Failed to register chart_router: {e}")

try:
    from .routers.ws_router import router as ws_router
    app.include_router(ws_router)
    logger.info("ws_router registered successfully")
except Exception as e:
    logger.error(f"Failed to register ws_router: {e}")

# Search router - contains /popular endpoint for data pipeline
try:
    from .routers.search_router import router as search_router
    app.include_router(search_router)
    logger.info("search_router registered successfully")
except Exception as e:
    logger.error(f"Failed to register search_router: {e}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
