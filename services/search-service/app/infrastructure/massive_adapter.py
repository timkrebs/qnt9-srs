"""
Massive API client adapter implementing IStockAPIClient.

Wraps MassiveClient to provide the IStockAPIClient interface
for use with StockSearchService.
"""

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional

from ..domain.entities import (
    DataSource,
    Stock,
    StockIdentifier,
    StockMetadata,
    StockPrice,
    IdentifierType,
)
from ..domain.exceptions import ExternalServiceException, StockNotFoundException
from .massive_client import MassiveClient, get_massive_client
from .stock_api_client import IStockAPIClient

logger = logging.getLogger(__name__)


class MassiveAPIAdapter(IStockAPIClient):
    """
    Adapter that wraps MassiveClient to implement IStockAPIClient interface.
    
    This allows MassiveClient to be used with StockSearchService
    while keeping the clean architecture separation.
    """

    def __init__(self, client: Optional[MassiveClient] = None):
        """
        Initialize the adapter.
        
        Args:
            client: MassiveClient instance (creates default if None)
        """
        self.client = client or get_massive_client()

    async def fetch_stock(self, identifier: StockIdentifier) -> Optional[Stock]:
        """
        Fetch stock data by identifier.

        Args:
            identifier: Stock identifier (ISIN, WKN, Symbol)

        Returns:
            Stock entity with current data, or None if not found

        Raises:
            ExternalServiceException: If API call fails
        """
        try:
            # Get the ticker symbol to search
            ticker = self._get_ticker_from_identifier(identifier)
            if not ticker:
                logger.warning(f"Could not determine ticker from identifier: {identifier}")
                return None

            # Get snapshot data from Massive API
            snapshot = await self.client.get_snapshot(ticker)
            if not snapshot:
                logger.info(f"No snapshot found for ticker: {ticker}")
                return None

            # Get ticker details for additional metadata
            ticker_info = await self.client.get_ticker_details(ticker)
            
            # Convert to domain entity
            return self._convert_to_stock(snapshot, ticker_info, identifier)

        except Exception as e:
            logger.error(f"Failed to fetch stock from Massive API: {e}")
            raise ExternalServiceException("massive", str(e))

    async def search_by_name(self, name: str, limit: int = 10) -> List[Stock]:
        """
        Search stocks by company name.

        Args:
            name: Company name or partial name
            limit: Maximum number of results

        Returns:
            List of matching stocks

        Raises:
            ExternalServiceException: If API call fails
        """
        try:
            # Search tickers using Massive API
            ticker_results = await self.client.search_tickers(name, limit=limit)
            
            stocks = []
            for ticker_info in ticker_results[:limit]:
                try:
                    # Get snapshot for each ticker
                    snapshot = await self.client.get_snapshot(ticker_info.ticker)
                    if snapshot:
                        # Create identifier from ticker info
                        identifier = StockIdentifier(
                            symbol=ticker_info.ticker,
                            name=ticker_info.name,
                        )
                        stock = self._convert_to_stock(snapshot, ticker_info, identifier)
                        if stock:
                            stocks.append(stock)
                except Exception as e:
                    logger.warning(f"Failed to get snapshot for {ticker_info.ticker}: {e}")
                    continue

            logger.info(f"Massive search_by_name '{name}' returned {len(stocks)} stocks")
            return stocks

        except Exception as e:
            logger.error(f"Failed to search stocks by name: {e}")
            raise ExternalServiceException("massive", str(e))

    def get_health_status(self) -> dict:
        """
        Get API client health status.

        Returns:
            Dictionary with health metrics
        """
        return {
            "service": "massive",
            "status": "healthy" if self.client.api_key else "degraded",
            "api_configured": bool(self.client.api_key),
        }

    def _get_ticker_from_identifier(self, identifier: StockIdentifier) -> Optional[str]:
        """
        Extract ticker symbol from identifier.
        
        For ISIN/WKN, we need to resolve to symbol first.
        For symbol/name, use directly.
        """
        if identifier.symbol:
            return identifier.symbol.upper()
        
        # For ISIN, try known mappings
        if identifier.isin:
            # Try to find in local mappings (can be extended)
            isin_mappings = {
                "US0378331005": "AAPL",
                "US5949181045": "MSFT",
                "US02079K3059": "GOOGL",
                "US0231351067": "AMZN",
                "US88160R1014": "TSLA",
                "US30303M1027": "META",
                "US67066G1040": "NVDA",
                "DE0005190003": "BMW.DE",
                "DE0007664039": "VOW3.DE",
                "DE0007100000": "MBG.DE",
            }
            if identifier.isin in isin_mappings:
                return isin_mappings[identifier.isin]
            # For unknown ISINs, log and return None
            logger.warning(f"Unknown ISIN: {identifier.isin}, cannot resolve to ticker")
            return None
        
        # For WKN, try known mappings
        if identifier.wkn:
            wkn_mappings = {
                "865985": "AAPL",
                "870747": "MSFT",
                "A14Y6F": "GOOGL",
                "906866": "AMZN",
                "A1CX3T": "TSLA",
                "A1JWVX": "META",
                "918422": "NVDA",
            }
            if identifier.wkn in wkn_mappings:
                return wkn_mappings[identifier.wkn]
            logger.warning(f"Unknown WKN: {identifier.wkn}, cannot resolve to ticker")
            return None
        
        # For name queries, we can try searching
        if identifier.name:
            # The caller should use search_by_name for name queries
            return identifier.name.upper()
        
        return None

    def _convert_to_stock(
        self,
        snapshot,
        ticker_info,
        identifier: StockIdentifier,
    ) -> Optional[Stock]:
        """
        Convert Massive API response to Stock domain entity.
        """
        try:
            # Determine the current price - use best available
            current_price = (
                snapshot.last_trade_price
                or snapshot.minute_close
                or snapshot.day_close
                or snapshot.prev_close
            )
            
            if not current_price or current_price <= 0:
                logger.warning(f"No valid price found for {snapshot.ticker}")
                return None

            # Create StockPrice
            price = StockPrice(
                current=current_price,
                currency="USD",  # Massive API primarily covers US stocks
                change_absolute=snapshot.todays_change,
                change_percent=snapshot.todays_change_percent,
                previous_close=snapshot.prev_close,
                open_price=snapshot.day_open,
                day_high=snapshot.day_high,
                day_low=snapshot.day_low,
                volume=snapshot.day_volume,
            )

            # Create StockMetadata from ticker_info if available
            metadata = StockMetadata()
            if ticker_info:
                metadata = StockMetadata(
                    exchange=ticker_info.primary_exchange,
                    market_cap=ticker_info.market_cap,
                    description=ticker_info.description,
                    employees=ticker_info.total_employees,
                    website=ticker_info.homepage_url,
                )

            # Update identifier with name if available
            if ticker_info and ticker_info.name and not identifier.name:
                identifier = StockIdentifier(
                    isin=identifier.isin,
                    wkn=identifier.wkn,
                    symbol=identifier.symbol or snapshot.ticker,
                    name=ticker_info.name,
                )
            elif not identifier.symbol:
                identifier = StockIdentifier(
                    isin=identifier.isin,
                    wkn=identifier.wkn,
                    symbol=snapshot.ticker,
                    name=identifier.name or snapshot.name,
                )

            return Stock(
                identifier=identifier,
                price=price,
                metadata=metadata,
                data_source=DataSource.MASSIVE,
                last_updated=datetime.now(timezone.utc),
            )

        except Exception as e:
            logger.error(f"Failed to convert snapshot to Stock: {e}")
            return None


# Singleton instance
_massive_adapter: Optional[MassiveAPIAdapter] = None


def get_massive_adapter() -> MassiveAPIAdapter:
    """Get or create the MassiveAPIAdapter singleton."""
    global _massive_adapter
    if _massive_adapter is None:
        _massive_adapter = MassiveAPIAdapter()
    return _massive_adapter
