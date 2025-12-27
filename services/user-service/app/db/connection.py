"""
Database connection management for User Service.
"""

from typing import AsyncGenerator

import asyncpg
from app.config import settings


class DatabaseManager:
    """Manages PostgreSQL database connections."""

    def __init__(self):
        self.pool: asyncpg.Pool = None

    async def connect(self):
        """Create database connection pool."""
        if not self.pool:
            # Use local PostgreSQL database
            self.pool = await asyncpg.create_pool(
                settings.DATABASE_URL,
                min_size=settings.DATABASE_POOL_MIN_SIZE,
                max_size=settings.DATABASE_POOL_SIZE,
                command_timeout=60,
                statement_cache_size=0,  # Required for Supabase Transaction Pooler (pgbouncer)
            )

    async def disconnect(self):
        """Close database connection pool."""
        if self.pool:
            await self.pool.close()
            self.pool = None

    async def get_connection(self) -> asyncpg.Connection:
        """Get a connection from the pool."""
        if not self.pool:
            await self.connect()
        return await self.pool.acquire()

    async def release_connection(self, conn: asyncpg.Connection):
        """Release a connection back to the pool."""
        if self.pool:
            await self.pool.release(conn)


db_manager = DatabaseManager()


async def get_db_connection() -> AsyncGenerator[asyncpg.Connection, None]:
    """Dependency for getting database connection."""
    conn = await db_manager.get_connection()
    try:
        yield conn
    finally:
        await db_manager.release_connection(conn)
