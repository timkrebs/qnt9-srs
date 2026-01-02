"""
Prometheus metrics for User Service.

Tracks user profile operations, cache performance, and subscription management.
"""

from fastapi import Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

# Request metrics
http_requests_total = Counter(
    "user_http_requests_total", "Total HTTP requests", ["method", "endpoint", "status"]
)

http_request_duration_seconds = Histogram(
    "user_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0),
)

# User profile metrics
user_profile_operations_total = Counter(
    "user_profile_operations_total", "Total user profile operations", ["operation", "status"]
)

# Cache metrics
user_cache_hits_total = Counter("user_cache_hits_total", "Total cache hits", ["cache_type"])

user_cache_misses_total = Counter("user_cache_misses_total", "Total cache misses", ["cache_type"])

user_cache_size = Gauge("user_cache_size", "Current cache size", ["cache_type"])

user_cache_evictions_total = Counter(
    "user_cache_evictions_total", "Total cache evictions", ["cache_type"]
)

# Subscription metrics
user_subscription_updates_total = Counter(
    "user_subscription_updates_total", "Total subscription updates", ["tier", "status"]
)

user_active_subscriptions = Gauge(
    "user_active_subscriptions", "Active subscriptions by tier", ["tier"]
)

# Database metrics
user_db_operations_total = Counter(
    "user_db_operations_total", "Total database operations", ["operation", "status"]
)

user_db_operation_duration_seconds = Histogram(
    "user_db_operation_duration_seconds",
    "Database operation duration in seconds",
    ["operation"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
)


def track_request_metrics(method: str, endpoint: str, status_code: int, duration: float):
    """Track HTTP request metrics."""
    http_requests_total.labels(method=method, endpoint=endpoint, status=status_code).inc()
    http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(duration)


def track_profile_operation(operation: str, success: bool):
    """Track user profile operations."""
    status = "success" if success else "failure"
    user_profile_operations_total.labels(operation=operation, status=status).inc()


def track_cache_hit(cache_type: str = "profile"):
    """Track cache hits."""
    user_cache_hits_total.labels(cache_type=cache_type).inc()


def track_cache_miss(cache_type: str = "profile"):
    """Track cache misses."""
    user_cache_misses_total.labels(cache_type=cache_type).inc()


def update_cache_size(cache_type: str, size: int):
    """Update cache size gauge."""
    user_cache_size.labels(cache_type=cache_type).set(size)


def track_cache_eviction(cache_type: str = "profile"):
    """Track cache evictions."""
    user_cache_evictions_total.labels(cache_type=cache_type).inc()


def track_subscription_update(tier: str, success: bool):
    """Track subscription updates."""
    status = "success" if success else "failure"
    user_subscription_updates_total.labels(tier=tier, status=status).inc()


def update_active_subscriptions(tier: str, count: int):
    """Update active subscription gauge."""
    user_active_subscriptions.labels(tier=tier).set(count)


def track_db_operation(operation: str, success: bool, duration: float):
    """Track database operation metrics."""
    status = "success" if success else "failure"
    user_db_operations_total.labels(operation=operation, status=status).inc()
    user_db_operation_duration_seconds.labels(operation=operation).observe(duration)


async def metrics_endpoint():
    """
    Prometheus metrics endpoint.

    Returns:
        Response with Prometheus metrics in text format
    """
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
