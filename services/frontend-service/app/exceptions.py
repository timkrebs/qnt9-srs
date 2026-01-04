"""
Custom exception classes for frontend service.

Provides specific exceptions for different error scenarios
to improve error handling and debugging.
"""

from typing import Any, Dict, Optional


class FrontendServiceException(Exception):
    """
    Base exception for all frontend service errors.

    All custom exceptions should inherit from this class
    for consistent error handling.
    """

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Initialize frontend service exception.

        Args:
            message: Human-readable error message
            details: Additional context about the error
        """
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class ServiceUnavailableException(FrontendServiceException):
    """
    Exception raised when a backend service is unavailable.

    Used when search-service or other dependencies cannot be reached.
    """

    def __init__(
        self,
        service_name: str,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Initialize service unavailable exception.

        Args:
            service_name: Name of the unavailable service
            message: Optional custom error message
            details: Additional context about the error
        """
        self.service_name = service_name
        default_message = f"Service '{service_name}' is currently unavailable"
        super().__init__(message or default_message, details)


class SearchTimeoutException(FrontendServiceException):
    """
    Exception raised when a search request times out.

    Used when the search operation exceeds the configured timeout.
    """

    def __init__(
        self,
        query: str,
        timeout_seconds: float,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Initialize search timeout exception.

        Args:
            query: The search query that timed out
            timeout_seconds: The timeout value that was exceeded
            details: Additional context about the error
        """
        self.query = query
        self.timeout_seconds = timeout_seconds
        message = (
            f"Search request timed out after {timeout_seconds}s for query: {query}"
        )
        super().__init__(message, details)


class ValidationException(FrontendServiceException):
    """
    Exception raised when input validation fails.

    Used for invalid search queries or malformed requests.
    """

    def __init__(
        self,
        field_name: str,
        value: Any,
        reason: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Initialize validation exception.

        Args:
            field_name: Name of the field that failed validation
            value: The invalid value
            reason: Explanation of why validation failed
            details: Additional context about the error
        """
        self.field_name = field_name
        self.value = value
        self.reason = reason
        message = f"Validation failed for '{field_name}': {reason}"
        super().__init__(message, details)
