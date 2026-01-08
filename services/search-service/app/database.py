"""
Database configuration and connection management.

Simplified configuration using environment variables for maximum performance.
"""

import logging
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator, Generator

from dotenv import load_dotenv
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool

from .models import Base

# Load environment variables
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

logger = logging.getLogger(__name__)

# Database configuration
# Default for local development (overridden by environment variables)
DEFAULT_DATABASE_URL = "postgresql://finio_user:finio_password@localhost:5432/finio_search"

# Connection Pool Settings (Phase 5 Optimization)
POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "20"))
MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "10"))
POOL_RECYCLE_SECONDS = int(os.getenv("DB_POOL_RECYCLE", "3600"))
POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "30"))
POOL_PRE_PING = os.getenv("DB_POOL_PRE_PING", "true").lower() == "true"

# Query Performance Settings
QUERY_LOGGING_THRESHOLD_MS = int(os.getenv("QUERY_LOG_THRESHOLD_MS", "100"))
ENABLE_QUERY_CACHE = os.getenv("ENABLE_QUERY_CACHE", "true").lower() == "true"
QUERY_CACHE_SIZE = int(os.getenv("QUERY_CACHE_SIZE", "500"))

# Read Replica Settings
READ_REPLICA_URL = os.getenv("DATABASE_READ_REPLICA_URL")
ENABLE_READ_REPLICA = os.getenv("ENABLE_READ_REPLICA", "false").lower() == "true"


def get_database_url() -> str:
    """
    Get database URL from environment.
    Uses DATABASE_URL environment variable or default.

    Returns:
        Database connection URL
    """
    db_url = os.getenv("DATABASE_URL") or DEFAULT_DATABASE_URL

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

    # For PostgreSQL with pgbouncer (Supabase Transaction Pooler)
    # Disable prepared statements as they are not supported
    if "postgresql" in db_url and "pooler.supabase.com" in db_url:
        return {"prepare_threshold": None}

    return {}


# Query performance tracking (Phase 5)
@event.listens_for(Engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """Track query start time."""
    conn.info.setdefault("query_start_time", []).append(time.time())


@event.listens_for(Engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """Log slow queries."""
    total_time = time.time() - conn.info["query_start_time"].pop()
    total_time_ms = total_time * 1000

    if total_time_ms > QUERY_LOGGING_THRESHOLD_MS:
        logger.warning(
            f"Slow query detected: {total_time_ms:.2f}ms",
            extra={
                "query_time_ms": total_time_ms,
                "statement": statement[:200],
                "parameters": str(parameters)[:100] if parameters else None,
            },
        )


# Initialize database connection
db_url = get_database_url()
connect_args = get_connect_args(db_url)

# Create primary engine with optimized connection pooling (Phase 5)
engine = create_engine(
    db_url,
    connect_args=connect_args,
    pool_pre_ping=POOL_PRE_PING,
    pool_recycle=POOL_RECYCLE_SECONDS,
    pool_timeout=POOL_TIMEOUT,
    poolclass=QueuePool,
    pool_size=POOL_SIZE,
    max_overflow=MAX_OVERFLOW,
    echo=False,
    query_cache_size=QUERY_CACHE_SIZE if ENABLE_QUERY_CACHE else 0,
)

# Create read replica engine if enabled (Phase 5)
read_engine = None
if ENABLE_READ_REPLICA and READ_REPLICA_URL:
    logger.info("Read replica enabled")
    read_engine = create_engine(
        READ_REPLICA_URL,
        connect_args=get_connect_args(READ_REPLICA_URL),
        pool_pre_ping=POOL_PRE_PING,
        pool_recycle=POOL_RECYCLE_SECONDS,
        pool_timeout=POOL_TIMEOUT,
        poolclass=QueuePool,
        pool_size=POOL_SIZE,
        max_overflow=MAX_OVERFLOW,
        echo=False,
        query_cache_size=QUERY_CACHE_SIZE if ENABLE_QUERY_CACHE else 0,
    )

# Create session factories
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
ReadSessionLocal = (
    sessionmaker(autocommit=False, autoflush=False, bind=read_engine)
    if read_engine
    else None
)

# Create async engine and session factory
# Convert postgresql:// to postgresql+asyncpg://
async_db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")
# Remove sslmode from URL for asyncpg (it uses ssl= instead)
if "?" in async_db_url:
    async_db_url = async_db_url.split("?")[0]

try:
    async_engine = create_async_engine(
        async_db_url,
        pool_pre_ping=POOL_PRE_PING,
        pool_recycle=POOL_RECYCLE_SECONDS,
        pool_size=POOL_SIZE,
        max_overflow=MAX_OVERFLOW,
        echo=False,
    )
    _async_session_factory = async_sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )
except Exception as e:
    logger.warning(f"Async engine not available: {e}")
    async_engine = None
    _async_session_factory = None


@asynccontextmanager
async def AsyncSessionLocal() -> AsyncGenerator[AsyncSession, None]:
    """Async context manager for database sessions."""
    if _async_session_factory is None:
        raise RuntimeError("Async database not configured")
    async with _async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def init_db() -> None:
    """
    Initialize database tables.

    Creates all tables on application startup.
    Uses checkfirst=True to safely handle existing tables.
    """
    try:
        logger.info("Initializing database tables...")
        Base.metadata.create_all(bind=engine, checkfirst=True)
        logger.info(
            f"Database initialized successfully (pool_size={POOL_SIZE}, "
            f"max_overflow={MAX_OVERFLOW}, query_cache={ENABLE_QUERY_CACHE})"
        )
    except Exception as e:
        error_msg = str(e).lower()
        if "already exists" in error_msg or "duplicate" in error_msg:
            logger.warning("Database objects already exist (expected)")
        else:
            logger.error(f"Failed to initialize database: {e}")
            raise


def get_db(use_replica: bool = False) -> Generator[Session, None, None]:
    """
    Get database session for dependency injection.

    Args:
        use_replica: If True and replica is available, use read replica

    Yields:
        SQLAlchemy database session
    """
    # Phase 5: Use read replica for read-only operations if available
    if use_replica and ReadSessionLocal:
        db = ReadSessionLocal()
        try:
            yield db
        except Exception as e:
            logger.warning(f"Read replica error, falling back to primary: {e}")
            db.close()
            # Fallback to primary
            db = SessionLocal()
            try:
                yield db
            finally:
                db.close()
        else:
            db.close()
    else:
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()


def get_db_stats() -> dict:
    """
    Get database connection pool statistics.

    Phase 5: Monitor connection pool health and performance.

    Returns:
        Dict with pool statistics
    """
    pool = engine.pool

    return {
        "pool_size": POOL_SIZE,
        "max_overflow": MAX_OVERFLOW,
        "checked_out": pool.checkedout(),
        "checked_in": pool.size() - pool.checkedout(),
        "overflow": pool.overflow(),
        "total_connections": pool.size(),
        "query_cache_enabled": ENABLE_QUERY_CACHE,
        "query_cache_size": QUERY_CACHE_SIZE,
        "read_replica_enabled": ENABLE_READ_REPLICA and read_engine is not None,
    }
