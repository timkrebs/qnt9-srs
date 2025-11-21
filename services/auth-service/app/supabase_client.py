"""
Supabase client configuration for authentication service.

Provides a configured Supabase client for authentication operations.
"""

from typing import Optional

from supabase import Client, create_client

from .config import settings
from .logging_config import get_logger

logger = get_logger(__name__)


class SupabaseConfig:
    """
    Supabase configuration class.

    Loads Supabase URL and key from settings.
    """

    def __init__(self) -> None:
        """Initialize Supabase configuration from settings."""
        self.url: str = settings.SUPABASE_URL
        self.key: str = settings.SUPABASE_SERVICE_KEY
        self.anon_key: str = settings.SUPABASE_ANON_KEY

        if not self.url or not self.key:
            logger.warning("Supabase credentials not fully configured")
            logger.debug(f"SUPABASE_URL: {'set' if self.url else 'not set'}")
            logger.debug(f"SUPABASE_SERVICE_KEY: {'set' if self.key else 'not set'}")

    @property
    def is_configured(self) -> bool:
        """Check if Supabase is properly configured."""
        return bool(self.url and self.key)


# Global configuration instance
config = SupabaseConfig()

# Global Supabase client instance
_supabase_client: Optional[Client] = None


def get_supabase_client() -> Client:
    """
    Get or create Supabase client instance.

    Returns:
        Configured Supabase client

    Raises:
        ValueError: If Supabase is not properly configured
    """
    global _supabase_client

    if not config.is_configured:
        raise ValueError("Supabase not configured. Set SUPABASE_URL and SUPABASE_SERVICE_KEY")

    if _supabase_client is None:
        logger.info("Initializing Supabase client...")
        _supabase_client = create_client(config.url, config.key)
        logger.info("Supabase client initialized successfully")

    return _supabase_client


def get_supabase_admin_client() -> Client:
    """
    Get Supabase admin client with service role key.

    Use this for admin operations that bypass Row Level Security (RLS).

    Returns:
        Supabase client with admin privileges
    """
    return get_supabase_client()
