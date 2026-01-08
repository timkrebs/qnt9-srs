"""Configuration management for Notification Service."""

import sys
from typing import List, Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Service Configuration
    SERVICE_NAME: str = "notification-service"
    SERVICE_HOST: str = "0.0.0.0"
    SERVICE_PORT: int = 8040
    DEBUG: bool = False

    # Database Configuration
    DATABASE_URL: str
    SUPABASE_URL: str
    SUPABASE_JWT_SECRET: Optional[str] = None
    JWT_SECRET_KEY: str  # Used for validating auth-service JWTs
    JWT_ALGORITHM: str = "HS256"

    # Email Configuration (Resend)
    RESEND_API_KEY: str
    RESEND_FROM_EMAIL: str = "noreply@finio.cloud"
    RESEND_FROM_NAME: str = "Finio Stock Research"

    # CORS Configuration
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8080"

    @field_validator("RESEND_API_KEY")
    @classmethod
    def validate_resend_api_key(cls, v: str) -> str:
        """Validate Resend API key is production-ready."""
        if not v or v.strip() == "":
            raise ValueError("RESEND_API_KEY is required")
        if v.startswith("re_") is False:
            print(
                "WARNING: RESEND_API_KEY does not appear to be a valid Resend key",
                file=sys.stderr,
            )
        return v

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins string into list."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    SEARCH_SERVICE_URL: str = "http://localhost:8020"

    NOTIFICATION_CHECK_INTERVAL: int = 3600
    PRICE_ALERT_SEND_HOUR: int = 8
    DAILY_SUMMARY_SEND_HOUR: int = 7
    ALERT_COOLDOWN_HOURS: int = 24

    REDIS_URL: Optional[str] = None
    NEWS_CACHE_TTL_SECONDS: int = 3600
    API_REQUEST_DELAY_MS: int = 100

    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
