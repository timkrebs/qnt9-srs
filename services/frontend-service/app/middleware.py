"""
Middleware components for request handling and logging.

Provides middleware for request tracing, logging, error handling,
and performance monitoring in the frontend service.
"""

import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from .logging_config import clear_request_id, get_logger, set_request_id

logger = get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for comprehensive request and response logging.

    Logs all incoming requests and outgoing responses with detailed
    information including timing, status codes, and request IDs for
    distributed tracing.
    """

    def __init__(self, app: ASGIApp) -> None:
        """
        Initialize request logging middleware.

        Args:
            app: ASGI application instance
        """
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and log details.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware or route handler

        Returns:
            HTTP response
        """
        # Generate or extract request ID
        request_id = request.headers.get("X-Request-ID")
        if not request_id:
            request_id = set_request_id()
        else:
            set_request_id(request_id)

        # Log incoming request
        start_time = time.perf_counter()

        logger.info(
            f"Request started: {request.method} {request.url.path}",
            extra={
                "extra_fields": {
                    "method": request.method,
                    "path": request.url.path,
                    "query_params": str(request.query_params),
                    "client_host": request.client.host if request.client else None,
                    "user_agent": request.headers.get("user-agent"),
                }
            },
        )

        try:
            # Process request
            response = await call_next(request)

            # Calculate request duration
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id

            # Log successful response
            logger.info(
                f"Request completed: {request.method} {request.url.path} "
                f"[{response.status_code}] ({duration_ms:.2f}ms)",
                extra={
                    "extra_fields": {
                        "method": request.method,
                        "path": request.url.path,
                        "status_code": response.status_code,
                        "duration_ms": duration_ms,
                    }
                },
            )

            return response
        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                f"Request failed: {request.method} {request.url.path} ({duration_ms:.2f}ms)",
                extra={"extra_fields": {"error": str(exc)}},
            )
            raise
        finally:
            clear_request_id()


class StaticFileCacheMiddleware(BaseHTTPMiddleware):
    """
    Middleware for adding cache-control headers to static files.

    Improves performance by enabling browser caching for static assets
    like CSS, JavaScript, and images.
    """

    # Cache durations for different file types (in seconds)
    CACHE_DURATIONS = {
        ".css": 86400,  # 1 day
        ".js": 86400,  # 1 day
        ".png": 604800,  # 7 days
        ".jpg": 604800,  # 7 days
        ".jpeg": 604800,  # 7 days
        ".gif": 604800,  # 7 days
        ".ico": 604800,  # 7 days
        ".svg": 604800,  # 7 days
        ".woff": 2592000,  # 30 days
        ".woff2": 2592000,  # 30 days
        ".ttf": 2592000,  # 30 days
    }

    def __init__(self, app: ASGIApp) -> None:
        """
        Initialize static file cache middleware.

        Args:
            app: ASGI application instance
        """
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Add cache headers to static file responses.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware or route handler

        Returns:
            HTTP response with cache headers for static files
        """
        response = await call_next(request)

        # Only process static file requests
        path = request.url.path
        if path.startswith("/static/"):
            # Determine cache duration based on file extension
            for ext, duration in self.CACHE_DURATIONS.items():
                if path.endswith(ext):
                    response.headers["Cache-Control"] = f"public, max-age={duration}"
                    response.headers["Vary"] = "Accept-Encoding"
                    break
            else:
                # Default cache for other static files
                response.headers["Cache-Control"] = "public, max-age=3600"

        return response


class PerformanceMonitoringMiddleware(BaseHTTPMiddleware):
    """
    Middleware for monitoring request performance.

    Tracks slow requests and logs warnings for requests exceeding
    performance thresholds.
    """

    def __init__(
        self,
        app: ASGIApp,
        slow_request_threshold_ms: float = 1000.0,
    ) -> None:
        """
        Initialize performance monitoring middleware.

        Args:
            app: ASGI application instance
            slow_request_threshold_ms: Threshold in milliseconds for slow requests
        """
        super().__init__(app)
        self.slow_request_threshold_ms = slow_request_threshold_ms

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Monitor request performance.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware or route handler

        Returns:
            HTTP response
        """
        start_time = time.perf_counter()

        response = await call_next(request)

        duration_ms = (time.perf_counter() - start_time) * 1000

        # Log slow requests
        if duration_ms > self.slow_request_threshold_ms:
            logger.warning(
                f"Slow request detected: {request.method} {request.url.path} "
                f"took {duration_ms:.2f}ms (threshold: {self.slow_request_threshold_ms}ms)",
                extra={
                    "extra_fields": {
                        "method": request.method,
                        "path": request.url.path,
                        "duration_ms": duration_ms,
                        "threshold_ms": self.slow_request_threshold_ms,
                    }
                },
            )

        return response
