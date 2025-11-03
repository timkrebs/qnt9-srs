"""
Frontend Service - Main FastAPI Application.

Provides a web UI for stock search functionality using HTMX for dynamic updates.
This service acts as the user-facing frontend for the QNT9 Stock Recommendation System.
"""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional

from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .api_client import search_client
from .config import settings
from .logging_config import get_logger, setup_logging

# Setup logging
setup_logging(log_level=settings.LOG_LEVEL, service_name="frontend-service")
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan context manager.

    Handles startup and shutdown events for the application.
    Replaces the deprecated @app.on_event decorators.
    """
    # Startup
    logger.info("Starting Frontend Service...")
    logger.info(f"Service URL: {settings.SEARCH_SERVICE_URL}")
    logger.info(f"Debug mode: {settings.DEBUG}")
    logger.info(f"Log level: {settings.LOG_LEVEL}")

    # Check search service health
    is_healthy = await search_client.health_check()
    if is_healthy:
        logger.info("Search service is healthy and ready")
    else:
        logger.warning(
            "Search service is not responding - some features may be unavailable"
        )

    yield

    # Shutdown
    logger.info("Shutting down Frontend Service...")


# Initialize FastAPI app
app = FastAPI(
    title="QNT9 Frontend Service",
    description="Web UI for QNT9 Stock Recommendation System",
    version="1.0.0",
    docs_url="/api/docs" if settings.DEBUG else None,
    redoc_url="/api/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)

# Setup templates and static files
BASE_PATH = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_PATH / "templates"))


# Add custom Jinja2 filters
def timestamp_to_date(timestamp: Optional[int]) -> str:
    """
    Convert Unix timestamp to readable date string.

    Args:
        timestamp: Unix timestamp (seconds since epoch), or None

    Returns:
        Formatted date string (e.g., "Nov 10, 2025"), or empty string if None
    """
    if not timestamp:
        return ""
    try:
        from datetime import datetime

        dt = datetime.fromtimestamp(timestamp)
        return dt.strftime("%b %d, %Y")
    except (ValueError, OSError):
        return ""


templates.env.filters["timestamp_to_date"] = timestamp_to_date

# Mount static files
try:
    app.mount(
        "/static",
        StaticFiles(directory=str(BASE_PATH / "static")),
        name="static",
    )
except RuntimeError:
    logger.warning("Static directory not found - will be created")


@app.get(
    "/",
    response_class=HTMLResponse,
    tags=["Pages"],
    summary="Homepage",
    description="Main landing page with stock search functionality",
)
async def homepage(request: Request) -> HTMLResponse:
    """
    Render the homepage with stock search interface.

    Provides the main user interface for searching stocks by ISIN, WKN, or symbol.
    Uses HTMX for dynamic updates without page reloads.

    Args:
        request: FastAPI request object

    Returns:
        Rendered HTML response
    """
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "app_name": settings.APP_NAME,
        },
    )


@app.get(
    "/health",
    tags=["Health"],
    summary="Health check",
    description="Check service health and dependencies",
)
async def health_check() -> Dict[str, Any]:
    """
    Perform health check on frontend service and dependencies.

    Checks the health of this service and all dependent services.
    Returns detailed status information for monitoring.

    Returns:
        Dictionary with health status information:
        {
            "status": "healthy" | "degraded",
            "service": "frontend-service",
            "dependencies": {
                "search_service": "healthy" | "unhealthy"
            }
        }
    """
    search_service_healthy = await search_client.health_check()

    return {
        "status": "healthy" if search_service_healthy else "degraded",
        "service": "frontend-service",
        "dependencies": {
            "search_service": "healthy" if search_service_healthy else "unhealthy",
        },
    }


@app.get(
    "/search",
    response_class=HTMLResponse,
    tags=["Search"],
    summary="Search for stock",
    description="Search for stock by ISIN, WKN, or symbol and return HTML partial",
)
async def search_stock(
    request: Request,
    query: str = Query(
        ...,
        min_length=1,
        max_length=100,  # Increased from 20 to support company names like "Deutsche Bank AG"
        description="Company name, ISIN, WKN, or symbol to search for",
    ),
) -> HTMLResponse:
    """
    Search for stock and return HTML partial for HTMX.

    Performs a stock search using the provided query and returns
    an HTML partial that can be inserted into the page by HTMX.

    Supports worldwide stock search by:
    - Company names (e.g., "Amazon", "Microsoft", "Deutsche Bank")
    - Stock symbols (e.g., "AAPL", "MSFT", "DBK.DE")
    - ISIN codes (e.g., "US0378331005")
    - WKN codes (e.g., "865985")

    Args:
        request: FastAPI request object
        query: Company name, ISIN, WKN, or symbol to search for

    Returns:
        HTML partial with stock card or error message

    Example:
        GET /search?query=Deutsche+Bank
        Returns: HTML partial with Deutsche Bank stock information (DB or DBK.DE)
    """
    logger.info(f"Search request received: query='{query}'")

    # Call search service
    result = await search_client.search(query)

    if result.get("success"):
        # Stock found - return stock card
        logger.info(
            f"Stock found for query '{query}': {result.get('data', {}).get('name')}"
        )
        return templates.TemplateResponse(
            request=request,
            name="components/stock_card.html",
            context={
                "stock": result.get("data"),
                "response_time": result.get("response_time_ms", 0),
                "query_type": result.get("query_type", "unknown"),
            },
        )
    else:
        # Stock not found or error - return error message
        logger.warning(f"Stock not found for query '{query}': {result.get('message')}")
        error_message = result.get("message", "Stock not found")

        return templates.TemplateResponse(
            request=request,
            name="components/error.html",
            context={
                "error_title": "Stock Not Found",
                "error_message": error_message,
                "error_details": result.get("detail"),
                "suggestions_list": _get_search_suggestions(),
            },
        )


@app.get(
    "/api/suggestions",
    response_class=HTMLResponse,
    tags=["Search"],
    summary="Get autocomplete suggestions",
    description="Get search suggestions for autocomplete functionality",
)
async def get_suggestions(
    request: Request,
    query: str = Query(
        ...,
        min_length=1,
        description="Partial search query",
    ),
) -> HTMLResponse:
    """
    Get autocomplete suggestions for HTMX.

    Retrieves search suggestions based on the partial query string
    to provide autocomplete functionality in the search interface.

    Args:
        request: FastAPI request object
        query: Partial search query string

    Returns:
        HTML partial with suggestion list

    Example:
        GET /api/suggestions?query=DE
        Returns: HTML partial with suggestions starting with "DE"
    """
    logger.debug(f"Suggestions request: query='{query}'")

    suggestions = await search_client.get_suggestions(query, limit=5)

    return templates.TemplateResponse(
        request=request,
        name="components/suggestions.html",
        context={
            "suggestions": suggestions,
            "query": query,
        },
    )


@app.get(
    "/about",
    response_class=HTMLResponse,
    tags=["Pages"],
    summary="About page",
    description="Information about the QNT9 Stock Recommendation System",
)
async def about_page(request: Request) -> HTMLResponse:
    """
    Render the about page.

    Provides information about the QNT9 Stock Recommendation System,
    its features, and usage instructions.

    Args:
        request: FastAPI request object

    Returns:
        Rendered HTML response
    """
    return templates.TemplateResponse(
        request=request,
        name="about.html",
        context={
            "app_name": settings.APP_NAME,
        },
    )


def _get_search_suggestions() -> List[str]:
    """
    Get helpful suggestions for failed searches.

    Returns a list of suggestions to help users refine their search queries
    when a search fails.

    Returns:
        List of suggestion strings
    """
    return [
        "Try searching by company name (e.g., 'Amazon', 'Microsoft', 'Deutsche Bank')",
        "Verify the ISIN follows the format: 2-letter country code + 10 alphanumeric characters",
        "Verify WKN is 6 characters with at least one digit (letters or numbers)",
        "Check if the stock symbol includes the exchange (e.g., DBK.DE for Deutsche Bank)",
        "Try searching with a different identifier type",
    ]


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=settings.HOST,
        port=settings.PORT,
        log_level=settings.LOG_LEVEL.lower(),
    )
