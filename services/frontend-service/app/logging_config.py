"""
Logging configuration module for frontend service.

Provides centralized logging setup with consistent formatting across the application.
"""

import logging
import sys
from typing import Optional


def setup_logging(
    log_level: str = "INFO",
    service_name: str = "frontend-service",
) -> logging.Logger:
    """
    Configure application logging with structured format.

    Sets up logging with consistent formatting across the application.
    Logs are output to stdout with timestamps and structured fields.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        service_name: Name of the service for log identification

    Returns:
        Configured logger instance

    Example:
        >>> logger = setup_logging("INFO", "frontend-service")
        >>> logger.info("Application started")
    """
    # Convert string to logging level
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Create formatter with structured output
    log_format = (
        "%(asctime)s - %(name)s - %(levelname)s - "
        "[%(filename)s:%(lineno)d] - %(message)s"
    )
    formatter = logging.Formatter(
        log_format,
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Remove existing handlers
    root_logger.handlers.clear()

    # Add console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Create service-specific logger
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

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.debug("Debugging information")
    """
    return logging.getLogger(name or "frontend-service")
