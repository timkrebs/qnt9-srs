"""
Configuration management for auth service.

Loads and validates environment variables for the application.
"""

from typing import List

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

    # Password Hashing
    PASSWORD_HASH_ROUNDS: int = 12

    # CORS Configuration (comma-separated string)
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8080"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    def get_cors_origins(self) -> List[str]:
        """Get CORS origins as a list."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


# Global settings instance
settings = Settings()
