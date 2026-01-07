from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app
import structlog
import sys

from app.config import settings
from app.database import db
from app.routers import preferences, admin
from app.workers.price_monitor import PriceMonitorWorker

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

app = FastAPI(
    title="QNT9 Notification Service",
    description="Notification service for price alerts and marketing emails",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(preferences.router)
app.include_router(admin.router)

metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

price_monitor: PriceMonitorWorker = None


@app.on_event("startup")
async def startup_event():
    """Initialize service on startup."""
    logger.info("Starting notification service", service=settings.SERVICE_NAME)

    try:
        await db.connect()
        logger.info("Database connected")

        global price_monitor
        price_monitor = PriceMonitorWorker()
        await price_monitor.start()
        logger.info("Price monitor worker started")

    except Exception as e:
        logger.error("Failed to start service", error=str(e))
        sys.exit(1)


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down notification service")

    if price_monitor:
        await price_monitor.stop()
        logger.info("Price monitor worker stopped")

    await db.disconnect()
    logger.info("Database disconnected")


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
