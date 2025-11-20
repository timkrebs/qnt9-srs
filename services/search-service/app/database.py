"""
Database configuration and connection management.

Simplified configuration using environment variables for maximum performance.
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

# Load environment variables
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

logger = logging.getLogger(__name__)

# Database configuration
# Default for local development (overridden by DATABASE_URL env var in production/Docker)
DEFAULT_DATABASE_URL = "postgresql://qnt9_user:qnt9_password@localhost:5432/qnt9_search"
POOL_SIZE = 5
MAX_OVERFLOW = 10
POOL_RECYCLE_SECONDS = 3600


def get_database_url() -> str:
    """
    Get database URL from environment.

    Returns:
        Database connection URL
    """
    db_url = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)

    # Sanitize for logging
    if "@" in db_url:
        safe_url = db_url.split("@")[0] + "@..."
    else:
        safe_url = db_url

    logger.info(f"Using database: {safe_url}")
    return db_url


def get_connect_args(db_url: str) -> dict:
    """
    Get database-specific connection arguments.

    Args:
        db_url: Database connection URL

    Returns:
        Connection arguments dict
    """
    if "sqlite" in db_url:
        return {"check_same_thread": False}
    return {}


# Initialize database connection
db_url = get_database_url()
connect_args = get_connect_args(db_url)

# Create engine with connection pooling
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

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """
    Initialize database tables.

    Creates all tables on application startup.
    Uses checkfirst=True to safely handle existing tables.
    """
    try:
        logger.info("Initializing database tables...")
        Base.metadata.create_all(bind=engine, checkfirst=True)
        logger.info("Database initialized successfully")
    except Exception as e:
        error_msg = str(e).lower()
        if "already exists" in error_msg or "duplicate" in error_msg:
            logger.warning("Database objects already exist (expected)")
        else:
            logger.error(f"Failed to initialize database: {e}")
            raise


def get_db() -> Generator[Session, None, None]:
    """
    Get database session for dependency injection.

    Yields:
        SQLAlchemy database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
