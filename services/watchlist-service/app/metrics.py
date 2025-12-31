"""
Prometheus metrics for Watchlist Service.

Tracks watchlist operations, tier limits, and performance.
"""

from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response

# Request metrics
http_requests_total = Counter(
    "watchlist_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"]
)

http_request_duration_seconds = Histogram(
    "watchlist_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0)
)

# Watchlist metrics
watchlist_add_total = Counter(
    "watchlist_add_total",
    "Total watchlist add operations",
    ["status", "tier"]
)

watchlist_remove_total = Counter(
    "watchlist_remove_total",
    "Total watchlist remove operations",
    ["status"]
)

watchlist_get_total = Counter(
    "watchlist_get_total",
    "Total watchlist retrieve operations",
    ["status"]
)

watchlist_items_per_user = Histogram(
    "watchlist_items_per_user",
    "Distribution of watchlist items per user",
    ["tier"],
    buckets=(1, 2, 3, 5, 10, 25, 50, 100, 250, 500, 1000)
)

# Tier limit metrics
watchlist_tier_limit_exceeded = Counter(
    "watchlist_tier_limit_exceeded_total",
    "Total tier limit exceeded errors",
    ["tier"]
)

watchlist_active_users = Gauge(
    "watchlist_active_users",
    "Active users with watchlists",
    ["tier"]
)

# Database metrics
watchlist_db_operations_total = Counter(
    "watchlist_db_operations_total",
    "Total database operations",
    ["operation", "status"]
)

watchlist_db_operation_duration_seconds = Histogram(
    "watchlist_db_operation_duration_seconds",
    "Database operation duration in seconds",
    ["operation"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0)
)


def track_request_metrics(method: str, endpoint: str, status_code: int, duration: float):
    """Track HTTP request metrics."""
    http_requests_total.labels(method=method, endpoint=endpoint, status=status_code).inc()
    http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(duration)


def track_watchlist_add(success: bool, tier: str):
    """Track watchlist add operations."""
    status = "success" if success else "failure"
    watchlist_add_total.labels(status=status, tier=tier).inc()


def track_watchlist_remove(success: bool):
    """Track watchlist remove operations."""
    status = "success" if success else "failure"
    watchlist_remove_total.labels(status=status).inc()


def track_watchlist_get(success: bool):
    """Track watchlist retrieve operations."""
    status = "success" if success else "failure"
    watchlist_get_total.labels(status=status).inc()


def track_watchlist_size(tier: str, size: int):
    """Track watchlist size distribution."""
    watchlist_items_per_user.labels(tier=tier).observe(size)


def track_tier_limit_exceeded(tier: str):
    """Track tier limit exceeded errors."""
    watchlist_tier_limit_exceeded.labels(tier=tier).inc()


def update_active_users(tier: str, count: int):
    """Update active users gauge."""
    watchlist_active_users.labels(tier=tier).set(count)


def track_db_operation(operation: str, success: bool, duration: float):
    """Track database operation metrics."""
    status = "success" if success else "failure"
    watchlist_db_operations_total.labels(operation=operation, status=status).inc()
    watchlist_db_operation_duration_seconds.labels(operation=operation).observe(duration)


async def metrics_endpoint():
    """
    Prometheus metrics endpoint.
    
    Returns:
        Response with Prometheus metrics in text format
    """
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
