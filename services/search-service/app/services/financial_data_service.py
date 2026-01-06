"""
Financial Data Service for real-time stock data integration using Polygon.io API.

Provides:
- Real-time stock quotes
- Intraday price data for charts
- Company news feed
- Market statistics

IMPORTANT: This service requires a valid MASSIVE_API_KEY environment variable.
No mock data is returned - if API key is missing, errors are raised.
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import aiohttp

logger = logging.getLogger(__name__)


class APIKeyNotConfiguredError(Exception):
    """Raised when MASSIVE_API_KEY is not configured."""
    pass


class FinancialDataService:
    """Service for fetching real-time financial data from Massive API (formerly Polygon.io)."""

    def __init__(self):
        """Initialize the financial data service."""
        self.api_key = os.getenv("MASSIVE_API_KEY", "")
        self.base_url = "https://api.polygon.io"
        self.session: Optional[aiohttp.ClientSession] = None

        if not self.api_key:
            logger.error("CRITICAL: MASSIVE_API_KEY not set - real stock data will be unavailable")

    async def get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    async def close(self):
        """Close the aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()

    async def get_real_time_quote(self, symbol: str) -> Dict[str, Any]:
        """
        Get real-time quote data for a symbol.

        Args:
            symbol: Stock ticker symbol (e.g., AAPL, MSFT)

        Returns:
            Dictionary containing current price, change, volume, and other data

        Raises:
            APIKeyNotConfiguredError: If MASSIVE_API_KEY is not set
            ValueError: If no data available for symbol
        """
        if not self.api_key:
            logger.error(f"Cannot fetch quote for {symbol}: MASSIVE_API_KEY not configured")
            raise APIKeyNotConfiguredError("MASSIVE_API_KEY environment variable is not configured")

        try:
            # Get previous day's close for comparison
            prev_close_data = await self._get_previous_close(symbol)
            if not prev_close_data:
                logger.error(f"No previous close data available for {symbol}")
                raise ValueError(f"No previous close data available for symbol: {symbol}")

            # Get current snapshot for real-time data
            snapshot_data = await self._get_snapshot(symbol)

            if snapshot_data:
                current_price = snapshot_data.get("last", {}).get("price")
                
                # If price is missing or zero, raise an error
                if current_price is None or current_price == 0:
                    logger.error(f"Invalid price data for {symbol} (price={current_price})")
                    raise ValueError(f"Invalid or missing price data for symbol: {symbol}")
                
                prev_close = prev_close_data.get("close", current_price)
                change = current_price - prev_close
                change_percent = (change / prev_close * 100) if prev_close != 0 else 0

                return {
                    "symbol": symbol.upper(),
                    "name": symbol.upper(),  # Add name field for frontend compatibility
                    "price": round(current_price, 2),
                    "change": round(change, 2),
                    "change_percent": round(change_percent, 2),  # Return as number, not string
                    "volume": snapshot_data.get("day", {}).get("volume", 0),
                    "open": snapshot_data.get("day", {}).get("open", 0),
                    "high": snapshot_data.get("day", {}).get("high", 0),
                    "low": snapshot_data.get("day", {}).get("low", 0),
                    "previous_close": prev_close,
                    "market_cap": snapshot_data.get("market_cap", 0),
                    "timestamp": datetime.utcnow().isoformat(),
                }
            else:
                logger.error(f"No snapshot data available for {symbol}")
                raise ValueError(f"No snapshot data available for symbol: {symbol}")

        except (APIKeyNotConfiguredError, ValueError):
            raise
        except Exception as e:
            logger.error(f"Error fetching quote for {symbol}: {e}")
            raise ValueError(f"Failed to fetch quote for {symbol}: {str(e)}")

    async def _get_previous_close(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get previous day's closing data."""
        session = await self.get_session()
        url = f"{self.base_url}/v2/aggs/ticker/{symbol.upper()}/prev"
        params = {"adjusted": "true", "apiKey": self.api_key}

        try:
            async with session.get(url, params=params, timeout=5) as response:
                if response.status == 200:
                    data = await response.json()
                    results = data.get("results", [])
                    if results:
                        result = results[0]
                        return {
                            "close": result.get("c", 0),
                            "open": result.get("o", 0),
                            "high": result.get("h", 0),
                            "low": result.get("l", 0),
                            "volume": result.get("v", 0),
                        }
                return None
        except Exception as e:
            logger.error(f"Error fetching previous close for {symbol}: {e}")
            return None

    async def _get_snapshot(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get current snapshot data."""
        session = await self.get_session()
        url = f"{self.base_url}/v2/snapshot/locale/us/markets/stocks/tickers/{symbol.upper()}"
        params = {"apiKey": self.api_key}

        try:
            async with session.get(url, params=params, timeout=5) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("ticker", {})
                return None
        except Exception as e:
            logger.error(f"Error fetching snapshot for {symbol}: {e}")
            return None

    async def get_intraday_data(
        self, symbol: str, timespan: str = "minute", multiplier: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get intraday price data for charts.

        Args:
            symbol: Stock ticker symbol
            timespan: Time resolution (minute, hour, day)
            multiplier: Multiplier for timespan (e.g., 5 for 5-minute bars)

        Returns:
            List of OHLCV data points

        Raises:
            APIKeyNotConfiguredError: If MASSIVE_API_KEY is not set
            ValueError: If no data available
        """
        if not self.api_key:
            logger.error(f"Cannot fetch intraday data for {symbol}: MASSIVE_API_KEY not configured")
            raise APIKeyNotConfiguredError("MASSIVE_API_KEY environment variable is not configured")

        try:
            # Get data for last trading day
            to_date = datetime.utcnow()
            from_date = to_date - timedelta(days=1)

            session = await self.get_session()
            url = f"{self.base_url}/v2/aggs/ticker/{symbol.upper()}/range/{multiplier}/{timespan}/{from_date.strftime('%Y-%m-%d')}/{to_date.strftime('%Y-%m-%d')}"
            params = {"adjusted": "true", "sort": "asc", "apiKey": self.api_key}

            async with session.get(url, params=params, timeout=10) as response:
                if response.status != 200:
                    logger.error(f"Failed to fetch intraday data: HTTP {response.status}")
                    raise ValueError(f"Failed to fetch intraday data for {symbol}: HTTP {response.status}")

                data = await response.json()
                results = data.get("results", [])

                if not results:
                    logger.error(f"No intraday data available for {symbol}")
                    raise ValueError(f"No intraday data available for symbol: {symbol}")

                chart_data = []
                for bar in results[-100:]:  # Last 100 data points
                    timestamp = datetime.fromtimestamp(bar["t"] / 1000)
                    chart_data.append(
                        {
                            "timestamp": timestamp.isoformat(),
                            "open": round(bar["o"], 2),
                            "high": round(bar["h"], 2),
                            "low": round(bar["l"], 2),
                            "close": round(bar["c"], 2),
                            "volume": bar["v"],
                        }
                    )

                return chart_data

        except (APIKeyNotConfiguredError, ValueError):
            raise
        except Exception as e:
            logger.error(f"Error fetching intraday data for {symbol}: {e}")
            raise ValueError(f"Failed to fetch intraday data for {symbol}: {str(e)}")

    async def get_company_news(self, symbol: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Fetch latest news for a company.

        Args:
            symbol: Stock ticker symbol
            limit: Maximum number of news items to return

        Returns:
            List of news articles with title, url, summary, etc.

        Raises:
            APIKeyNotConfiguredError: If MASSIVE_API_KEY is not set
            ValueError: If no news available
        """
        if not self.api_key:
            logger.error(f"Cannot fetch news for {symbol}: MASSIVE_API_KEY not configured")
            raise APIKeyNotConfiguredError("MASSIVE_API_KEY environment variable is not configured")

        try:
            session = await self.get_session()
            url = f"{self.base_url}/v2/reference/news"
            params = {
                "ticker": symbol.upper(),
                "limit": limit,
                "order": "desc",
                "apiKey": self.api_key,
            }

            async with session.get(url, params=params, timeout=10) as response:
                if response.status != 200:
                    logger.error(f"Failed to fetch news for {symbol}: HTTP {response.status}")
                    raise ValueError(f"Failed to fetch news for {symbol}: HTTP {response.status}")

                data = await response.json()
                results = data.get("results", [])

                if not results:
                    logger.warning(f"No news articles available for {symbol}")
                    return []  # Return empty list for news - this is acceptable

                news_items = []
                for item in results[:limit]:
                    news_items.append(
                        {
                            "title": item.get("title", ""),
                            "url": item.get("article_url", ""),
                            "summary": item.get("description", ""),
                            "source": item.get("publisher", {}).get("name", "Unknown"),
                            "published_at": item.get("published_utc", ""),
                            "image_url": item.get("image_url", ""),
                        }
                    )

                return news_items

        except (APIKeyNotConfiguredError, ValueError):
            raise
        except Exception as e:
            logger.error(f"Error fetching news for {symbol}: {e}")
            raise ValueError(f"Failed to fetch news for {symbol}: {str(e)}")


# Singleton instance
financial_data_service = FinancialDataService()
