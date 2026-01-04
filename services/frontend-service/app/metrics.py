"""
Prometheus metrics for Frontend Service.

Tracks page views, API proxy requests, template rendering, and user interactions.
"""

from fastapi import Response
from prometheus_client import (CONTENT_TYPE_LATEST, Counter, Gauge, Histogram,
                               generate_latest)

# Request metrics
http_requests_total = Counter(
    "frontend_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)

http_request_duration_seconds = Histogram(
    "frontend_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=(0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0),
)

# Page view metrics
frontend_page_views_total = Counter(
    "frontend_page_views_total", "Total page views", ["page"]
)

frontend_page_load_duration_seconds = Histogram(
    "frontend_page_load_duration_seconds",
    "Page load duration in seconds",
    ["page"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0),
)

# Template rendering metrics
frontend_template_render_duration_seconds = Histogram(
    "frontend_template_render_duration_seconds",
    "Template rendering duration in seconds",
    ["template"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5),
)

# Proxy request metrics
frontend_proxy_requests_total = Counter(
    "frontend_proxy_requests_total",
    "Total proxy requests to backend services",
    ["service", "endpoint", "status"],
)

frontend_proxy_request_duration_seconds = Histogram(
    "frontend_proxy_request_duration_seconds",
    "Proxy request duration in seconds",
    ["service", "endpoint"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)

frontend_proxy_errors_total = Counter(
    "frontend_proxy_errors_total",
    "Total proxy request errors",
    ["service", "error_type"],
)

# User interaction metrics
frontend_search_queries_total = Counter(
    "frontend_search_queries_total", "Total search queries submitted", ["authenticated"]
)

frontend_watchlist_operations_total = Counter(
    "frontend_watchlist_operations_total",
    "Total watchlist operations",
    ["operation", "status"],
)

# Static file metrics
frontend_static_file_requests_total = Counter(
    "frontend_static_file_requests_total",
    "Total static file requests",
    ["file_type", "status"],
)

# Active users
frontend_active_sessions = Gauge(
    "frontend_active_sessions", "Number of active user sessions"
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


def track_page_view(page: str, duration: float):
    """Track page view metrics."""
    frontend_page_views_total.labels(page=page).inc()
    frontend_page_load_duration_seconds.labels(page=page).observe(duration)


def track_template_render(template: str, duration: float):
    """Track template rendering metrics."""
    frontend_template_render_duration_seconds.labels(template=template).observe(
        duration
    )


def track_proxy_request(service: str, endpoint: str, status_code: int, duration: float):
    """Track proxy request metrics."""
    frontend_proxy_requests_total.labels(
        service=service, endpoint=endpoint, status=status_code
    ).inc()
    frontend_proxy_request_duration_seconds.labels(
        service=service, endpoint=endpoint
    ).observe(duration)


def track_proxy_error(service: str, error_type: str):
    """Track proxy errors."""
    frontend_proxy_errors_total.labels(service=service, error_type=error_type).inc()


def track_search_query(authenticated: bool):
    """Track search queries."""
    auth_str = "true" if authenticated else "false"
    frontend_search_queries_total.labels(authenticated=auth_str).inc()


def track_watchlist_operation(operation: str, success: bool):
    """Track watchlist operations."""
    status = "success" if success else "failure"
    frontend_watchlist_operations_total.labels(operation=operation, status=status).inc()


def track_static_file(file_type: str, status_code: int):
    """Track static file requests."""
    frontend_static_file_requests_total.labels(
        file_type=file_type, status=status_code
    ).inc()


def update_active_sessions(count: int):
    """Update active sessions gauge."""
    frontend_active_sessions.set(count)


async def metrics_endpoint():
    """
    Prometheus metrics endpoint.

    Returns:
        Response with Prometheus metrics in text format
    """
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
