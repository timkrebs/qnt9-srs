"""
Configuration for frontend service
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""

    # Service URLs
    SEARCH_SERVICE_URL: str = "http://localhost:8000"
    AUTH_SERVICE_URL: str = "http://localhost:8002"

    # Application config
    APP_NAME: str = "QNT9 Stock Search"
    DEBUG: bool = True

    # Server config
    HOST: str = "0.0.0.0"
    PORT: int = 8080

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
