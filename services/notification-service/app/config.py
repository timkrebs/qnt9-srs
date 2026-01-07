from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    SERVICE_NAME: str = "notification-service"
    SERVICE_HOST: str = "0.0.0.0"
    SERVICE_PORT: int = 8040

    DATABASE_URL: str
    SUPABASE_URL: str
    SUPABASE_JWT_SECRET: str

    RESEND_API_KEY: str
    RESEND_FROM_EMAIL: str = "noreply@qnt9.com"
    RESEND_FROM_NAME: str = "QNT9 Stock Research"

    SEARCH_SERVICE_URL: str = "http://localhost:8020"

    NOTIFICATION_CHECK_INTERVAL: int = 3600
    PRICE_ALERT_SEND_HOUR: int = 8
    ALERT_COOLDOWN_HOURS: int = 24

    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
