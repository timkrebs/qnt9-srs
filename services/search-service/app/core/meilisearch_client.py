"""
Meilisearch client for fast autocomplete and fuzzy search.

Provides sub-100ms autocomplete functionality with typo tolerance
and relevance ranking for stock symbol search.
"""

import logging
import os
from typing import Any, Optional

from meilisearch_python_sdk import AsyncClient
from meilisearch_python_sdk.errors import MeilisearchError
from meilisearch_python_sdk.models.settings import MeilisearchSettings

logger = logging.getLogger(__name__)


class MeilisearchConfig:
    """Meilisearch configuration from environment variables."""

    def __init__(self) -> None:
        """Initialize configuration from environment."""
        self.url: str = os.getenv("MEILISEARCH_URL", "http://localhost:7700")
        self.api_key: Optional[str] = os.getenv("MEILISEARCH_API_KEY")
        self.index_name: str = os.getenv("MEILISEARCH_INDEX", "stocks")
        self.timeout: int = int(os.getenv("MEILISEARCH_TIMEOUT", "5"))


class MeilisearchClientManager:
    """
    Manages Meilisearch client lifecycle and index configuration.

    Provides fast autocomplete search with typo tolerance and
    relevance ranking for stock symbols, names, and identifiers.
    """

    _instance: Optional["MeilisearchClientManager"] = None

    def __new__(cls) -> "MeilisearchClientManager":
        """Ensure singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Initialize manager (only once due to singleton)."""
        if hasattr(self, "_initialized"):
            return

        self._initialized = True
        self.config = MeilisearchConfig()
        self._client: Optional[AsyncClient] = None

        logger.info(
            "Meilisearch client manager initialized: %s",
            self.config.url,
        )

    async def get_client(self) -> AsyncClient:
        """
        Get or create Meilisearch client.

        Returns:
            Async Meilisearch client instance
        """
        if self._client is None:
            await self._create_client()
        return self._client

    async def _create_client(self) -> None:
        """Create Meilisearch client."""
        self._client = AsyncClient(
            url=self.config.url,
            api_key=self.config.api_key,
            timeout=self.config.timeout,
        )

        logger.info(
            "Meilisearch client created: %s",
            self.config.url,
        )

    async def initialize_index(self) -> None:
        """
        Initialize stock search index with optimized settings.

        Configures:
        - Searchable attributes (symbol, name, isin, wkn)
        - Filterable attributes (exchange, currency)
        - Ranking rules for relevance
        - Typo tolerance for user errors
        """
        client = await self.get_client()

        try:
            index = client.index(self.config.index_name)

            settings = MeilisearchSettings(
                searchable_attributes=[
                    "symbol",
                    "name",
                    "isin",
                    "wkn",
                ],
                filterable_attributes=[
                    "exchange",
                    "currency",
                    "sector",
                ],
                sortable_attributes=[
                    "market_cap",
                    "volume",
                ],
                ranking_rules=[
                    "words",
                    "typo",
                    "proximity",
                    "attribute",
                    "sort",
                    "exactness",
                ],
                typo_tolerance={
                    "enabled": True,
                    "min_word_size_for_typos": {
                        "one_typo": 3,
                        "two_typos": 5,
                    },
                },
                pagination={
                    "max_total_hits": 1000,
                },
            )

            await index.update_settings(settings)

            logger.info(
                "Meilisearch index '%s' initialized with optimized settings",
                self.config.index_name,
            )

        except MeilisearchError as e:
            logger.error("Failed to initialize Meilisearch index: %s", e)
            raise

    async def health_check(self) -> dict[str, Any]:
        """
        Check Meilisearch health.

        Returns:
            Health status with version and connectivity info
        """
        try:
            client = await self.get_client()
            health = await client.health()
            version = await client.get_version()

            return {
                "status": health.status if health else "unknown",
                "version": version.pkg_version if version else "unknown",
                "url": self.config.url,
            }

        except MeilisearchError as e:
            logger.error("Meilisearch health check failed: %s", e)
            return {
                "status": "unhealthy",
                "error": str(e),
                "url": self.config.url,
            }

    async def search_autocomplete(
        self,
        query: str,
        limit: int = 10,
        filters: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """
        Perform autocomplete search.

        Args:
            query: Search query
            limit: Maximum results (default 10)
            filters: Optional filter expression

        Returns:
            List of matching stocks
        """
        try:
            client = await self.get_client()
            index = client.index(self.config.index_name)

            results = await index.search(
                query=query,
                limit=limit,
                filter=filters,
            )

            return results.hits if results else []

        except MeilisearchError as e:
            logger.error("Autocomplete search failed: %s", e)
            return []

    async def add_documents(
        self,
        documents: list[dict[str, Any]],
        primary_key: str = "symbol",
    ) -> None:
        """
        Add or update documents in index.

        Args:
            documents: List of stock documents
            primary_key: Primary key field
        """
        try:
            client = await self.get_client()
            index = client.index(self.config.index_name)

            task = await index.add_documents(
                documents=documents,
                primary_key=primary_key,
            )

            logger.info(
                "Added %d documents to index '%s' (task: %s)",
                len(documents),
                self.config.index_name,
                task.task_uid,
            )

        except MeilisearchError as e:
            logger.error("Failed to add documents: %s", e)
            raise

    async def delete_documents(self, document_ids: list[str]) -> None:
        """
        Delete documents from index.

        Args:
            document_ids: List of document IDs to delete
        """
        try:
            client = await self.get_client()
            index = client.index(self.config.index_name)

            task = await index.delete_documents(document_ids)

            logger.info(
                "Deleted %d documents from index '%s' (task: %s)",
                len(document_ids),
                self.config.index_name,
                task.task_uid,
            )

        except MeilisearchError as e:
            logger.error("Failed to delete documents: %s", e)
            raise

    async def get_index_stats(self) -> dict[str, Any]:
        """
        Get index statistics.

        Returns:
            Index stats including document count and size
        """
        try:
            client = await self.get_client()
            index = client.index(self.config.index_name)

            stats = await index.get_stats()

            return {
                "number_of_documents": stats.number_of_documents,
                "is_indexing": stats.is_indexing,
                "field_distribution": stats.field_distribution,
            }

        except MeilisearchError as e:
            logger.error("Failed to get index stats: %s", e)
            return {}

    async def close(self) -> None:
        """Close Meilisearch client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
            logger.info("Meilisearch client closed")


_meilisearch_manager = MeilisearchClientManager()


def get_meilisearch_manager() -> MeilisearchClientManager:
    """Get global Meilisearch manager instance."""
    return _meilisearch_manager
