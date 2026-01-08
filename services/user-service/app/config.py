"""Configuration management for User Service."""

import sys
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Service Configuration
    SERVICE_NAME: str = "user-service"
    SERVICE_HOST: str = "0.0.0.0"
    SERVICE_PORT: int = 8011
    LOG_LEVEL: str = "INFO"
    DEBUG: bool = False

    # Database Configuration (PostgreSQL)
    DATABASE_URL: str = (
        "postgresql://postgres:postgres@localhost:5432/finio"
    )
    DATABASE_POOL_SIZE: int = 20
    DATABASE_POOL_MIN_SIZE: int = 5

    # Stripe Configuration
    STRIPE_API_KEY: str = "sk_test_stub"
    STRIPE_WEBHOOK_SECRET: str = "whsec_stub"

    # CORS Configuration
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8080"

    @field_validator("STRIPE_API_KEY")
    @classmethod
    def validate_stripe_api_key(cls, v: str) -> str:
        """Validate Stripe API key format."""
        if v == "sk_test_stub":
            print(
                "WARNING: Using stub STRIPE_API_KEY. Set proper key for production!",
                file=sys.stderr,
            )
        elif not v.startswith(("sk_test_", "sk_live_")):
            print(
                "WARNING: STRIPE_API_KEY does not appear to be a valid Stripe key",
                file=sys.stderr,
            )
        return v

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins string into list."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
