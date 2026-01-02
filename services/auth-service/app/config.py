"""
Configuration management for auth service.

Loads and validates environment variables for the application.
"""

import sys
from typing import List

from pydantic import ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    All settings can be overridden via environment variables.
    """

    # Service Configuration
    APP_NAME: str = "QNT9 Auth Service"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    HOST: str = "0.0.0.0"
    PORT: int = 8010

    # Database Configuration
    DATABASE_URL: str = "postgresql://qnt9:qnt9_secret_password@localhost:5432/qnt9_db"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_POOL_MIN_SIZE: int = 5

    # JWT Configuration
    JWT_SECRET_KEY: str = "your-super-secret-key-change-in-production-min-32-chars"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def validate_jwt_secret(cls, v: str) -> str:
        """Validate JWT secret key is production-ready."""
        if len(v) < 32:
            raise ValueError("JWT_SECRET_KEY must be at least 32 characters long")

        if v == "your-super-secret-key-change-in-production-min-32-chars":
            print(
                "WARNING: Using default JWT_SECRET_KEY. This is insecure for production!",
                file=sys.stderr,
            )
            if not cls.model_fields.get("DEBUG", False):
                raise ValueError(
                    "Default JWT_SECRET_KEY not allowed in production. Set JWT_SECRET_KEY environment variable."
                )

        return v

    # Password Hashing
    PASSWORD_HASH_ROUNDS: int = 12

    # CORS Configuration (comma-separated string)
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8080"

    # Redis Configuration
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_MAX_CONNECTIONS: int = 50
    CACHE_PREFIX: str = "qnt9:auth:cache:"
    CACHE_DEFAULT_TTL: int = 300
    RATE_LIMIT_PREFIX: str = "qnt9:auth:ratelimit:"
    RATE_LIMIT_WINDOW_SECONDS: int = 60
    RATE_LIMIT_MAX_REQUESTS: int = 60

    # Email Configuration
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "noreply@qnt9.com"
    SMTP_FROM_NAME: str = "QNT9 Stock Research"
    EMAIL_VERIFICATION_ENABLED: bool = False
    EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS: int = 24

    # Frontend URL for email links
    FRONTEND_URL: str = "http://localhost:8080"

    # Supabase Configuration
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    SUPABASE_JWT_SECRET: str = ""

    @field_validator("SUPABASE_URL")
    @classmethod
    def validate_supabase_url(cls, v: str) -> str:
        """Validate Supabase URL is provided."""
        if not v:
            raise ValueError(
                "SUPABASE_URL must be set. Get it from your Supabase project settings."
            )
        if not v.startswith("https://"):
            raise ValueError("SUPABASE_URL must start with https://")
        return v

    @field_validator("SUPABASE_KEY")
    @classmethod
    def validate_supabase_key(cls, v: str) -> str:
        """Validate Supabase anon key is provided."""
        if not v:
            raise ValueError(
                "SUPABASE_KEY (anon key) must be set. Get it from your Supabase project settings."
            )
        return v

    @field_validator("SUPABASE_SERVICE_ROLE_KEY")
    @classmethod
    def validate_service_role_key(cls, v: str) -> str:
        """Validate Supabase service role key is provided."""
        if not v:
            raise ValueError(
                "SUPABASE_SERVICE_ROLE_KEY must be set. Get it from your Supabase project settings."
            )
        return v

    @field_validator("SUPABASE_JWT_SECRET")
    @classmethod
    def validate_supabase_jwt_secret(cls, v: str) -> str:
        """Validate Supabase JWT secret is provided."""
        if not v:
            raise ValueError(
                "SUPABASE_JWT_SECRET must be set. Get it from your Supabase project settings."
            )
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    def get_cors_origins(self) -> List[str]:
        """Get CORS origins as a list with validation."""
        origins = [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

        if not origins and not self.DEBUG:
            raise ValueError("CORS_ORIGINS must be configured for production")

        for origin in origins:
            if origin == "*":
                print(
                    "WARNING: CORS configured with wildcard (*). This is insecure!", file=sys.stderr
                )
                if not self.DEBUG:
                    raise ValueError("Wildcard CORS origin not allowed in production")

        return origins


# Global settings instance
try:
    settings = Settings()
except ValidationError as e:
    print(f"Configuration validation failed: {e}", file=sys.stderr)
    sys.exit(1)
