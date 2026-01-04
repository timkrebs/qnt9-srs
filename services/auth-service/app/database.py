"""
Database connection management for Auth Service.

Provides async PostgreSQL connection pooling using asyncpg with transaction support.
Also manages Supabase client for authentication.
"""

from typing import AsyncGenerator, Optional

import asyncpg
from asyncpg import Pool

from supabase import Client as SupabaseClient
from supabase import create_client

from .config import settings
from .logging_config import get_logger

logger = get_logger(__name__)


class DatabaseManager:
    """
    Manages PostgreSQL database connections with connection pooling.

    Attributes:
        pool: asyncpg connection pool
    """

    def __init__(self) -> None:
        """Initialize database manager."""
        self.pool: Optional[Pool] = None

    async def connect(self) -> None:
        """
        Create database connection pool.

        Creates an async connection pool to PostgreSQL with configurable
        pool size for optimal performance.
        """
        if self.pool is not None:
            return

        logger.info("Connecting to database...")
        try:
            self.pool = await asyncpg.create_pool(
                settings.DATABASE_URL,
                min_size=settings.DATABASE_POOL_MIN_SIZE,
                max_size=settings.DATABASE_POOL_SIZE,
                command_timeout=60,
                statement_cache_size=0,  # Required for Supabase Transaction Pooler (pgbouncer)
            )
            logger.info(
                "Database connection pool created",
                extra={
                    "extra_fields": {
                        "pool_min_size": settings.DATABASE_POOL_MIN_SIZE,
                        "pool_max_size": settings.DATABASE_POOL_SIZE,
                    }
                },
            )
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    async def disconnect(self) -> None:
        """Close database connection pool."""
        if self.pool:
            await self.pool.close()
            self.pool = None
            logger.info("Database connection pool closed")

    async def get_connection(self) -> asyncpg.Connection:
        """
        Get a connection from the pool.

        Returns:
            asyncpg.Connection: Database connection

        Raises:
            RuntimeError: If pool is not initialized
        """
        if not self.pool:
            await self.connect()
        return await self.pool.acquire()

    async def release_connection(self, conn: asyncpg.Connection) -> None:
        """
        Release a connection back to the pool.

        Args:
            conn: Connection to release
        """
        if self.pool:
            await self.pool.release(conn)

    async def execute(self, query: str, *args) -> str:
        """
        Execute a query without returning results.

        Args:
            query: SQL query string
            *args: Query parameters

        Returns:
            Status string from execution
        """
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)

    async def fetch(self, query: str, *args) -> list:
        """
        Execute a query and fetch all results.

        Args:
            query: SQL query string
            *args: Query parameters

        Returns:
            List of records
        """
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)

    async def fetchrow(self, query: str, *args) -> Optional[asyncpg.Record]:
        """
        Execute a query and fetch one result.

        Args:
            query: SQL query string
            *args: Query parameters

        Returns:
            Single record or None
        """
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, *args)

    async def fetchval(self, query: str, *args):
        """
        Execute a query and fetch a single value.

        Args:
            query: SQL query string
            *args: Query parameters

        Returns:
            Single value from first column of first row
        """
        async with self.pool.acquire() as conn:
            return await conn.fetchval(query, *args)

    def transaction(self):
        """
        Get a transaction context manager.

        Usage:
            async with db_manager.transaction() as conn:
                await conn.execute("INSERT ...")
                await conn.execute("INSERT ...")

        Returns:
            Async context manager that provides a connection with transaction
        """
        if not self.pool:
            raise RuntimeError("Database pool not initialized. Call connect() first.")
        return TransactionContext(self.pool)


class TransactionContext:
    """
    Context manager for database transactions.

    Ensures atomic operations - all succeed or all rollback.
    """

    def __init__(self, pool: Pool):
        self.pool = pool
        self.conn: Optional[asyncpg.Connection] = None
        self.transaction: Optional[asyncpg.transaction.Transaction] = None

    async def __aenter__(self) -> asyncpg.Connection:
        """Acquire connection and start transaction."""
        self.conn = await self.pool.acquire()
        self.transaction = self.conn.transaction()
        await self.transaction.start()
        return self.conn

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Commit transaction on success, rollback on error, then release connection."""
        try:
            if exc_type is not None:
                await self.transaction.rollback()
                logger.warning(f"Transaction rolled back due to error: {exc_val}")
            else:
                await self.transaction.commit()
                logger.debug("Transaction committed successfully")
        finally:
            await self.pool.release(self.conn)


# Global database manager instance
db_manager = DatabaseManager()


class SupabaseManager:
    """
    Manages Supabase client for authentication operations.

    Provides singleton access to Supabase client with admin privileges.
    """

    def __init__(self) -> None:
        """Initialize Supabase manager."""
        self._client: Optional[SupabaseClient] = None

    def get_client(self) -> SupabaseClient:
        """
        Get or create Supabase client.

        Returns:
            SupabaseClient: Supabase client instance with service role key

        Raises:
            RuntimeError: If Supabase configuration is missing
        """
        if self._client is None:
            logger.info("Initializing Supabase client...")
            try:
                # Create client with service role key
                # The service role key automatically bypasses Row Level Security
                self._client = create_client(
                    supabase_url=settings.SUPABASE_URL,
                    supabase_key=settings.SUPABASE_SERVICE_ROLE_KEY,
                )
                logger.info(
                    "Supabase client initialized with service role (bypasses RLS)",
                    extra={
                        "extra_fields": {
                            "supabase_url": settings.SUPABASE_URL,
                        }
                    },
                )
            except Exception as e:
                logger.error(f"Failed to initialize Supabase client: {e}")
                raise RuntimeError(f"Supabase client initialization failed: {e}")

        return self._client

    def reset_client(self) -> None:
        """Reset Supabase client (useful for testing)."""
        self._client = None
        logger.info("Supabase client reset")


# Global Supabase manager instance
supabase_manager = SupabaseManager()


def get_supabase_client() -> SupabaseClient:
    """
    FastAPI dependency for Supabase client access.

    Returns:
        SupabaseClient: Authenticated Supabase client
    """
    return supabase_manager.get_client()


async def get_db() -> AsyncGenerator[DatabaseManager, None]:
    """
    FastAPI dependency for database access.

    Yields:
        DatabaseManager instance
    """
    yield db_manager


async def get_db_connection() -> AsyncGenerator[asyncpg.Connection, None]:
    """
    FastAPI dependency for getting a database connection.

    Yields:
        asyncpg.Connection from the pool
    """
    conn = await db_manager.get_connection()
    try:
        yield conn
    finally:
        await db_manager.release_connection(conn)
