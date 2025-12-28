"""Database connection management."""

import asyncpg
import structlog
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from app.config import settings

logger = structlog.get_logger(__name__)

# Global connection pool
_pool: asyncpg.Pool | None = None


async def get_db_pool() -> asyncpg.Pool:
    """
    Get or create database connection pool.
    
    Returns:
        asyncpg.Pool: Database connection pool
    """
    global _pool
    
    if _pool is None:
        logger.info("Creating database connection pool")
        _pool = await asyncpg.create_pool(
            settings.DATABASE_URL,
            min_size=2,
            max_size=10,
            command_timeout=10,
            statement_cache_size=0,  # Required for Supabase pooler (pgbouncer)
        )
        logger.info("Database connection pool created")
    
    return _pool


async def close_db_pool():
    """Close database connection pool."""
    global _pool
    
    if _pool is not None:
        logger.info("Closing database connection pool")
        await _pool.close()
        _pool = None
        logger.info("Database connection pool closed")


@asynccontextmanager
async def get_db_connection() -> AsyncGenerator[asyncpg.Connection, None]:
    """
    Get database connection from pool.
    
    Yields:
        asyncpg.Connection: Database connection
        
    Example:
        async with get_db_connection() as conn:
            result = await conn.fetchrow("SELECT * FROM watchlists WHERE id = $1", id)
    """
    pool = await get_db_pool()
    async with pool.acquire() as connection:
        yield connection
