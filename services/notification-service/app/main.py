"""Finio Notification Service - Main FastAPI Application.

Provides notification functionality including price alerts and daily summaries.
"""

from contextlib import asynccontextmanager
import sys
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app
import structlog

from app.config import settings
from app.database import db
from app.routers import preferences, admin
from app.workers.price_monitor import PriceMonitorWorker
from app.workers.daily_summary import DailySummaryWorker

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
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Worker instances (initialized in lifespan)
price_monitor: PriceMonitorWorker = None
daily_summary: DailySummaryWorker = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan context manager.

    Handles startup and shutdown events for the application.
    """
    global price_monitor, daily_summary

    # Startup
    logger.info("Starting notification service", service=settings.SERVICE_NAME)

    try:
        await db.connect()
        logger.info("Database connected")

        price_monitor = PriceMonitorWorker()
        await price_monitor.start()
        logger.info(
            "Price monitor worker started",
            send_hour=settings.PRICE_ALERT_SEND_HOUR,
        )

        daily_summary = DailySummaryWorker()
        await daily_summary.start()
        logger.info(
            "Daily summary worker started",
            send_hour=settings.DAILY_SUMMARY_SEND_HOUR,
        )

    except Exception as e:
        logger.error("Failed to start service", error=str(e))
        sys.exit(1)

    yield

    # Shutdown
    logger.info("Shutting down notification service")

    if price_monitor:
        await price_monitor.stop()
        logger.info("Price monitor worker stopped")

    if daily_summary:
        await daily_summary.stop()
        logger.info("Daily summary worker stopped")

    await db.disconnect()
    logger.info("Database disconnected")


app = FastAPI(
    title="Finio Notification Service",
    description="Notification service for price alerts and daily summaries",
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

app.include_router(preferences.router)
app.include_router(admin.router)

metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        await db.fetchval("SELECT 1")
        return {
            "status": "healthy",
            "service": settings.SERVICE_NAME,
            "database": "connected",
        }
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return {
            "status": "unhealthy",
            "service": settings.SERVICE_NAME,
            "database": "disconnected",
            "error": str(e),
        }


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": settings.SERVICE_NAME,
        "version": "1.0.0",
        "status": "running",
    }


@app.post("/api/v1/test/daily-summary")
async def test_daily_summary():
    """
    Test endpoint to manually trigger daily summary emails.
    
    This will send daily summary emails to all eligible users immediately.
    Use for testing purposes only.
    """
    if not daily_summary:
        return {"success": False, "error": "Daily summary worker not initialized"}
    
    try:
        logger.info("Manually triggering daily summary")
        await daily_summary._send_daily_summaries()
        return {
            "success": True,
            "message": "Daily summary job triggered successfully",
        }
    except Exception as e:
        logger.error("Failed to trigger daily summary", error=str(e))
        return {
            "success": False,
            "error": str(e),
        }


@app.post("/api/v1/test/price-alerts")
async def test_price_alerts():
    """
    Test endpoint to manually trigger price alert checks.
    
    This will check all price alerts and send notifications immediately.
    Use for testing purposes only.
    """
    if not price_monitor:
        return {"success": False, "error": "Price monitor worker not initialized"}
    
    try:
        logger.info("Manually triggering price alerts check")
        await price_monitor._check_price_alerts()
        return {
            "success": True,
            "message": "Price alerts check triggered successfully",
        }
    except Exception as e:
        logger.error("Failed to trigger price alerts", error=str(e))
        return {
            "success": False,
            "error": str(e),
        }


@app.get("/api/v1/test/eligible-users")
async def get_eligible_users():
    """
    Get list of users eligible for daily summary.
    
    Returns users who have stock_news notifications enabled and have watchlist items.
    """
    if not daily_summary:
        return {"success": False, "error": "Daily summary worker not initialized"}
    
    try:
        users = await daily_summary._get_eligible_users()
        return {
            "success": True,
            "count": len(users),
            "users": [
                {
                    "user_id": str(u["user_id"]),
                    "email": u["email"],
                    "full_name": u.get("full_name"),
                }
                for u in users
            ],
        }
    except Exception as e:
        logger.error("Failed to get eligible users", error=str(e))
        return {
            "success": False,
            "error": str(e),
        }
