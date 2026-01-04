"""
Prometheus metrics for Auth Service.

Tracks authentication operations, token generation, and request performance.
"""

from fastapi import Response
from prometheus_client import (CONTENT_TYPE_LATEST, Counter, Gauge, Histogram,
                               generate_latest)

# Request metrics
http_requests_total = Counter(
    "auth_http_requests_total", "Total HTTP requests", ["method", "endpoint", "status"]
)

http_request_duration_seconds = Histogram(
    "auth_http_request_duration_seconds",
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

# Authentication metrics
auth_signup_total = Counter("auth_signup_total", "Total user signups", ["status"])

auth_signin_total = Counter("auth_signin_total", "Total user sign-ins", ["status"])

auth_token_refresh_total = Counter(
    "auth_token_refresh_total", "Total token refresh requests", ["status"]
)

auth_password_reset_total = Counter(
    "auth_password_reset_total", "Total password reset requests", ["status"]
)

# Rate limiting metrics
auth_rate_limit_hits = Counter(
    "auth_rate_limit_hits_total", "Total rate limit hits", ["endpoint"]
)

# Active users gauge
auth_active_sessions = Gauge("auth_active_sessions", "Number of active user sessions")

# Database metrics
auth_db_operations_total = Counter(
    "auth_db_operations_total", "Total database operations", ["operation", "status"]
)

auth_db_operation_duration_seconds = Histogram(
    "auth_db_operation_duration_seconds",
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


def track_signup(success: bool):
    """Track signup metrics."""
    status = "success" if success else "failure"
    auth_signup_total.labels(status=status).inc()


def track_signin(success: bool):
    """Track sign-in metrics."""
    status = "success" if success else "failure"
    auth_signin_total.labels(status=status).inc()


def track_token_refresh(success: bool):
    """Track token refresh metrics."""
    status = "success" if success else "failure"
    auth_token_refresh_total.labels(status=status).inc()


def track_password_reset(success: bool):
    """Track password reset metrics."""
    status = "success" if success else "failure"
    auth_password_reset_total.labels(status=status).inc()


def track_rate_limit_hit(endpoint: str):
    """Track rate limit hits."""
    auth_rate_limit_hits.labels(endpoint=endpoint).inc()


def track_db_operation(operation: str, success: bool, duration: float):
    """Track database operation metrics."""
    status = "success" if success else "failure"
    auth_db_operations_total.labels(operation=operation, status=status).inc()
    auth_db_operation_duration_seconds.labels(operation=operation).observe(duration)


async def metrics_endpoint():
    """
    Prometheus metrics endpoint.

    Returns:
        Response with Prometheus metrics in text format
    """
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
