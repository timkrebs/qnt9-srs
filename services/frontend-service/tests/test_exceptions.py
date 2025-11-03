"""
Tests for custom exception classes.

Tests all custom exception types to ensure proper initialization
and error message formatting.
"""


from app.exceptions import (
    FrontendServiceException,
    SearchTimeoutException,
    ServiceUnavailableException,
    ValidationException,
)


def test_frontend_service_exception_basic() -> None:
    """
    Test basic FrontendServiceException initialization.

    Verifies that the base exception can be created with just a message.
    """
    exc = FrontendServiceException("Test error")

    assert exc.message == "Test error"
    assert exc.details == {}
    assert str(exc) == "Test error"


def test_frontend_service_exception_with_details() -> None:
    """
    Test FrontendServiceException with details.

    Verifies that additional context can be attached to the exception.
    """
    details = {"code": "ERR001", "context": "test_context"}
    exc = FrontendServiceException("Test error", details=details)

    assert exc.message == "Test error"
    assert exc.details == details
    assert exc.details["code"] == "ERR001"
    assert exc.details["context"] == "test_context"


def test_service_unavailable_exception_default_message() -> None:
    """
    Test ServiceUnavailableException with default message.

    Verifies that a default message is generated from the service name.
    """
    exc = ServiceUnavailableException("search-service")

    assert exc.service_name == "search-service"
    assert exc.message == "Service 'search-service' is currently unavailable"
    assert exc.details == {}


def test_service_unavailable_exception_custom_message() -> None:
    """
    Test ServiceUnavailableException with custom message.

    Verifies that a custom message can override the default.
    """
    custom_msg = "Backend is down for maintenance"
    exc = ServiceUnavailableException("search-service", message=custom_msg)

    assert exc.service_name == "search-service"
    assert exc.message == custom_msg


def test_service_unavailable_exception_with_details() -> None:
    """
    Test ServiceUnavailableException with details.

    Verifies that additional context can be provided.
    """
    details = {"status_code": 503, "retry_after": 30}
    exc = ServiceUnavailableException(
        "search-service",
        details=details,
    )

    assert exc.service_name == "search-service"
    assert exc.details == details
    assert exc.details["status_code"] == 503


def test_search_timeout_exception() -> None:
    """
    Test SearchTimeoutException initialization.

    Verifies that timeout exceptions include query and timeout information.
    """
    exc = SearchTimeoutException("AAPL", 5.0)

    assert exc.query == "AAPL"
    assert exc.timeout_seconds == 5.0
    assert "timed out" in exc.message.lower()
    assert "AAPL" in exc.message
    assert "5.0s" in exc.message


def test_search_timeout_exception_with_details() -> None:
    """
    Test SearchTimeoutException with additional details.

    Verifies that context can be attached to timeout exceptions.
    """
    details = {"attempt": 3, "last_error": "Connection refused"}
    exc = SearchTimeoutException("DE0005140008", 10.0, details=details)

    assert exc.query == "DE0005140008"
    assert exc.timeout_seconds == 10.0
    assert exc.details["attempt"] == 3
    assert exc.details["last_error"] == "Connection refused"


def test_validation_exception() -> None:
    """
    Test ValidationException initialization.

    Verifies that validation errors include field, value, and reason.
    """
    exc = ValidationException(
        field_name="query",
        value="",
        reason="Query cannot be empty",
    )

    assert exc.field_name == "query"
    assert exc.value == ""
    assert exc.reason == "Query cannot be empty"
    assert "query" in exc.message.lower()
    assert "Query cannot be empty" in exc.message


def test_validation_exception_with_details() -> None:
    """
    Test ValidationException with additional details.

    Verifies that validation context can be provided.
    """
    details = {
        "min_length": 1,
        "max_length": 50,
        "actual_length": 0,
    }
    exc = ValidationException(
        field_name="query",
        value="",
        reason="Query is too short",
        details=details,
    )

    assert exc.field_name == "query"
    assert exc.details["min_length"] == 1
    assert exc.details["max_length"] == 50
    assert exc.details["actual_length"] == 0


def test_exception_inheritance() -> None:
    """
    Test that all custom exceptions inherit from base.

    Verifies proper exception hierarchy for consistent error handling.
    """
    service_exc = ServiceUnavailableException("test")
    timeout_exc = SearchTimeoutException("test", 5.0)
    validation_exc = ValidationException("field", "value", "reason")

    assert isinstance(service_exc, FrontendServiceException)
    assert isinstance(timeout_exc, FrontendServiceException)
    assert isinstance(validation_exc, FrontendServiceException)

    assert isinstance(service_exc, Exception)
    assert isinstance(timeout_exc, Exception)
    assert isinstance(validation_exc, Exception)
