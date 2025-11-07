"""
Logging configuration for auth service.

Provides structured logging with different levels and formatters.
"""

import logging
import sys


def setup_logging(
    log_level: str = "INFO",
    service_name: str = "auth-service",
) -> None:
    """
    Configure logging for the application.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        service_name: Name of the service for log identification
    """
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=f"%(asctime)s - {service_name} - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for the given name.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)
