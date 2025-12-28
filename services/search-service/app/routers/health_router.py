"""
Health check and monitoring router.

Provides endpoints for health checks, readiness probes, and metrics.
"""

import logging
from datetime import datetime

from fastapi import APIRouter, status
from pydantic import BaseModel

from ..cache.memory_cache import get_memory_cache
from ..database import get_db_stats

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
async def readiness_check():
    """
    Readiness check.

    Checks if all dependencies are available:
    - PostgreSQL database
    - Redis cache
    - External APIs

    Returns 200 if ready, 503 if not ready.
    Used by Kubernetes readiness probes.
    """
    checks = {
        "database": "healthy",  # TODO: Implement actual DB check
        "redis": "healthy",  # TODO: Implement actual Redis check
        "external_api": "healthy",  # TODO: Implement actual API check
    }

    all_ready = all(check == "healthy" for check in checks.values())

    response = ReadinessResponse(
        ready=all_ready, checks=checks, timestamp=datetime.utcnow().isoformat()
    )

    if not all_ready:
        return response  # FastAPI will return 200 by default

    return response


@router.get("/metrics", summary="Prometheus metrics", description="Prometheus metrics endpoint")
async def metrics():
    """
    Prometheus metrics endpoint.

    Returns metrics in Prometheus format.
    TODO: Implement with prometheus_client library.
    """
    # TODO: Implement Prometheus metrics
    # from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    # return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

    return {"message": "Metrics endpoint - to be implemented with prometheus_client"}


@router.get(
    "/cache/stats", summary="Cache statistics", description="Get statistics for all cache layers"
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
