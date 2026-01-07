from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Service Info
    SERVICE_NAME: str = "data-service"
    LOG_LEVEL: str = "INFO"
    
    # Database (Supabase Postgres)
    DATABASE_URL: str

    # Massive API (Data Source)
    MASSIVE_API_KEY: str
    MASSIVE_USE_REALTIME: bool = False
    MASSIVE_S3_ACCESS_KEY_ID: Optional[str] = None
    MASSIVE_S3_SECRET_ACCESS_KEY: Optional[str] = None  # Often implied or not needed if public
    MASSIVE_S3_ENDPOINT: Optional[str] = None
    MASSIVE_S3_BUCKET: Optional[str] = None

    # Supabase (Storage & Auth)
    SUPABASE_URL: Optional[str] = None
    SUPABASE_KEY: Optional[str] = None
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = None
    SUPABASE_S3_STORAGE_URL: Optional[str] = None
    SEARCH_SERVICE_URL: Optional[str] = "http://search-service:8000"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

settings = Settings()
