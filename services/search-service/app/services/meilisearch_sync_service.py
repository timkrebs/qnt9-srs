"""
Meilisearch index synchronization service.

Keeps Meilisearch index in sync with PostgreSQL symbol mappings
for fast autocomplete functionality.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import AsyncSessionLocal
from ..models import SymbolMapping
from .meilisearch_client import get_meilisearch_manager

logger = logging.getLogger(__name__)


class MeilisearchSyncService:
    """
    Synchronizes PostgreSQL data to Meilisearch index.

    Provides batch and incremental sync operations to keep
    Meilisearch autocomplete index up-to-date.
    """

    def __init__(self) -> None:
        """Initialize sync service."""
        self.meilisearch = get_meilisearch_manager()

    async def full_sync(self) -> dict[str, Any]:
        """
        Perform full index synchronization.

        Loads all symbol mappings from PostgreSQL and updates
        Meilisearch index.

        Returns:
            Sync statistics
        """
        start_time = datetime.now(timezone.utc)
        logger.info("Starting full Meilisearch index sync")

        try:
            async with AsyncSessionLocal() as session:
                documents = await self._load_all_symbols(session)

            if not documents:
                logger.warning("No symbols found for sync")
                return {
                    "status": "completed",
                    "documents_synced": 0,
                    "duration_seconds": 0,
                }

            await self.meilisearch.add_documents(documents)

            duration = (datetime.now(timezone.utc) - start_time).total_seconds()

            logger.info(
                "Full sync completed: %d documents in %.2f seconds",
                len(documents),
                duration,
            )

            return {
                "status": "completed",
                "documents_synced": len(documents),
                "duration_seconds": duration,
                "synced_at": start_time.isoformat(),
            }

        except Exception as e:
            logger.error("Full sync failed: %s", e)
            return {
                "status": "failed",
                "error": str(e),
            }

    async def incremental_sync(
        self,
        since: datetime,
    ) -> dict[str, Any]:
        """
        Perform incremental sync for recently updated symbols.

        Args:
            since: Only sync symbols updated after this timestamp

        Returns:
            Sync statistics
        """
        start_time = datetime.now(timezone.utc)
        logger.info("Starting incremental sync since %s", since)

        try:
            async with AsyncSessionLocal() as session:
                documents = await self._load_symbols_since(session, since)

            if not documents:
                logger.info("No updates found for incremental sync")
                return {
                    "status": "completed",
                    "documents_synced": 0,
                    "duration_seconds": 0,
                }

            await self.meilisearch.add_documents(documents)

            duration = (datetime.now(timezone.utc) - start_time).total_seconds()

            logger.info(
                "Incremental sync completed: %d documents in %.2f seconds",
                len(documents),
                duration,
            )

            return {
                "status": "completed",
                "documents_synced": len(documents),
                "duration_seconds": duration,
                "synced_at": start_time.isoformat(),
            }

        except Exception as e:
            logger.error("Incremental sync failed: %s", e)
            return {
                "status": "failed",
                "error": str(e),
            }

    async def _load_all_symbols(
        self,
        session: AsyncSession,
    ) -> list[dict[str, Any]]:
        """
        Load all active symbol mappings from database.

        Args:
            session: Database session

        Returns:
            List of documents for Meilisearch
        """
        stmt = select(SymbolMapping).where(SymbolMapping.is_active == True)
        result = await session.execute(stmt)
        mappings = result.scalars().all()

        documents = []
        symbols_seen = set()

        for mapping in mappings:
            if mapping.yahoo_symbol not in symbols_seen:
                doc = self._create_document(mapping)
                if doc:
                    documents.append(doc)
                    symbols_seen.add(mapping.yahoo_symbol)
            else:
                existing_doc = next(
                    (d for d in documents if d["symbol"] == mapping.yahoo_symbol),
                    None,
                )
                if existing_doc:
                    self._merge_identifiers(existing_doc, mapping)

        logger.info("Loaded %d unique symbols from database", len(documents))
        return documents

    async def _load_symbols_since(
        self,
        session: AsyncSession,
        since: datetime,
    ) -> list[dict[str, Any]]:
        """
        Load symbols updated since timestamp.

        Args:
            session: Database session
            since: Timestamp cutoff

        Returns:
            List of updated documents
        """
        stmt = (
            select(SymbolMapping)
            .where(SymbolMapping.is_active == True)
            .where(SymbolMapping.updated_at >= since)
        )
        result = await session.execute(stmt)
        mappings = result.scalars().all()

        documents = []
        symbols_seen = set()

        for mapping in mappings:
            if mapping.yahoo_symbol not in symbols_seen:
                doc = self._create_document(mapping)
                if doc:
                    documents.append(doc)
                    symbols_seen.add(mapping.yahoo_symbol)
            else:
                existing_doc = next(
                    (d for d in documents if d["symbol"] == mapping.yahoo_symbol),
                    None,
                )
                if existing_doc:
                    self._merge_identifiers(existing_doc, mapping)

        return documents

    def _create_document(
        self,
        mapping: SymbolMapping,
    ) -> dict[str, Any] | None:
        """
        Create Meilisearch document from symbol mapping.

        Args:
            mapping: Symbol mapping from database

        Returns:
            Document dict or None if invalid
        """
        if not mapping.yahoo_symbol:
            return None

        doc = {
            "symbol": mapping.yahoo_symbol,
            "name": mapping.company_name or "",
            "priority": mapping.priority or 0,
        }

        if mapping.identifier_type == "ISIN":
            doc["isin"] = mapping.identifier_value
        elif mapping.identifier_type == "WKN":
            doc["wkn"] = mapping.identifier_value

        if hasattr(mapping, "exchange") and mapping.exchange:
            doc["exchange"] = mapping.exchange

        if hasattr(mapping, "currency") and mapping.currency:
            doc["currency"] = mapping.currency

        return doc

    def _merge_identifiers(
        self,
        doc: dict[str, Any],
        mapping: SymbolMapping,
    ) -> None:
        """
        Merge additional identifiers into existing document.

        Args:
            doc: Existing document
            mapping: Additional mapping to merge
        """
        if mapping.identifier_type == "ISIN" and "isin" not in doc:
            doc["isin"] = mapping.identifier_value
        elif mapping.identifier_type == "WKN" and "wkn" not in doc:
            doc["wkn"] = mapping.identifier_value

    async def get_sync_status(self) -> dict[str, Any]:
        """
        Get current sync status.

        Returns:
            Status information including document count
        """
        try:
            stats = await self.meilisearch.get_index_stats()
            health = await self.meilisearch.health_check()

            return {
                "meilisearch_status": health.get("status"),
                "meilisearch_version": health.get("version"),
                "index_documents": stats.get("number_of_documents", 0),
                "is_indexing": stats.get("is_indexing", False),
            }

        except Exception as e:
            logger.error("Failed to get sync status: %s", e)
            return {
                "status": "error",
                "error": str(e),
            }


_sync_service = MeilisearchSyncService()


def get_sync_service() -> MeilisearchSyncService:
    """Get global sync service instance."""
    return _sync_service
