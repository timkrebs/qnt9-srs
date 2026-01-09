"""Configuration for Watchlist Service."""

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Watchlist service configuration.

    All settings can be overridden via environment variables.
    """

    # Service configuration
    SERVICE_NAME: str = Field(default="watchlist-service")
    SERVICE_HOST: str = Field(default="0.0.0.0")
    SERVICE_PORT: int = Field(default=8012, ge=1, le=65535)
    DEBUG: bool = Field(default=True)
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO"
    )

    # JWT Authentication
    JWT_SECRET_KEY: str = Field(
        default="your-super-secret-key-change-in-production-min-32-chars"
    )
    JWT_ALGORITHM: str = Field(default="HS256")

    # Supabase Configuration (required for token validation)
    SUPABASE_URL: str = Field(default="")

    # Database
    DATABASE_URL: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/finio"
    )

    # Tier Limits
    FREE_TIER_WATCHLIST_LIMIT: int = Field(default=10, ge=1)
    PAID_TIER_WATCHLIST_LIMIT: int = Field(default=999, ge=1)

    # CORS
    CORS_ORIGINS: str = Field(default="http://localhost:8080,http://localhost:3000")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins string into list."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]


settings = Settings()
