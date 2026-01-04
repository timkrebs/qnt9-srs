"""
Custom exceptions for the search service domain.

These exceptions represent domain-level errors and are independent
of infrastructure concerns (HTTP, database, etc.).
"""

from typing import Any, Optional


class SearchServiceException(Exception):
    """Base exception for all search service errors."""

    def __init__(self, message: str, details: Optional[dict] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class InvalidIdentifierException(SearchServiceException):
    """Raised when a stock identifier is invalid or malformed."""

    def __init__(self, identifier: str, identifier_type: Optional[str] = None):
        message = f"Invalid identifier: {identifier}"
        if identifier_type:
            message = f"Invalid {identifier_type}: {identifier}"
        super().__init__(
            message=message, details={"identifier": identifier, "type": identifier_type}
        )


class StockNotFoundException(SearchServiceException):
    """Raised when a stock cannot be found in any data source."""

    def __init__(self, query: str, query_type: Optional[str] = None):
        message = f"Stock not found: {query}"
        if query_type:
            message = f"Stock not found for {query_type}: {query}"
        super().__init__(
            message=message, details={"query": query, "query_type": query_type}
        )


class ExternalServiceException(SearchServiceException):
    """Raised when an external API service fails."""

    def __init__(self, service: str, reason: Optional[str] = None):
        message = f"External service '{service}' unavailable"
        if reason:
            message += f": {reason}"
        super().__init__(
            message=message, details={"service": service, "reason": reason}
        )


class RateLimitExceededException(SearchServiceException):
    """Raised when rate limit is exceeded."""

    def __init__(
        self, limit: int, window_seconds: int, retry_after: Optional[int] = None
    ):
        message = f"Rate limit exceeded: {limit} requests per {window_seconds} seconds"
        if retry_after:
            message += f". Retry after {retry_after} seconds"
        super().__init__(
            message=message,
            details={
                "limit": limit,
                "window_seconds": window_seconds,
                "retry_after": retry_after,
            },
        )


class CacheException(SearchServiceException):
    """Raised when cache operations fail."""

    def __init__(self, operation: str, reason: Optional[str] = None):
        message = f"Cache {operation} failed"
        if reason:
            message += f": {reason}"
        super().__init__(
            message=message, details={"operation": operation, "reason": reason}
        )


class ValidationException(SearchServiceException):
    """Raised when input validation fails."""

    def __init__(self, field: str, value: Any, reason: str):
        message = f"Validation failed for {field}: {reason}"
        super().__init__(
            message=message,
            details={"field": field, "value": str(value), "reason": reason},
        )


class DataIntegrityException(SearchServiceException):
    """Raised when data integrity constraints are violated."""

    def __init__(self, entity: str, reason: str):
        message = f"Data integrity error for {entity}: {reason}"
        super().__init__(message=message, details={"entity": entity, "reason": reason})


class CircuitBreakerOpenException(SearchServiceException):
    """Raised when circuit breaker is open (too many failures)."""

    def __init__(
        self, service: str, failure_count: int, retry_after: Optional[int] = None
    ):
        message = f"Circuit breaker open for '{service}' after {failure_count} failures"
        if retry_after:
            message += f". Retry after {retry_after} seconds"
        super().__init__(
            message=message,
            details={
                "service": service,
                "failure_count": failure_count,
                "retry_after": retry_after,
            },
        )
