"""
Configuration module for frontend service.

This module provides centralized configuration management using Pydantic settings.
All configuration values can be overridden via environment variables or .env file.
"""

from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings for the frontend service.

    All settings can be configured via environment variables.
    Settings are validated on instantiation to ensure correct configuration.

    Attributes:
        SEARCH_SERVICE_URL: Base URL for the search service API
        AUTH_SERVICE_URL: Base URL for the authentication service API
        APP_NAME: Display name for the application
        DEBUG: Enable debug mode (shows API docs, detailed errors)
        HOST: Server bind address
        PORT: Server port number
        LOG_LEVEL: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        REQUEST_TIMEOUT: Default timeout for HTTP requests in seconds
    """

    # Service URLs
    SEARCH_SERVICE_URL: str = Field(
        default="http://localhost:8000",
        description="Base URL for the search service API",
    )
    AUTH_SERVICE_URL: str = Field(
        default="http://localhost:8002",
        description="Base URL for the authentication service API",
    )

    # Application configuration
    APP_NAME: str = Field(
        default="QNT9 Stock Search",
        description="Display name for the application",
    )
    DEBUG: bool = Field(
        default=True,
        description="Enable debug mode",
    )

    # Server configuration
    HOST: str = Field(
        default="0.0.0.0",
        description="Server bind address",
    )
    PORT: int = Field(
        default=8080,
        ge=1,
        le=65535,
        description="Server port number",
    )

    # Logging configuration
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging level",
    )

    # HTTP client configuration
    REQUEST_TIMEOUT: float = Field(
        default=10.0,  # Increased from 2.0 to support company name search (4-5s response time)
        gt=0,
        le=30.0,
        description="Default timeout for HTTP requests in seconds",
    )

    @field_validator("SEARCH_SERVICE_URL", "AUTH_SERVICE_URL")
    @classmethod
    def validate_url(cls, value: str) -> str:
        """
        Validate that service URLs are properly formatted.

        Args:
            value: The URL to validate

        Returns:
            The validated URL without trailing slash

        Raises:
            ValueError: If URL is invalid
        """
        if not value:
            raise ValueError("Service URL cannot be empty")

        value = value.rstrip("/")

        if not (value.startswith("http://") or value.startswith("https://")):
            raise ValueError(
                f"Service URL must start with http:// or https://, got: {value}"
            )

        return value

    model_config = {
        "env_file": ".env",
        "case_sensitive": True,
        "extra": "ignore",
    }


# Global settings instance
settings = Settings()
