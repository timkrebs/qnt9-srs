"""
Logging configuration module for frontend service.

Provides centralized logging setup with consistent formatting across the application.
Implements structured logging with request tracing capabilities for distributed systems.
"""

import json
import logging
import sys
from contextvars import ContextVar
from typing import Any, Dict, Optional
from uuid import uuid4

# Context variable for request ID tracking across async calls
request_id_context: ContextVar[Optional[str]] = ContextVar("request_id", default=None)


class StructuredFormatter(logging.Formatter):
    """
    Custom log formatter that outputs structured JSON logs.

    Includes request ID from context for distributed tracing and provides
    machine-readable log output for log aggregation systems.
    """

    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON with structured fields.

        Args:
            record: Log record to format

        Returns:
            JSON-formatted log string
        """
        request_id = request_id_context.get()

        log_data: Dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        if request_id:
            log_data["request_id"] = request_id

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)

        return json.dumps(log_data)


class HumanReadableFormatter(logging.Formatter):
    """
    Human-readable log formatter for development environments.

    Provides colored output and enhanced readability while maintaining
    structured information.
    """

    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
        "RESET": "\033[0m",
    }

    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record with colors and request ID.

        Args:
            record: Log record to format

        Returns:
            Formatted log string with colors
        """
        request_id = request_id_context.get()
        color = self.COLORS.get(record.levelname, self.COLORS["RESET"])
        reset = self.COLORS["RESET"]

        log_parts = [
            f"{color}{record.levelname:8}{reset}",
            f"[{record.name}]",
        ]

        if request_id:
            log_parts.append(f"[req:{request_id[:8]}]")

        log_parts.extend(
            [
                f"[{record.filename}:{record.lineno}]",
                record.getMessage(),
            ]
        )

        message = " ".join(log_parts)

        if record.exc_info:
            message += f"\n{self.formatException(record.exc_info)}"

        return message


def setup_logging(
    log_level: str = "INFO",
    service_name: str = "frontend-service",
    use_json: bool = False,
) -> logging.Logger:
    """
    Configure application logging with structured format.

    Sets up logging with consistent formatting across the application.
    Supports both JSON structured logging for production and human-readable
    format for development.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        service_name: Name of the service for log identification
        use_json: Use JSON structured logging instead of human-readable format

    Returns:
        Configured logger instance
    """
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    formatter: logging.Formatter
    if use_json:
        formatter = StructuredFormatter(datefmt="%Y-%m-%d %H:%M:%S")
    else:
        formatter = HumanReadableFormatter(datefmt="%Y-%m-%d %H:%M:%S")

    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    root_logger.handlers.clear()

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Reduce noise from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

    logger = logging.getLogger(service_name)
    logger.setLevel(numeric_level)

    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Get a logger instance for a specific module.

    Args:
        name: Name for the logger (typically __name__ of the module)

    Returns:
        Logger instance
    """
    return logging.getLogger(name or "frontend-service")


def set_request_id(request_id: Optional[str] = None) -> str:
    """
    Set request ID in context for distributed tracing.

    Args:
        request_id: Request ID to set, generates new UUID if None

    Returns:
        The request ID that was set
    """
    if request_id is None:
        request_id = str(uuid4())
    request_id_context.set(request_id)
    return request_id


def get_request_id() -> Optional[str]:
    """
    Get current request ID from context.

    Returns:
        Current request ID or None if not set
    """
    return request_id_context.get()


def clear_request_id() -> None:
    """Clear request ID from context."""
    request_id_context.set(None)
