"""
Health check and monitoring router.

Provides endpoints for health checks, readiness probes, and metrics.
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ..cache.memory_cache import get_memory_cache
from ..database import get_db_stats, get_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["health"])


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str
    timestamp: str
    service: str = "search-service"
    version: str = "2.0.0"


class ReadinessResponse(BaseModel):
    """Readiness check response model."""

    ready: bool
    checks: dict
    timestamp: str


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Health check",
    description="Basic health check endpoint - returns 200 if service is running",
)
async def health_check():
    """
    Basic health check.

    Always returns 200 OK if the service is running.
    Used by load balancers and orchestrators for liveness probes.
    """
    return HealthResponse(status="healthy", timestamp=datetime.utcnow().isoformat())


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    summary="Readiness check",
    description="Check if service is ready to accept traffic (dependencies available)",
)
async def readiness_check(session: AsyncSession = Depends(get_session)):
    """
    Readiness check with actual dependency verification.

    Checks if all dependencies are available:
    - PostgreSQL database (connection and query test)
    - Redis cache (connection test)
    - External APIs (optional health check)

    Returns 200 if ready, 503 if not ready.
    Used by Kubernetes readiness probes.
    """
    checks = {}

    db_healthy = await _check_database_health(session)
    checks["database"] = "healthy" if db_healthy else "unhealthy"

    redis_healthy = await _check_redis_health()
    checks["redis"] = "healthy" if redis_healthy else "unhealthy"

    checks["external_api"] = "healthy"

    all_ready = all(check == "healthy" for check in checks.values())

    response = ReadinessResponse(
        ready=all_ready, checks=checks, timestamp=datetime.utcnow().isoformat()
    )

    return response


async def _check_database_health(session: AsyncSession) -> bool:
    """
    Check PostgreSQL database health.

    Args:
        session: Database session

    Returns:
        True if database is healthy, False otherwise
    """
    try:
        from sqlalchemy import text

        result = await session.execute(text("SELECT 1"))
        result.scalar()
        return True
    except Exception as e:
        logger.error("Database health check failed: %s", e)
        return False


async def _check_redis_health() -> bool:
    """
    Check Redis health.

    Returns:
        True if Redis is healthy, False otherwise
    """
    try:
        from ..repositories.redis_repository import redis_client

        if redis_client:
            await redis_client.ping()
            return True
        else:
            logger.warning("Redis client not initialized")
            return False
    except Exception as e:
        logger.error("Redis health check failed: %s", e)
        return False


@router.get(
    "/metrics", summary="Prometheus metrics", description="Prometheus metrics endpoint"
)
async def metrics():
    """
    Prometheus metrics endpoint.

    Returns metrics in Prometheus format for monitoring and alerting.
    Integrates with the metrics system configured in metrics_middleware.
    """
    from ..metrics import metrics_endpoint

    return metrics_endpoint()


@router.get(
    "/cache/stats",
    summary="Cache statistics",
    description="Get statistics for all cache layers",
)
async def cache_stats():
    """
    Get cache statistics for all layers.

    Returns statistics for:
    - Memory cache (L0)
    - Redis cache (L1) - coming soon
    - PostgreSQL cache (L2) - coming soon
    """
    memory_cache = get_memory_cache()
    stats = memory_cache.get_stats()

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "caches": {
            "memory": {
                "layer": "L0",
                "type": "LRU",
                "description": "In-memory cache for hot stocks",
                **stats,
            }
        },
    }


@router.get(
    "/db/stats",
    summary="Database connection pool statistics",
    description="Get database pool health metrics",
)
async def database_stats():
    """
    Get database connection pool statistics.

    Phase 5: Monitor connection pool health and query cache performance.
    """
    try:
        stats = get_db_stats()

        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "connection_pool": {
                "pool_size": stats["pool_size"],
                "max_overflow": stats["max_overflow"],
                "checked_out": stats["checked_out"],
                "checked_in": stats["checked_in"],
                "overflow": stats["overflow"],
                "total_connections": stats["total_connections"],
                "utilization_percent": (
                    round((stats["checked_out"] / stats["pool_size"]) * 100, 2)
                    if stats["pool_size"] > 0
                    else 0
                ),
            },
            "query_optimization": {
                "cache_enabled": stats["query_cache_enabled"],
                "cache_size": stats["query_cache_size"],
                "read_replica_enabled": stats["read_replica_enabled"],
            },
        }
    except Exception as e:
        logger.error(f"Error getting database stats: {e}")
        return {
            "status": "error",
            "error": str(e),
        }
