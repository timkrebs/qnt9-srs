"""
Security middleware and configuration.

Implements CORS, security headers, request validation, and sanitization
for production deployment.
"""

import logging
import re
from typing import Callable

from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class SecurityConfig:
    """Security configuration constants."""

    MAX_REQUEST_SIZE_BYTES = 1_000_000
    MAX_QUERY_LENGTH = 500
    MAX_RESULTS_LIMIT = 100

    ALLOWED_CHARS_PATTERN = re.compile(r"^[a-zA-Z0-9\s\-_.&()]+$")

    SQL_INJECTION_PATTERNS = [
        r"(\bUNION\b.*\bSELECT\b)",
        r"(\bDROP\b.*\bTABLE\b)",
        r"(\bINSERT\b.*\bINTO\b)",
        r"(\bUPDATE\b.*\bSET\b)",
        r"(\bDELETE\b.*\bFROM\b)",
        r"(--)",
        r"(;.*--)",
        r"(\bEXEC\b)",
        r"(\bEXECUTE\b)",
    ]

    XSS_PATTERNS = [
        r"<script[^>]*>.*</script>",
        r"javascript:",
        r"onerror\s*=",
        r"onload\s*=",
    ]


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Add security headers to all responses.

    Implements OWASP recommended security headers for API protection.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and add security headers to response.

        Args:
            request: Incoming request
            call_next: Next middleware in chain

        Returns:
            Response with security headers
        """
        response = await call_next(request)

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none'"
        )
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=()"
        )

        return response


class RequestValidationMiddleware(BaseHTTPMiddleware):
    """
    Validate and sanitize incoming requests.

    Protects against oversized requests, SQL injection, XSS, and other attacks.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Validate request before processing.

        Args:
            request: Incoming request
            call_next: Next middleware in chain

        Returns:
            Response or error if validation fails
        """
        content_length = request.headers.get("content-length")
        if (
            content_length
            and int(content_length) > SecurityConfig.MAX_REQUEST_SIZE_BYTES
        ):
            logger.warning(
                "Request too large: %s bytes from %s",
                content_length,
                request.client.host if request.client else "unknown",
            )
            return JSONResponse(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                content={
                    "error": "request_too_large",
                    "message": "Request exceeds maximum allowed size",
                    "max_size_bytes": SecurityConfig.MAX_REQUEST_SIZE_BYTES,
                },
            )

        query_params = dict(request.query_params)

        if "q" in query_params or "query" in query_params:
            query_value = query_params.get("q") or query_params.get("query")

            if len(query_value) > SecurityConfig.MAX_QUERY_LENGTH:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={
                        "error": "query_too_long",
                        "message": "Search query exceeds maximum length",
                        "max_length": SecurityConfig.MAX_QUERY_LENGTH,
                    },
                )

            if not self._is_safe_query(query_value):
                logger.warning(
                    "Potentially malicious query detected: %s from %s",
                    query_value[:50],
                    request.client.host if request.client else "unknown",
                )
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={
                        "error": "invalid_query",
                        "message": "Query contains invalid or potentially harmful characters",
                    },
                )

        if "limit" in query_params:
            try:
                limit = int(query_params["limit"])
                if limit > SecurityConfig.MAX_RESULTS_LIMIT:
                    return JSONResponse(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        content={
                            "error": "limit_too_high",
                            "message": f"Limit exceeds maximum of {SecurityConfig.MAX_RESULTS_LIMIT}",
                        },
                    )
            except ValueError:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={
                        "error": "invalid_limit",
                        "message": "Limit must be a valid integer",
                    },
                )

        response = await call_next(request)
        return response

    def _is_safe_query(self, query: str) -> bool:
        """
        Check if query is safe from injection attacks.

        Args:
            query: Search query string

        Returns:
            True if safe, False if potentially malicious
        """
        query_upper = query.upper()

        for pattern in SecurityConfig.SQL_INJECTION_PATTERNS:
            if re.search(pattern, query_upper, re.IGNORECASE):
                logger.warning("SQL injection pattern detected: %s", pattern)
                return False

        for pattern in SecurityConfig.XSS_PATTERNS:
            if re.search(pattern, query, re.IGNORECASE):
                logger.warning("XSS pattern detected: %s", pattern)
                return False

        return True


def configure_cors(app: FastAPI) -> None:
    """
    Configure CORS middleware for production.

    Args:
        app: FastAPI application instance
    """
    import os

    allowed_origins_str = os.getenv(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:3000,http://localhost:8000",
    )

    allowed_origins = [
        origin.strip() for origin in allowed_origins_str.split(",") if origin.strip()
    ]

    logger.info("Configuring CORS with origins: %s", allowed_origins)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "X-Request-ID",
            "X-API-Key",
        ],
        expose_headers=[
            "X-Request-ID",
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset",
        ],
        max_age=3600,
    )


def configure_security_middleware(app: FastAPI) -> None:
    """
    Configure all security middleware.

    Args:
        app: FastAPI application instance
    """
    configure_cors(app)

    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestValidationMiddleware)

    logger.info("Security middleware configured")


def sanitize_input(value: str, max_length: int = 200) -> str:
    """
    Sanitize user input string.

    Args:
        value: Input string to sanitize
        max_length: Maximum allowed length

    Returns:
        Sanitized string
    """
    if not value:
        return ""

    sanitized = value.strip()[:max_length]

    sanitized = re.sub(r"[<>\"']", "", sanitized)

    sanitized = re.sub(r"\s+", " ", sanitized)

    return sanitized


def validate_symbol(symbol: str) -> bool:
    """
    Validate stock symbol format.

    Args:
        symbol: Stock symbol to validate

    Returns:
        True if valid, False otherwise
    """
    if not symbol or len(symbol) > 10:
        return False

    return bool(re.match(r"^[A-Z0-9.-]+$", symbol.upper()))


def validate_isin(isin: str) -> bool:
    """
    Validate ISIN format.

    Args:
        isin: ISIN to validate

    Returns:
        True if valid format, False otherwise
    """
    if not isin or len(isin) != 12:
        return False

    return bool(re.match(r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$", isin.upper()))


def validate_wkn(wkn: str) -> bool:
    """
    Validate WKN format.

    Args:
        wkn: WKN to validate

    Returns:
        True if valid format, False otherwise
    """
    if not wkn or len(wkn) != 6:
        return False

    return bool(re.match(r"^[A-Z0-9]{6}$", wkn.upper()))
