"""
Database configuration and connection management for search service.

This module implements a fallback pattern for database configuration:
1. Supabase PostgreSQL (free tier production)
2. Vault KV secrets (production)
3. Environment variables
4. Local SQLite (development fallback)

The module provides database session management and initialization functionality.
"""

import logging
import os
from pathlib import Path
from typing import Generator

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool

from .models import Base
from .supabase_config import get_supabase_connection_string

# Load environment variables from .env file
# Search for .env in current directory and parent directories
env_path = Path(__file__).parent.parent / ".env"
if not env_path.exists():
    # Try repository root
    env_path = Path(__file__).parent.parent.parent.parent / ".env"

if env_path.exists():
    load_dotenv(dotenv_path=env_path)
    logger = logging.getLogger(__name__)
    logger.info(f"Loaded environment variables from: {env_path}")
else:
    logger = logging.getLogger(__name__)
    logger.warning("No .env file found, using system environment variables")

logger = logging.getLogger(__name__)

# Database configuration constants
DEFAULT_SQLITE_URL = "sqlite:///./search_service.db"
DEFAULT_LOCAL_POSTGRES_URL = "postgresql://srs_admin:local_dev_password@localhost:5432/srs_db"
POSTGRES_CONNECTION_TIMEOUT = 10
POOL_SIZE = 5
MAX_OVERFLOW = 10
POOL_RECYCLE_SECONDS = 3600


def _get_database_url() -> str:
    """
    Get database connection URL using fallback strategy.

    Strategy:
    1. Check USE_LOCAL_DB environment variable for local development
    2. Try to get Supabase PostgreSQL connection (free tier)
    3. Try to get credentials from Vault KV
    4. Fall back to DATABASE_URL environment variable
    5. Default to SQLite for local development

    Returns:
        Database connection URL string
    """
    use_local_db = os.getenv("USE_LOCAL_DB", "false").lower() == "true"

    if use_local_db:
        logger.info("LOCAL DEVELOPMENT MODE - Using local database")
        db_url = os.getenv("DATABASE_URL", DEFAULT_LOCAL_POSTGRES_URL)
        logger.info(f"Using local database: {_sanitize_db_url(db_url)}")
        return db_url

    try:
        logger.debug("Attempting to get Supabase connection string...")
        supabase_url = get_supabase_connection_string()
        if supabase_url:
            logger.info("Using Supabase PostgreSQL database (free tier)")
            return supabase_url
        else:
            logger.debug("Supabase connection string not available, trying Vault...")
    except Exception as supabase_error:
        logger.warning(f"Supabase configuration failed: {supabase_error}")

    # Try to get connection string from Vault, fallback to environment variables
    try:
        logger.debug("Attempting to import Vault KV module...")
        from .vault_kv import get_db_connection_string

        logger.debug("Vault KV module imported successfully")
        try:
            logger.debug("Calling get_db_connection_string()...")
            db_url = get_db_connection_string()
            logger.info("Using database credentials from Vault")
            return db_url
        except Exception as vault_error:
            logger.warning(f"Could not read from Vault KV: {vault_error}")
            logger.info("Falling back to environment variables...")
            db_url = os.getenv("DATABASE_URL", DEFAULT_SQLITE_URL)
            logger.info(f"Using database URL: {_sanitize_db_url(db_url)}")
            return db_url
    except ImportError as e:
        logger.warning(f"Vault module not available: {e}")
        db_url = os.getenv("DATABASE_URL", DEFAULT_SQLITE_URL)
        logger.info(f"Using database URL: {_sanitize_db_url(db_url)}")
        return db_url


def _sanitize_db_url(db_url: str) -> str:
    """
    Remove sensitive information from database URL for logging.

    Args:
        db_url: Database connection URL

    Returns:
        Sanitized URL with password removed
    """
    if "@" in db_url:
        return db_url.split("@")[0] + "@..."
    return db_url


def _get_connect_args(db_url: str) -> dict:
    """
    Get database-specific connection arguments.

    Args:
        db_url: Database connection URL

    Returns:
        Dictionary of connection arguments
    """
    if db_url.startswith("postgresql"):
        return {"connect_timeout": POSTGRES_CONNECTION_TIMEOUT}
    elif db_url.startswith("sqlite"):
        return {"check_same_thread": False}
    return {}


# Get database URL using fallback strategy
db_url = _get_database_url()
connect_args = _get_connect_args(db_url)

# Create engine with connection pooling
logger.debug("Creating SQLAlchemy engine...")
engine = create_engine(
    db_url,
    connect_args=connect_args,
    pool_pre_ping=True,
    pool_recycle=POOL_RECYCLE_SECONDS,
    poolclass=QueuePool,
    pool_size=POOL_SIZE,
    max_overflow=MAX_OVERFLOW,
    echo=False,
)
logger.debug("SQLAlchemy engine created successfully")

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """
    Initialize database tables.

    Creates all tables defined in the Base metadata.
    Should be called on application startup.

    Raises:
        Exception: If database initialization fails
    """
    try:
        logger.info("Initializing database tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


def get_db() -> Generator[Session, None, None]:
    """
    Dependency function for FastAPI to get database session.

    Creates a new database session for each request and ensures
    proper cleanup after the request completes.

    Yields:
        Database session

    Example:
        @app.get("/endpoint")
        def endpoint(db: Session = Depends(get_db)):
            # Use db session here
            pass
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
