"""
Database configuration and connection management for search service
Implements Vault → Environment Variable → SQLite fallback pattern
"""

import logging
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

from .models import Base

logger = logging.getLogger(__name__)

# Check for local development mode
USE_LOCAL_DB = os.getenv("USE_LOCAL_DB", "false").lower() == "true"

if USE_LOCAL_DB:
    print("LOCAL DEVELOPMENT MODE - Using local database")
    db_url = os.getenv(
        "DATABASE_URL",
        "postgresql://srs_admin:local_dev_password@localhost:5432/srs_db",
    )
    print(f"Using local database: {db_url.split('@')[0] if '@' in db_url else db_url}")
else:
    # Try to get connection string from Vault, fallback to environment variables
    try:
        print("Attempting to import Vault KV module...")
        from .vault_kv import get_db_connection_string

        print("Vault KV module imported successfully")
        try:
            print("Calling get_db_connection_string()...")
            db_url = get_db_connection_string()
            print("Using database credentials from Vault")
        except Exception as vault_error:
            print(f"Could not read from Vault KV: {vault_error}")
            print("   Falling back to environment variables...")
            # Fallback to environment variables or SQLite for development
            db_url = os.getenv(
                "DATABASE_URL",
                "sqlite:///./search_service.db",  # Default to SQLite for local dev
            )
            print(f"Using database URL: {db_url.split('@')[0] if '@' in db_url else db_url}")
    except ImportError as e:
        print(f"Vault module not available: {e}")
        # Fallback to environment variables or SQLite for development
        db_url = os.getenv(
            "DATABASE_URL",
            "sqlite:///./search_service.db",  # Default to SQLite for local dev
        )
        print(f"Using database URL: {db_url.split('@')[0] if '@' in db_url else db_url}")

# Use with SQLAlchemy
print("Creating SQLAlchemy engine...")

# Add connection settings with timeout
connect_args = {}
if db_url.startswith("postgresql"):
    # PostgreSQL-specific settings
    connect_args = {
        "connect_timeout": 10,  # 10 second connection timeout
    }
    print("Connecting to PostgreSQL with 10s timeout...")
elif db_url.startswith("sqlite"):
    # SQLite-specific settings
    connect_args = {"check_same_thread": False}

# Create engine with connection pooling
engine = create_engine(
    db_url,
    connect_args=connect_args,
    pool_pre_ping=True,  # Verify connections before using them
    pool_recycle=3600,  # Recycle connections after 1 hour
    poolclass=QueuePool,
    pool_size=5,
    max_overflow=10,
    echo=False,  # Set to True for SQL debugging
)
print("SQLAlchemy engine created successfully")

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """
    Initialize database tables
    Call this on application startup
    """
    try:
        print("Initializing database tables...")
        Base.metadata.create_all(bind=engine)
        print("Database tables initialized successfully")
        logger.info("Database initialized successfully")
    except Exception as e:
        print(f"Error initializing database: {e}")
        logger.error(f"Failed to initialize database: {e}")
        raise


def get_db():
    """
    Dependency function for FastAPI to get database session
    Use with: db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
