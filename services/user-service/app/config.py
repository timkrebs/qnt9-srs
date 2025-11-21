"""
Configuration management for User Service.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # Service Configuration
    SERVICE_NAME: str = "user-service"
    SERVICE_HOST: str = "0.0.0.0"
    SERVICE_PORT: int = 8011
    LOG_LEVEL: str = "INFO"

    # Database Configuration
    DATABASE_URL: str = (
        "postgresql://postgres:postgres@localhost:5432/qnt9_search"  # Fallback for local dev
    )
    SUPABASE_DB_URL: str = ""  # Primary database URL from Supabase
    DATABASE_POOL_SIZE: int = 20
    DATABASE_POOL_MIN_SIZE: int = 5

    # Supabase Configuration
    SUPABASE_URL: str = "http://localhost:54321"
    SUPABASE_ANON_KEY: str = "stub-key"

    # Stripe Configuration
    STRIPE_API_KEY: str = "sk_test_stub"
    STRIPE_WEBHOOK_SECRET: str = "whsec_stub"

    class Config:
        """Pydantic config."""

        env_file = ".env"
        case_sensitive = True


settings = Settings()
