"""
Main FastAPI application with Clean Architecture structure.

This file wires together all layers:
- Domain: Business entities and rules
- Infrastructure: External APIs, databases
- Repositories: Data access
- Services: Business logic orchestration
- Routers: HTTP endpoints
"""

import os
from contextlib import asynccontextmanager
from typing import Optional, Union

import redis.asyncio as redis
import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, generate_latest
from sqlalchemy.orm import Session

from .consul import ConsulClient, get_service_id
from .database import get_db, init_db
from .dependencies import set_stock_service
from .infrastructure.yahoo_finance_client import YahooFinanceClient
from .repositories.postgres_repository import (
    PostgresSearchHistoryRepository,
    PostgresStockRepository,
)
from .repositories.redis_repository import RedisStockRepository
from .routers import health_router, legacy_router, search_router
from .services.stock_service import StockSearchService

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

# Prometheus metrics
REQUEST_COUNT = Counter(
    "search_service_requests_total",
    "Total number of requests",
    ["method", "endpoint", "status"],
)

REQUEST_LATENCY = Histogram(
    "search_service_request_latency_seconds",
    "Request latency in seconds",
    ["method", "endpoint"],
)

CACHE_HITS = Counter(
    "search_service_cache_hits_total", "Total cache hits", ["cache_layer"]
)

# Global state
redis_client: Optional[redis.Redis] = None
stock_service: Optional[StockSearchService] = None

# Initialize Consul client
consul_enabled = os.getenv("CONSUL_ENABLED", "false").lower() == "true"
consul_host = os.getenv("CONSUL_HOST", "consul")
consul_port = int(os.getenv("CONSUL_PORT", "8500"))
use_service_discovery = os.getenv("USE_SERVICE_DISCOVERY", "false").lower() == "true"

consul_client = ConsulClient(enabled=consul_enabled, host=consul_host, port=consul_port)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global redis_client, stock_service

    logger.info("Starting Search Service 2.0...")

    # Register with Consul
    service_name = os.getenv("SERVICE_NAME", "search-service")
    service_port = int(os.getenv("PORT", "8000"))
    service_id = get_service_id(service_name)

    consul_client.register_service(
        service_id=service_id,
        service_name=service_name,
        port=service_port,
        health_check_path="/api/v1/health",  # Correct health endpoint
        tags=["v1", "http", "search", "api"],
        meta={"version": "2.0.0"},
    )

    # Initialize PostgreSQL
    try:
        init_db()
        logger.info("PostgreSQL initialized successfully")
    except Exception as e:
        logger.error("Failed to initialize PostgreSQL", error=str(e))
        raise

    # Initialize Redis
    try:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        redis_client = await redis.from_url(
            redis_url, encoding="utf-8", decode_responses=False
        )
        await redis_client.ping()
        logger.info("Redis connected successfully", url=redis_url)
    except Exception as e:
        logger.warning("Redis not available, using PostgreSQL only", error=str(e))
        redis_client = None

    # Initialize service dependencies
    try:
        stock_service = create_stock_service(redis_client)
        set_stock_service(stock_service)  # Set global dependency
        logger.info("Stock service initialized")
    except Exception as e:
        logger.error("Failed to initialize stock service", error=str(e))
        raise

    logger.info("Search Service 2.0 started successfully")

    yield

    # Shutdown
    logger.info("Shutting down Search Service...")

    # Deregister from Consul
    consul_client.deregister_service(service_id)

    if redis_client:
        await redis_client.close()
        logger.info("Redis connection closed")

    logger.info("Search Service shut down complete")


def create_stock_service(redis_client: redis.Redis = None) -> StockSearchService:
    """
    Create and configure stock search service with all dependencies.

    Args:
        redis_client: Redis client (optional, will use PostgreSQL only if None)

    Returns:
        Configured StockSearchService instance
    """
    # Get database session
    db: Session = next(get_db())

    # Create repositories
    postgres_repo = PostgresStockRepository(db, cache_ttl_minutes=5)

    redis_repo: Union[RedisStockRepository, PostgresStockRepository]
    if redis_client:
        redis_repo = RedisStockRepository(redis_client, ttl_seconds=300)
    else:
        # Fallback to using PostgreSQL as both layers
        redis_repo = postgres_repo

    history_repo = PostgresSearchHistoryRepository(db)

    # Create external API client
    yahoo_client = YahooFinanceClient(
        timeout_seconds=5.0, max_retries=3, rate_limit_requests=5, rate_limit_window=1
    )

    # Create service
    return StockSearchService(
        redis_repo=redis_repo,
        postgres_repo=postgres_repo,
        api_client=yahoo_client,
        history_repo=history_repo,
    )


# Create FastAPI app
app = FastAPI(
    title="QNT9 Stock Search Service v2",
    description="Robust stock search microservice with Clean Architecture",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)


# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request ID middleware
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Add request ID for distributed tracing."""
    request_id = request.headers.get("X-Request-ID", f"req-{id(request)}")

    # Add to structlog context
    structlog.contextvars.bind_contextvars(request_id=request_id)

    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id

    structlog.contextvars.clear_contextvars()

    return response


# Metrics middleware
@app.middleware("http")
async def track_metrics(request: Request, call_next):
    """Track Prometheus metrics."""
    import time

    start_time = time.time()

    response = await call_next(request)

    # Record metrics
    duration = time.time() - start_time
    REQUEST_COUNT.labels(
        method=request.method, endpoint=request.url.path, status=response.status_code
    ).inc()

    REQUEST_LATENCY.labels(method=request.method, endpoint=request.url.path).observe(
        duration
    )

    return response


# Include routers
app.include_router(search_router.router)
app.include_router(health_router.router)
app.include_router(legacy_router.router)  # Legacy endpoints for backwards compatibility


# Prometheus metrics endpoint
@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    from fastapi.responses import Response

    return Response(content=generate_latest(), media_type="text/plain")


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "QNT9 Stock Search Service",
        "version": "2.0.0",
        "architecture": "Clean Architecture",
        "status": "operational",
        "docs": "/api/docs",
        "health": "/api/v1/health",
        "ready": "/api/v1/ready",
    }


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions."""
    logger.error(
        "Unhandled exception",
        path=request.url.path,
        method=request.method,
        error=str(exc),
        exc_info=True,
    )

    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "internal_server_error",
            "message": "An unexpected error occurred",
            "request_id": request.headers.get("X-Request-ID"),
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.app_v2:app", host="0.0.0.0", port=8000, reload=True, log_level="info"
    )
