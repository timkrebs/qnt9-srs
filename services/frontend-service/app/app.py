"""
Frontend Service - Main FastAPI Application
Provides web UI for stock search using HTMX
"""

import logging
from pathlib import Path

from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .api_client import search_client
from .config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="QNT9 Frontend Service",
    description="Web UI for QNT9 Stock Recommendation System",
    version="1.0.0",
    docs_url="/api/docs" if settings.DEBUG else None,
    redoc_url="/api/redoc" if settings.DEBUG else None,
)

# Setup templates and static files
BASE_PATH = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_PATH / "templates"))

# Mount static files (will be created next)
try:
    app.mount("/static", StaticFiles(directory=str(BASE_PATH / "static")), name="static")
except RuntimeError:
    logger.warning("Static directory not found - will be created")


@app.on_event("startup")
async def startup_event():
    """Application startup"""
    logger.info("Starting Frontend Service...")
    logger.info(f"Search Service URL: {settings.SEARCH_SERVICE_URL}")

    # Check search service health
    is_healthy = await search_client.health_check()
    if is_healthy:
        logger.info("Search service is healthy")
    else:
        logger.warning("Search service is not responding")


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown"""
    logger.info("Shutting down Frontend Service...")


@app.get("/", response_class=HTMLResponse, tags=["Pages"])
async def homepage(request: Request):
    """
    Homepage with stock search functionality
    """
    return templates.TemplateResponse(
        "index.html", {"request": request, "app_name": settings.APP_NAME}
    )


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    search_service_healthy = await search_client.health_check()

    return {
        "status": "healthy",
        "service": "frontend-service",
        "dependencies": {"search_service": "healthy" if search_service_healthy else "unhealthy"},
    }


@app.get("/search", response_class=HTMLResponse, tags=["Search"])
async def search_stock(request: Request, query: str = Query(..., min_length=1, max_length=20)):
    """
    Search for stock and return HTML partial (for HTMX)

    Args:
        query: ISIN, WKN, or symbol to search

    Returns:
        HTML partial with stock card or error message
    """
    logger.info(f"Search request: {query}")

    # Call search service
    result = await search_client.search(query)

    if result.get("success"):
        # Stock found - return stock card
        return templates.TemplateResponse(
            "components/stock_card.html",
            {
                "request": request,
                "stock": result.get("data"),
                "response_time": result.get("response_time_ms", 0),
                "query_type": result.get("query_type", "unknown"),
            },
        )
    else:
        # Stock not found or error - return error message
        error_message = result.get("message", "Stock not found")
        return templates.TemplateResponse(
            "components/error.html",
            {
                "request": request,
                "error_title": "Stock Not Found",
                "error_message": error_message,
                "error_details": result.get("detail"),
                "suggestions_list": [
                    "Verify the ISIN follows the format: 2-letter country code + 10 alphanumeric characters",
                    "Verify WKN is 6 characters (letters or numbers)",
                    "Check if the stock symbol includes the exchange (e.g., DBK.DE for Deutsche Bank)",
                    "Try searching with a different identifier type",
                ],
            },
        )


@app.get("/api/suggestions", response_class=HTMLResponse, tags=["Search"])
async def get_suggestions(request: Request, query: str = Query(..., min_length=1)):
    """
    Get autocomplete suggestions (for HTMX)

    Args:
        query: Partial search query

    Returns:
        HTML partial with suggestion list
    """
    suggestions = await search_client.get_suggestions(query, limit=5)

    return templates.TemplateResponse(
        "components/suggestions.html",
        {"request": request, "suggestions": suggestions, "query": query},
    )


@app.get("/about", response_class=HTMLResponse, tags=["Pages"])
async def about_page(request: Request):
    """About page"""
    return templates.TemplateResponse(
        "about.html", {"request": request, "app_name": settings.APP_NAME}
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.HOST, port=settings.PORT, log_level="info")
