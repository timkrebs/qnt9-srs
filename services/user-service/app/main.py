"""
FastAPI application for User Service.

Manages user profiles, subscription tiers, and tier-based access control.
Implements in-memory caching for improved performance.
"""

from contextlib import asynccontextmanager
from datetime import datetime

import asyncpg
import structlog
from app.cache import cache_key_user_profile, user_profile_cache
from app.config import settings
from app.db.connection import db_manager, get_db_connection
from app.metrics import metrics_endpoint, track_request_metrics
from app.metrics_middleware import PrometheusMiddleware
from app.models import (HealthResponse, MessageResponse, SubscriptionUpdate,
                        UserProfile)
from app.shutdown_handler import setup_graceful_shutdown
from app.tracing import configure_opentelemetry, instrument_fastapi
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware

logger = structlog.get_logger()

# Configure OpenTelemetry tracing
configure_opentelemetry(
    service_name="user-service",
    service_version="1.0.0",
    enable_tracing=True,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting User Service")
    await db_manager.connect()
    logger.info("User Service started")

    # Setup graceful shutdown handlers
    shutdown_handler = setup_graceful_shutdown(
        service_name="user-service", cleanup_callbacks=[db_manager.disconnect]
    )
    app.state.shutdown_handler = shutdown_handler
    app.state.is_shutting_down = False

    logger.info("Graceful shutdown handlers configured")

    yield

    logger.info("Shutting down User Service")
    app.state.is_shutting_down = True
    await db_manager.disconnect()
    logger.info("User Service shutdown complete")


app = FastAPI(
    title="Finio User Service",
    description="User profile and subscription management for Finio Stock Research",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)

# CORS middleware with restricted permissions for production
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


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint with cache stats."""
    return {
        "status": "healthy",
        "service": "user-service",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "cache_stats": user_profile_cache.get_stats(),
    }


@app.get("/users/{user_id}", response_model=UserProfile)
async def get_user_profile(
    user_id: str, conn: asyncpg.Connection = Depends(get_db_connection)
):
    """Get user profile with tier information. Uses caching for performance."""
    try:
        # Check cache first
        cache_key = cache_key_user_profile(user_id)
        cached_profile = user_profile_cache.get(cache_key)
        if cached_profile:
            logger.debug("Cache hit for user profile", user_id=user_id)
            return UserProfile(**cached_profile)

        # Cache miss - fetch from database
        row = await conn.fetchrow(
            """
            SELECT id, email, tier, subscription_start, subscription_end,
                   stripe_customer_id, last_login, created_at, updated_at
            FROM users
            WHERE id = $1
            """,
            user_id,
        )

        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        profile_data = dict(row)

        # Cache the result (60 second TTL)
        user_profile_cache.set(cache_key, profile_data)
        logger.debug("Cached user profile", user_id=user_id)

        return UserProfile(**profile_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to fetch user profile", user_id=user_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch user profile",
        )


@app.post("/users/{user_id}/upgrade", response_model=MessageResponse)
async def upgrade_user(
    user_id: str,
    subscription: SubscriptionUpdate,
    conn: asyncpg.Connection = Depends(get_db_connection),
):
    """
    Upgrade user to paid tier.

    This is a stub implementation. In production, this would:
    1. Validate payment with Stripe
    2. Create Stripe customer and subscription
    3. Handle webhooks for subscription events
    """
    try:
        # Check if user exists
        user = await conn.fetchrow("SELECT id, email FROM users WHERE id = $1", user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        # Stub Stripe integration
        stripe_customer_id = f"cus_stub_{user_id[:8]}"
        stripe_subscription_id = f"sub_stub_{user_id[:8]}"

        # Update user tier
        await conn.execute(
            """
            UPDATE users
            SET tier = 'paid',
                subscription_start = NOW(),
                subscription_end = NOW() + INTERVAL '1 month',
                stripe_customer_id = $2,
                stripe_subscription_id = $3,
                updated_at = NOW()
            WHERE id = $1
            """,
            user_id,
            stripe_customer_id,
            stripe_subscription_id,
        )

        logger.info(
            "User upgraded to paid tier", user_id=user_id, plan=subscription.plan
        )

        # Invalidate user profile cache
        user_profile_cache.delete(cache_key_user_profile(user_id))

        # Trigger training for user's watchlist stocks
        await trigger_watchlist_training(user_id, conn)

        return MessageResponse(
            message=f"Successfully upgraded to {subscription.plan} plan", success=True
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to upgrade user", user_id=user_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upgrade user",
        )


@app.post("/users/{user_id}/downgrade", response_model=MessageResponse)
async def downgrade_user(
    user_id: str, conn: asyncpg.Connection = Depends(get_db_connection)
):
    """Downgrade user to free tier."""
    try:
        # Check if user exists
        user = await conn.fetchrow("SELECT id FROM users WHERE id = $1", user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        # Update user tier
        await conn.execute(
            """
            UPDATE users
            SET tier = 'free',
                subscription_end = NOW(),
                updated_at = NOW()
            WHERE id = $1
            """,
            user_id,
        )

        logger.info("User downgraded to free tier", user_id=user_id)

        # Invalidate user profile cache
        user_profile_cache.delete(cache_key_user_profile(user_id))

        return MessageResponse(
            message="Successfully downgraded to free tier", success=True
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to downgrade user", user_id=user_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to downgrade user",
        )


@app.patch("/users/{user_id}/last-login")
async def update_last_login(
    user_id: str, conn: asyncpg.Connection = Depends(get_db_connection)
):
    """Update user's last login timestamp."""
    try:
        await conn.execute(
            "UPDATE users SET last_login = NOW(), updated_at = NOW() WHERE id = $1",
            user_id,
        )
        # Invalidate cache since last_login changed
        user_profile_cache.delete(cache_key_user_profile(user_id))
        return {"message": "Last login updated"}
    except Exception as e:
        logger.error("Failed to update last login", user_id=user_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update last login",
        )


async def trigger_watchlist_training(user_id: str, conn: asyncpg.Connection):
    """
    Trigger training for all stocks in user's watchlist.

    This queues training jobs for stocks that don't have recent predictions.
    """
    try:
        # Get user's watchlist stocks
        stocks = await conn.fetch(
            "SELECT symbol FROM watchlists WHERE user_id = $1", user_id
        )

        if not stocks:
            return

        # Check which stocks need training
        for stock in stocks:
            symbol = stock["symbol"]

            # Check if predictions exist and are fresh
            last_prediction = await conn.fetchrow(
                """
                SELECT created_at FROM prediction_cache
                WHERE symbol = $1 AND expires_at > NOW()
                ORDER BY created_at DESC
                LIMIT 1
                """,
                symbol,
            )

            # If no recent predictions, queue training job
            if not last_prediction:
                job_id = await conn.fetchval(
                    """
                    INSERT INTO training_jobs (symbol, status, priority)
                    VALUES ($1, 'queued', 8)
                    RETURNING id
                    """,
                    symbol,
                )
                logger.info("Training job queued", symbol=symbol, job_id=str(job_id))

    except Exception as e:
        logger.error(
            "Failed to trigger watchlist training", user_id=user_id, error=str(e)
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.SERVICE_HOST,
        port=settings.SERVICE_PORT,
        reload=True,
        log_level=settings.LOG_LEVEL.lower(),
    )
