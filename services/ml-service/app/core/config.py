from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    SERVICE_NAME: str = "ml-service"
    LOG_LEVEL: str = "INFO"
    
    # Database (Supabase Postgres)
    DATABASE_URL: str

    # Supabase Storage (Model Artifacts)
    SUPABASE_URL: str
    SUPABASE_KEY: str  # Service Role Key preferred for backend
    SUPABASE_BUCKET_MODELS: str = "qnt9-models"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

settings = Settings()
