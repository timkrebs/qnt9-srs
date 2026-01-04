"""
Symbol mapping repository for ISIN/WKN to Yahoo symbol resolution.

Provides database access for symbol mappings with caching support.
"""

import logging
from typing import Optional

from cachetools import TTLCache
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import SymbolMapping

logger = logging.getLogger(__name__)


class SymbolMappingRepository:
    """
    Repository for symbol mapping database operations.

    Provides methods to resolve ISINs, WKNs, and company names to Yahoo
    Finance symbols using the database with in-memory caching.
    """

    def __init__(self, cache_ttl: int = 3600):
        """
        Initialize symbol mapping repository.

        Args:
            cache_ttl: Cache time-to-live in seconds (default: 1 hour)
        """
        self.cache: TTLCache = TTLCache(maxsize=500, ttl=cache_ttl)
        logger.info("SymbolMappingRepository initialized with cache TTL %ds", cache_ttl)

    async def get_mapping(
        self, identifier_type: str, identifier_value: str, session: AsyncSession
    ) -> Optional[str]:
        """
        Get Yahoo symbol for given identifier.

        Args:
            identifier_type: Type of identifier (isin, wkn, or name)
            identifier_value: The identifier value
            session: Database session

        Returns:
            Yahoo Finance symbol if found, None otherwise
        """
        cache_key = f"{identifier_type}:{identifier_value.upper()}"

        if cache_key in self.cache:
            logger.debug("Symbol mapping cache hit for %s", cache_key)
            return self.cache[cache_key]

        try:
            stmt = (
                select(SymbolMapping)
                .where(SymbolMapping.identifier_type == identifier_type)
                .where(SymbolMapping.identifier_value == identifier_value.upper())
                .where(SymbolMapping.is_active == 1)
                .order_by(SymbolMapping.priority.desc())
                .limit(1)
            )

            result = await session.execute(stmt)
            mapping = result.scalar_one_or_none()

            if mapping:
                self.cache[cache_key] = mapping.yahoo_symbol
                logger.debug(
                    "Found mapping %s -> %s (priority: %d)",
                    cache_key,
                    mapping.yahoo_symbol,
                    mapping.priority,
                )
                return mapping.yahoo_symbol

            logger.debug("No mapping found for %s", cache_key)
            return None

        except Exception as e:
            logger.error("Error fetching symbol mapping for %s: %s", cache_key, e)
            return None

    async def get_isin_mapping(self, isin: str, session: AsyncSession) -> Optional[str]:
        """
        Get Yahoo symbol for ISIN.

        Args:
            isin: International Securities Identification Number
            session: Database session

        Returns:
            Yahoo Finance symbol if found, None otherwise
        """
        return await self.get_mapping("isin", isin, session)

    async def get_wkn_mapping(self, wkn: str, session: AsyncSession) -> Optional[str]:
        """
        Get Yahoo symbol for WKN.

        Args:
            wkn: German securities identification number
            session: Database session

        Returns:
            Yahoo Finance symbol if found, None otherwise
        """
        return await self.get_mapping("wkn", wkn, session)

    async def get_name_mapping(self, name: str, session: AsyncSession) -> Optional[str]:
        """
        Get Yahoo symbol for company name.

        Args:
            name: Company name
            session: Database session

        Returns:
            Yahoo Finance symbol if found, None otherwise
        """
        return await self.get_mapping("name", name, session)

    async def add_mapping(
        self,
        identifier_type: str,
        identifier_value: str,
        yahoo_symbol: str,
        session: AsyncSession,
        stock_name: Optional[str] = None,
        exchange: Optional[str] = None,
        priority: int = 50,
    ) -> SymbolMapping:
        """
        Add a new symbol mapping.

        Args:
            identifier_type: Type of identifier (isin, wkn, or name)
            identifier_value: The identifier value
            yahoo_symbol: Yahoo Finance symbol
            session: Database session
            stock_name: Company name (optional)
            exchange: Stock exchange (optional)
            priority: Mapping priority (default: 50)

        Returns:
            Created SymbolMapping instance
        """
        mapping = SymbolMapping(
            identifier_type=identifier_type,
            identifier_value=identifier_value.upper(),
            yahoo_symbol=yahoo_symbol,
            stock_name=stock_name,
            exchange=exchange,
            priority=priority,
            is_active=1,
        )

        session.add(mapping)
        await session.commit()
        await session.refresh(mapping)

        cache_key = f"{identifier_type}:{identifier_value.upper()}"
        self.cache[cache_key] = yahoo_symbol

        logger.info("Added new symbol mapping: %s -> %s", cache_key, yahoo_symbol)
        return mapping

    def clear_cache(self) -> None:
        """Clear the in-memory cache."""
        self.cache.clear()
        logger.info("Symbol mapping cache cleared")

    def get_cache_stats(self) -> dict:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache size and capacity
        """
        return {
            "size": len(self.cache),
            "max_size": self.cache.maxsize,
            "ttl": self.cache.ttl,
        }
