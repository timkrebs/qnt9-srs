"""
Redis connection management with pooling and health checks.

Provides centralized Redis client management for distributed caching
and rate limiting across the application.
"""

import logging
import os
from typing import Optional
from urllib.parse import urlparse

from redis.asyncio import ConnectionPool, Redis
from redis.asyncio.retry import Retry
from redis.backoff import ExponentialBackoff

logger = logging.getLogger(__name__)


class RedisConfig:
    """Redis configuration from environment variables."""

    def __init__(self) -> None:
        """Initialize configuration from environment."""
        redis_url = os.getenv("REDIS_URL")

        if redis_url:
            parsed = urlparse(redis_url)
            self.host: str = parsed.hostname or ""
            self.port: int = parsed.port or 6379
            self.password: Optional[str] = parsed.password
            self.db: int = int(parsed.path.lstrip("/") or "0")
            self.username: Optional[str] = parsed.username
        else:
            self.host: str = os.getenv("REDIS_HOST")
            self.port: int = int(os.getenv("REDIS_PORT", "6379"))
            self.db: int = int(os.getenv("REDIS_DB", "0"))
            self.password: Optional[str] = os.getenv("REDIS_PASSWORD")
            self.username: Optional[str] = os.getenv("REDIS_USERNAME")

        self.max_connections: int = int(os.getenv("REDIS_MAX_CONNECTIONS", "50"))
        self.socket_timeout: int = int(os.getenv("REDIS_SOCKET_TIMEOUT", "5"))
        self.socket_connect_timeout: int = int(os.getenv("REDIS_CONNECT_TIMEOUT", "5"))
        self.decode_responses: bool = True
        self.retry_on_timeout: bool = True

        self.max_retries: int = 3
        self.retry_min_backoff_ms: int = 10
        self.retry_max_backoff_ms: int = 1000


class RedisConnectionManager:
    """
    Manages Redis connection pool and client lifecycle.

    Provides a singleton Redis client with automatic connection pooling,
    retry logic, and health check capabilities.
    """

    _instance: Optional["RedisConnectionManager"] = None
    _client: Optional[Redis] = None
    _pool: Optional[ConnectionPool] = None

    def __new__(cls) -> "RedisConnectionManager":
        """Ensure singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Initialize manager (only once due to singleton)."""
        if not hasattr(self, "_initialized"):
            self.config = RedisConfig()
            self._initialized = True
            logger.info(
                "Redis connection manager initialized: %s:%d",
                self.config.host,
                self.config.port,
            )

    async def initialize(self) -> None:
        """
        Initialize Redis connection pool.

        Creates the Redis client and connection pool.
        Can be called explicitly during startup or will be
        called automatically on first use.
        """
        if self._client is None:
            await self._create_client()
            logger.info("Redis connection pool initialized")

    async def get_client(self) -> Redis:
        """
        Get or create Redis client.

        Returns:
            Async Redis client instance
        """
        if self._client is None:
            await self._create_client()
        return self._client

    async def _create_client(self) -> None:
        """Create Redis client with connection pool."""
        retry = Retry(
            ExponentialBackoff(
                base=self.config.retry_min_backoff_ms,
                cap=self.config.retry_max_backoff_ms,
            ),
            self.config.max_retries,
        )

        pool_kwargs = {
            "host": self.config.host,
            "port": self.config.port,
            "db": self.config.db,
            "password": self.config.password,
            "max_connections": self.config.max_connections,
            "socket_timeout": self.config.socket_timeout,
            "socket_connect_timeout": self.config.socket_connect_timeout,
            "decode_responses": self.config.decode_responses,
            "retry_on_timeout": self.config.retry_on_timeout,
            "retry": retry,
        }

        if hasattr(self.config, "username") and self.config.username:
            pool_kwargs["username"] = self.config.username

        self._pool = ConnectionPool(**pool_kwargs)

        self._client = Redis(connection_pool=self._pool)

        logger.info(
            "Redis client created with pool (max_connections=%d)",
            self.config.max_connections,
        )

    async def health_check(self) -> bool:
        """
        Check Redis health.

        Returns:
            True if healthy, False otherwise
        """
        try:
            client = await self.get_client()
            await client.ping()
            return True
        except Exception as e:
            logger.error("Redis health check failed: %s", e)
            return False

    async def get_pool_stats(self) -> dict:
        """
        Get connection pool statistics.

        Returns:
            Dictionary with pool metrics
        """
        if not self._pool:
            return {"status": "not_initialized"}

        return {
            "max_connections": self._pool.max_connections,
            "connection_kwargs": {
                "host": self.config.host,
                "port": self.config.port,
                "db": self.config.db,
            },
        }

    async def close(self) -> None:
        """Close Redis connection and clean up resources."""
        if self._client:
            await self._client.close()
            self._client = None
            logger.info("Redis client closed")

        if self._pool:
            await self._pool.disconnect()
            self._pool = None
            logger.info("Redis connection pool closed")


_redis_manager = RedisConnectionManager()


def get_redis_manager() -> RedisConnectionManager:
    """
    Get the global Redis connection manager instance.

    Returns:
        RedisConnectionManager singleton instance
    """
    return _redis_manager


async def get_redis_client() -> Redis:
    """
    Dependency injection function for Redis client.

    Returns:
        Async Redis client instance
    """
    return await _redis_manager.get_client()


async def redis_health_check() -> bool:
    """
    Check if Redis is healthy.

    Returns:
        True if healthy, False otherwise
    """
    return await _redis_manager.health_check()


async def get_redis_stats() -> dict:
    """
    Get Redis connection pool statistics.

    Returns:
        Pool statistics dictionary
    """
    return await _redis_manager.get_pool_stats()


async def close_redis_connections() -> None:
    """Close all Redis connections. Call during application shutdown."""
    await _redis_manager.close()
