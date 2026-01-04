"""
Prometheus metrics for Search Service.

Tracks search operations, cache performance, API fallback usage, and query patterns.
"""

from fastapi import Response
from prometheus_client import (CONTENT_TYPE_LATEST, Counter, Gauge, Histogram,
                               generate_latest)

# Request metrics
http_requests_total = Counter(
    "search_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)

http_request_duration_seconds = Histogram(
    "search_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=(
        0.005,
        0.01,
        0.025,
        0.05,
        0.075,
        0.1,
        0.25,
        0.5,
        0.75,
        1.0,
        2.5,
        5.0,
        7.5,
        10.0,
    ),
)

# Search metrics
search_queries_total = Counter(
    "search_queries_total", "Total search queries", ["query_type", "status"]
)

search_query_duration_seconds = Histogram(
    "search_query_duration_seconds",
    "Search query duration in seconds",
    ["query_type"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0),
)

search_results_per_query = Histogram(
    "search_results_per_query",
    "Number of results returned per query",
    ["query_type"],
    buckets=(0, 1, 5, 10, 25, 50, 100),
)

# Cache metrics
search_cache_hits_total = Counter(
    "search_cache_hits_total", "Total cache hits", ["cache_type"]
)

search_cache_misses_total = Counter(
    "search_cache_misses_total", "Total cache misses", ["cache_type"]
)

search_cache_size = Gauge(
    "search_cache_size", "Current cache size in items", ["cache_type"]
)

search_cache_evictions_total = Counter(
    "search_cache_evictions_total", "Total cache evictions", ["cache_type"]
)

# API source metrics
search_api_calls_total = Counter(
    "search_api_calls_total",
    "Total API calls to external providers",
    ["provider", "status"],
)

search_api_call_duration_seconds = Histogram(
    "search_api_call_duration_seconds",
    "API call duration in seconds",
    ["provider"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

search_api_fallback_total = Counter(
    "search_api_fallback_total",
    "Total API fallback attempts",
    ["from_provider", "to_provider"],
)

# Database metrics
search_db_operations_total = Counter(
    "search_db_operations_total", "Total database operations", ["operation", "status"]
)

search_db_operation_duration_seconds = Histogram(
    "search_db_operation_duration_seconds",
    "Database operation duration in seconds",
    ["operation"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
)


def track_request_metrics(
    method: str, endpoint: str, status_code: int, duration: float
):
    """Track HTTP request metrics."""
    http_requests_total.labels(
        method=method, endpoint=endpoint, status=status_code
    ).inc()
    http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(
        duration
    )


def track_search_query(
    query_type: str, success: bool, duration: float, result_count: int = 0
):
    """Track search query metrics."""
    status = "success" if success else "failure"
    search_queries_total.labels(query_type=query_type, status=status).inc()
    search_query_duration_seconds.labels(query_type=query_type).observe(duration)
    if success:
        search_results_per_query.labels(query_type=query_type).observe(result_count)


def track_cache_hit(cache_type: str = "search"):
    """Track cache hits."""
    search_cache_hits_total.labels(cache_type=cache_type).inc()


def track_cache_miss(cache_type: str = "search"):
    """Track cache misses."""
    search_cache_misses_total.labels(cache_type=cache_type).inc()


def update_cache_size(cache_type: str, size: int):
    """Update cache size gauge."""
    search_cache_size.labels(cache_type=cache_type).set(size)


def track_cache_eviction(cache_type: str = "search"):
    """Track cache evictions."""
    search_cache_evictions_total.labels(cache_type=cache_type).inc()


def track_api_call(provider: str, success: bool, duration: float):
    """Track external API calls."""
    status = "success" if success else "failure"
    search_api_calls_total.labels(provider=provider, status=status).inc()
    search_api_call_duration_seconds.labels(provider=provider).observe(duration)


def track_api_fallback(from_provider: str, to_provider: str):
    """Track API fallback attempts."""
    search_api_fallback_total.labels(
        from_provider=from_provider, to_provider=to_provider
    ).inc()


def track_db_operation(operation: str, success: bool, duration: float):
    """Track database operation metrics."""
    status = "success" if success else "failure"
    search_db_operations_total.labels(operation=operation, status=status).inc()
    search_db_operation_duration_seconds.labels(operation=operation).observe(duration)


async def metrics_endpoint():
    """
    Prometheus metrics endpoint.

    Returns:
        Response with Prometheus metrics in text format
    """
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
