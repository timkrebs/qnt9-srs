"""
Financial Data Service for real-time stock data integration using Polygon.io API.

Provides:
- Real-time stock quotes
- Intraday price data for charts
- Company news feed
- Market statistics
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import aiohttp

logger = logging.getLogger(__name__)


class FinancialDataService:
    """Service for fetching real-time financial data from Massive API (formerly Polygon.io)."""

    def __init__(self):
        """Initialize the financial data service."""
        self.api_key = os.getenv("MASSIVE_API_KEY", "")
        self.base_url = "https://api.polygon.io"
        self.session: Optional[aiohttp.ClientSession] = None

        if not self.api_key:
            logger.warning("MASSIVE_API_KEY not set, using mock data")

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
        """
        if not self.api_key:
            return self._get_mock_quote(symbol)

        try:
            # Get previous day's close for comparison
            prev_close_data = await self._get_previous_close(symbol)
            if not prev_close_data:
                return self._get_mock_quote(symbol)

            # Get current snapshot for real-time data
            snapshot_data = await self._get_snapshot(symbol)

            if snapshot_data:
                current_price = snapshot_data.get("last", {}).get("price", 0)
                prev_close = prev_close_data.get("close", current_price)
                change = current_price - prev_close
                change_percent = (change / prev_close * 100) if prev_close != 0 else 0

                return {
                    "symbol": symbol.upper(),
                    "price": round(current_price, 2),
                    "change": round(change, 2),
                    "change_percent": f"{change_percent:.2f}",
                    "volume": snapshot_data.get("day", {}).get("volume", 0),
                    "open": snapshot_data.get("day", {}).get("open", 0),
                    "high": snapshot_data.get("day", {}).get("high", 0),
                    "low": snapshot_data.get("day", {}).get("low", 0),
                    "previous_close": prev_close,
                    "market_cap": snapshot_data.get("market_cap", 0),
                    "timestamp": datetime.utcnow().isoformat(),
                }
            else:
                return self._get_mock_quote(symbol)

        except Exception as e:
            logger.error(f"Error fetching quote for {symbol}: {e}")
            return self._get_mock_quote(symbol)

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

    def _get_mock_quote(self, symbol: str) -> Dict[str, Any]:
        """Return mock data for development/testing."""
        import random

        base_price = random.uniform(50, 500)
        change = random.uniform(-10, 10)
        prev_close = base_price - change

        return {
            "symbol": symbol.upper(),
            "price": round(base_price, 2),
            "change": round(change, 2),
            "change_percent": f"{(change/prev_close*100):.2f}",
            "volume": random.randint(1000000, 50000000),
            "open": round(prev_close + random.uniform(-2, 2), 2),
            "high": round(base_price + abs(change), 2),
            "low": round(base_price - abs(change) * 1.5, 2),
            "previous_close": round(prev_close, 2),
            "market_cap": random.randint(10, 3000) * 1000000000,
            "timestamp": datetime.utcnow().isoformat(),
        }

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
        """
        if not self.api_key:
            return await self._get_mock_intraday(symbol)

        try:
            # Get data for last trading day
            to_date = datetime.utcnow()
            from_date = to_date - timedelta(days=1)

            session = await self.get_session()
            url = f"{self.base_url}/v2/aggs/ticker/{symbol.upper()}/range/{multiplier}/{timespan}/{from_date.strftime('%Y-%m-%d')}/{to_date.strftime('%Y-%m-%d')}"
            params = {"adjusted": "true", "sort": "asc", "apiKey": self.api_key}

            async with session.get(url, params=params, timeout=10) as response:
                if response.status != 200:
                    logger.warning(f"Failed to fetch intraday data: {response.status}")
                    return await self._get_mock_intraday(symbol)

                data = await response.json()
                results = data.get("results", [])

                if not results:
                    return await self._get_mock_intraday(symbol)

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

        except Exception as e:
            logger.error(f"Error fetching intraday data for {symbol}: {e}")
            return await self._get_mock_intraday(symbol)

    async def _get_mock_intraday(self, symbol: str) -> List[Dict[str, Any]]:
        """Generate mock intraday data for testing."""
        import random

        data = []
        base_price = random.uniform(100, 500)
        now = datetime.utcnow()

        for i in range(78):  # 6.5 hours of 5-minute intervals
            timestamp = now - timedelta(minutes=5 * (78 - i))
            price_change = random.uniform(-2, 2)
            open_price = base_price
            close_price = base_price + price_change

            data.append(
                {
                    "timestamp": timestamp.isoformat(),
                    "open": round(open_price, 2),
                    "high": round(max(open_price, close_price) + random.uniform(0, 1), 2),
                    "low": round(min(open_price, close_price) - random.uniform(0, 1), 2),
                    "close": round(close_price, 2),
                    "volume": random.randint(10000, 100000),
                }
            )

            base_price = close_price

        return data

    async def get_company_news(self, symbol: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Fetch latest news for a company.

        Args:
            symbol: Stock ticker symbol
            limit: Maximum number of news items to return

        Returns:
            List of news articles with title, url, summary, etc.
        """
        if not self.api_key:
            return self._get_mock_news(symbol, limit)

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
                    return self._get_mock_news(symbol, limit)

                data = await response.json()
                results = data.get("results", [])

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

        except Exception as e:
            logger.error(f"Error fetching news for {symbol}: {e}")
            return self._get_mock_news(symbol, limit)

    def _get_mock_news(self, symbol: str, limit: int) -> List[Dict[str, Any]]:
        """Generate mock news data."""
        news = []
        sources = ["Financial Times", "Bloomberg", "Reuters", "CNBC", "Wall Street Journal"]

        for i in range(limit):
            news.append(
                {
                    "title": f"{symbol} Stock Analysis: Key Market Developments {i+1}",
                    "url": f"https://example.com/news/{symbol.lower()}-{i+1}",
                    "summary": f"Latest market analysis and insights on {symbol} stock performance, including expert opinions and technical indicators.",
                    "source": sources[i % len(sources)],
                    "published_at": (datetime.utcnow() - timedelta(hours=i * 2)).isoformat(),
                    "image_url": "",
                }
            )
        return news


# Singleton instance
financial_data_service = FinancialDataService()
