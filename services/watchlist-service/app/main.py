"""
Watchlist Service - Main Application.

Manages user watchlists with tier-based limits:
- Free tier: Maximum 3 stocks
- Paid/Enterprise: Unlimited stocks
"""

from contextlib import asynccontextmanager

import structlog
from app.auth import User, get_current_user
from app.config import settings
from app.database import close_db_pool, get_db_connection, get_db_pool
from app.metrics import metrics_endpoint, track_request_metrics
from app.metrics_middleware import PrometheusMiddleware
from app.models import (ErrorResponse, MessageResponse, WatchlistCreate,
                        WatchlistItem, WatchlistResponse, WatchlistUpdate)
from app.shutdown_handler import setup_graceful_shutdown
from app.tracing import configure_opentelemetry, instrument_fastapi
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

# Configure OpenTelemetry tracing
configure_opentelemetry(
    service_name="watchlist-service",
    service_version="1.0.0",
    enable_tracing=not settings.DEBUG,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting Watchlist Service", version="1.0.0")
    await get_db_pool()
    logger.info("Watchlist Service started")

    # Setup graceful shutdown handlers
    shutdown_handler = setup_graceful_shutdown(
        service_name="watchlist-service", cleanup_callbacks=[close_db_pool]
    )
    app.state.shutdown_handler = shutdown_handler
    app.state.is_shutting_down = False

    logger.info("Graceful shutdown handlers configured")

    yield

    # Shutdown
    logger.info("Shutting down Watchlist Service")
    app.state.is_shutting_down = True
    await close_db_pool()
    logger.info("Watchlist Service stopped")


app = FastAPI(
    title="Watchlist Service",
    description="Manage user stock watchlists with tier-based limits",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)

# CORS middleware with restricted permissions
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=[
        "Content-Type",
        "Authorization",
        "Accept",
        "Origin",
        "X-Requested-With",
    ],
    expose_headers=["Content-Length", "X-Request-ID"],
    max_age=600,
)

# Add Prometheus metrics middleware
app.add_middleware(PrometheusMiddleware, track_func=track_request_metrics)

# Instrument FastAPI with OpenTelemetry
instrument_fastapi(app, excluded_urls="/health,/metrics")


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
        if request.url.path in ["/health", "/metrics"]:
            return await call_next(request)

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service is shutting down",
        )

    return await call_next(request)


@app.get("/metrics", include_in_schema=False)
async def metrics():
    """Prometheus metrics endpoint."""
    return await metrics_endpoint()


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.SERVICE_NAME,
        "version": "1.0.0",
    }


@app.get(
    "/api/watchlist",
    response_model=WatchlistResponse,
    responses={
        200: {"description": "Watchlist retrieved successfully"},
        401: {"description": "Unauthorized", "model": ErrorResponse},
    },
    summary="Get user watchlist",
    tags=["Watchlist"],
)
async def get_watchlist(user: User = Depends(get_current_user)):
    """
    Get current user's watchlist.

    Returns all stocks in the user's watchlist with their details.
    """
    logger.info(
        "Fetching watchlist",
        user_id=user.id,
        user_email=user.email,
        user_tier=user.tier,
    )

    async with get_db_connection() as conn:
        # Log connection info for debugging
        db_user = await conn.fetchval("SELECT current_user")
        db_name = await conn.fetchval("SELECT current_database()")
        logger.debug(
            "Database connection established",
            db_user=db_user,
            db_name=db_name,
        )

        rows = await conn.fetch(
            """
            SELECT id, user_id, symbol, alert_enabled, alert_price_above,
                   alert_price_below, notes, added_at
            FROM watchlists
            WHERE user_id = $1
            ORDER BY added_at DESC
            """,
            user.id,
        )

        logger.info(
            "Watchlist query executed",
            user_id=user.id,
            rows_returned=len(rows),
        )

        watchlist = [
            WatchlistItem(
                id=str(row["id"]),
                user_id=str(row["user_id"]),
                symbol=row["symbol"],
                alert_enabled=row["alert_enabled"],
                alert_price_above=(
                    float(row["alert_price_above"])
                    if row["alert_price_above"]
                    else None
                ),
                alert_price_below=(
                    float(row["alert_price_below"])
                    if row["alert_price_below"]
                    else None
                ),
                notes=row["notes"],
                added_at=row["added_at"],
            )
            for row in rows
        ]

        # Determine limit based on tier
        limit = (
            settings.PAID_TIER_WATCHLIST_LIMIT
            if user.tier in ("paid", "enterprise")
            else settings.FREE_TIER_WATCHLIST_LIMIT
        )

        logger.info(
            "Watchlist retrieved",
            user_id=user.id,
            count=len(watchlist),
            tier=user.tier,
            limit=limit,
        )

        return WatchlistResponse(
            watchlist=watchlist,
            total=len(watchlist),
            tier=user.tier,
            limit=limit,
        )


@app.post(
    "/api/watchlist",
    response_model=WatchlistItem,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Stock added to watchlist"},
        400: {"description": "Bad request", "model": ErrorResponse},
        401: {"description": "Unauthorized", "model": ErrorResponse},
        403: {"description": "Tier limit exceeded", "model": ErrorResponse},
        409: {"description": "Stock already in watchlist", "model": ErrorResponse},
    },
    summary="Add stock to watchlist",
    tags=["Watchlist"],
)
async def add_to_watchlist(
    item: WatchlistCreate,
    user: User = Depends(get_current_user),
):
    """
    Add a stock to the user's watchlist.

    Tier limits:
    - Free tier: Maximum 3 stocks
    - Paid/Enterprise: Unlimited stocks

    Returns the created watchlist item.
    """
    async with get_db_connection() as conn:
        # Check current count
        count_row = await conn.fetchrow(
            "SELECT COUNT(*) as count FROM watchlists WHERE user_id = $1",
            user.id,
        )
        current_count = count_row["count"]

        # Determine limit based on tier
        limit = (
            settings.PAID_TIER_WATCHLIST_LIMIT
            if user.tier in ("paid", "enterprise")
            else settings.FREE_TIER_WATCHLIST_LIMIT
        )

        # Check tier limit
        if current_count >= limit:
            logger.warning(
                "Watchlist limit exceeded",
                user_id=user.id,
                tier=user.tier,
                current=current_count,
                limit=limit,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Watchlist limit reached. {user.tier.title()} tier allows {limit} stocks. Upgrade to add more.",
            )

        # Check if already exists
        existing = await conn.fetchrow(
            "SELECT id FROM watchlists WHERE user_id = $1 AND symbol = $2",
            user.id,
            item.symbol.upper(),
        )

        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"{item.symbol} is already in your watchlist",
            )

        # Insert new item
        logger.info(
            "Inserting watchlist item",
            user_id=user.id,
            symbol=item.symbol.upper(),
            alert_enabled=item.alert_enabled,
        )

        row = await conn.fetchrow(
            """
            INSERT INTO watchlists (user_id, symbol, alert_enabled, alert_price_above, alert_price_below, notes)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING id, user_id, symbol, alert_enabled, alert_price_above, alert_price_below, notes, added_at
            """,
            user.id,
            item.symbol.upper(),
            item.alert_enabled,
            item.alert_price_above,
            item.alert_price_below,
            item.notes,
        )

        if not row:
            logger.error(
                "Watchlist insert failed - no row returned",
                user_id=user.id,
                symbol=item.symbol.upper(),
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to add stock to watchlist",
            )

        logger.info(
            "Watchlist item inserted successfully",
            user_id=user.id,
            symbol=item.symbol.upper(),
            watchlist_id=str(row["id"]),
        )

        watchlist_item = WatchlistItem(
            id=str(row["id"]),
            user_id=str(row["user_id"]),
            symbol=row["symbol"],
            alert_enabled=row["alert_enabled"],
            alert_price_above=(
                float(row["alert_price_above"]) if row["alert_price_above"] else None
            ),
            alert_price_below=(
                float(row["alert_price_below"]) if row["alert_price_below"] else None
            ),
            notes=row["notes"],
            added_at=row["added_at"],
        )

        logger.info(
            "Stock added to watchlist",
            user_id=user.id,
            symbol=item.symbol,
            tier=user.tier,
            count=current_count + 1,
            limit=limit,
        )

        return watchlist_item


@app.delete(
    "/api/watchlist/{symbol}",
    response_model=MessageResponse,
    responses={
        200: {"description": "Stock removed from watchlist"},
        401: {"description": "Unauthorized", "model": ErrorResponse},
        404: {"description": "Stock not found in watchlist", "model": ErrorResponse},
    },
    summary="Remove stock from watchlist",
    tags=["Watchlist"],
)
async def remove_from_watchlist(
    symbol: str,
    user: User = Depends(get_current_user),
):
    """
    Remove a stock from the user's watchlist.

    Returns success message if stock was removed.
    """
    async with get_db_connection() as conn:
        result = await conn.execute(
            "DELETE FROM watchlists WHERE user_id = $1 AND symbol = $2",
            user.id,
            symbol.upper(),
        )

        # Check if any row was deleted
        if result == "DELETE 0":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{symbol} not found in your watchlist",
            )

        logger.info(
            "Stock removed from watchlist",
            user_id=user.id,
            symbol=symbol,
        )

        return MessageResponse(
            message=f"{symbol} removed from watchlist",
            success=True,
        )


@app.patch(
    "/api/watchlist/{symbol}",
    response_model=WatchlistItem,
    responses={
        200: {"description": "Watchlist item updated"},
        401: {"description": "Unauthorized", "model": ErrorResponse},
        404: {"description": "Stock not found in watchlist", "model": ErrorResponse},
    },
    summary="Update watchlist item",
    tags=["Watchlist"],
)
async def update_watchlist_item(
    symbol: str,
    updates: WatchlistUpdate,
    user: User = Depends(get_current_user),
):
    """
    Update watchlist item (notes, alerts).

    Only updates fields that are provided in the request.
    """
    async with get_db_connection() as conn:
        # Build dynamic UPDATE query
        update_fields = []
        params = [user.id, symbol.upper()]
        param_idx = 3

        if updates.notes is not None:
            update_fields.append(f"notes = ${param_idx}")
            params.append(updates.notes)
            param_idx += 1

        if updates.alert_enabled is not None:
            update_fields.append(f"alert_enabled = ${param_idx}")
            params.append(updates.alert_enabled)
            param_idx += 1

        if updates.alert_price_above is not None:
            update_fields.append(f"alert_price_above = ${param_idx}")
            params.append(updates.alert_price_above)
            param_idx += 1

        if updates.alert_price_below is not None:
            update_fields.append(f"alert_price_below = ${param_idx}")
            params.append(updates.alert_price_below)
            param_idx += 1

        if not update_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update",
            )

        query = f"""
            UPDATE watchlists
            SET {', '.join(update_fields)}
            WHERE user_id = $1 AND symbol = $2
            RETURNING id, user_id, symbol, alert_enabled, alert_price_above, alert_price_below, notes, added_at
        """

        row = await conn.fetchrow(query, *params)

        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{symbol} not found in your watchlist",
            )

        logger.info(
            "Watchlist item updated",
            user_id=user.id,
            symbol=symbol,
        )

        return WatchlistItem(
            id=str(row["id"]),
            user_id=str(row["user_id"]),
            symbol=row["symbol"],
            alert_enabled=row["alert_enabled"],
            alert_price_above=(
                float(row["alert_price_above"]) if row["alert_price_above"] else None
            ),
            alert_price_below=(
                float(row["alert_price_below"]) if row["alert_price_below"] else None
            ),
            notes=row["notes"],
            added_at=row["added_at"],
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.SERVICE_HOST,
        port=settings.SERVICE_PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
