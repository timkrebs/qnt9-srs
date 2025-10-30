"""
External API clients for stock data retrieval
Implements Yahoo Finance and Alpha Vantage integration with rate limiting
"""
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import yfinance as yf
from alpha_vantage.fundamentaldata import FundamentalData
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class RateLimiter:
    """Simple in-memory rate limiter"""

    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: List[datetime] = []

    def is_allowed(self) -> bool:
        """Check if request is allowed under rate limit"""
        now = datetime.utcnow()
        # Remove requests outside the current window
        self.requests = [
            req for req in self.requests if now - req < timedelta(seconds=self.window_seconds)
        ]

        if len(self.requests) >= self.max_requests:
            return False

        self.requests.append(now)
        return True

    def wait_time(self) -> float:
        """Calculate seconds to wait before next request is allowed"""
        if not self.requests:
            return 0.0

        now = datetime.utcnow()
        oldest = self.requests[0]
        window_end = oldest + timedelta(seconds=self.window_seconds)

        if now >= window_end:
            return 0.0

        return (window_end - now).total_seconds()


class YahooFinanceClient:
    """
    Yahoo Finance API client with rate limiting
    Rate limit: 5 requests per second
    """

    def __init__(self):
        self.rate_limiter = RateLimiter(max_requests=5, window_seconds=1)
        self.timeout = 2.0  # 2 second timeout per requirement

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=4))
    def search_by_isin(self, isin: str) -> Optional[Dict[str, Any]]:
        """
        Search for stock by ISIN using Yahoo Finance

        Args:
            isin: International Securities Identification Number (12 chars)

        Returns:
            Dictionary with stock data or None if not found
        """
        if not self.rate_limiter.is_allowed():
            wait = self.rate_limiter.wait_time()
            logger.warning(f"Yahoo Finance rate limit reached. Waiting {wait:.2f}s")
            import time

            time.sleep(wait)

        try:
            logger.info(f"Searching Yahoo Finance for ISIN: {isin}")
            # Yahoo Finance doesn't directly support ISIN search,
            # so we need to convert ISIN to ticker symbol first
            ticker = self._convert_isin_to_ticker(isin)
            if not ticker:
                logger.warning(f"Could not convert ISIN {isin} to ticker symbol")
                return None

            return self._get_stock_data(ticker)

        except Exception as e:
            logger.error(f"Error searching Yahoo Finance for ISIN {isin}: {e}")
            return None

    def search_by_symbol(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Search for stock by ticker symbol

        Args:
            symbol: Stock ticker symbol

        Returns:
            Dictionary with stock data or None if not found
        """
        if not self.rate_limiter.is_allowed():
            wait = self.rate_limiter.wait_time()
            logger.warning(f"Yahoo Finance rate limit reached. Waiting {wait:.2f}s")
            import time

            time.sleep(wait)

        try:
            logger.info(f"Searching Yahoo Finance for symbol: {symbol}")
            return self._get_stock_data(symbol)

        except Exception as e:
            logger.error(f"Error searching Yahoo Finance for symbol {symbol}: {e}")
            return None

    def _get_stock_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve stock data from Yahoo Finance

        Args:
            symbol: Stock ticker symbol

        Returns:
            Dictionary with stock data
        """
        try:
            stock = yf.Ticker(symbol)
            info = stock.info

            # Check if stock exists and has valid data
            if not info or "symbol" not in info:
                return None

            return {
                "symbol": info.get("symbol", symbol),
                "name": info.get("longName", info.get("shortName", "")),
                "current_price": info.get("currentPrice", info.get("regularMarketPrice")),
                "currency": info.get("currency"),
                "exchange": info.get("exchange"),
                "market_cap": info.get("marketCap"),
                "sector": info.get("sector"),
                "industry": info.get("industry"),
                "isin": info.get("isin"),
                "source": "yahoo",
                "raw_data": info,
            }

        except Exception as e:
            logger.error(f"Error retrieving stock data for {symbol}: {e}")
            return None

    def _convert_isin_to_ticker(self, isin: str) -> Optional[str]:
        """
        Attempt to convert ISIN to ticker symbol
        Note: This is a simplified implementation. Production would need a mapping database.

        Args:
            isin: ISIN code

        Returns:
            Ticker symbol or None
        """
        # For now, try to use yfinance search
        try:
            # Try searching directly with ISIN
            stock = yf.Ticker(isin)
            info = stock.info
            if info and "symbol" in info:
                return info["symbol"]
        except Exception:
            pass

        return None


class AlphaVantageClient:
    """
    Alpha Vantage API client with rate limiting
    Rate limit: 5 requests per minute (free tier)
    """

    def __init__(self):
        self.api_key = os.getenv("ALPHA_VANTAGE_API_KEY", "demo")
        if self.api_key == "demo":
            logger.warning("Using Alpha Vantage demo API key. Rate limits apply.")

        self.rate_limiter = RateLimiter(max_requests=5, window_seconds=60)
        self.fd = FundamentalData(key=self.api_key, output_format="json")
        self.timeout = 2.0

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=8))
    def search_by_symbol(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Search for stock by ticker symbol using Alpha Vantage

        Args:
            symbol: Stock ticker symbol

        Returns:
            Dictionary with stock data or None if not found
        """
        if not self.rate_limiter.is_allowed():
            wait = self.rate_limiter.wait_time()
            logger.warning(f"Alpha Vantage rate limit reached. Waiting {wait:.2f}s")
            import time

            time.sleep(wait)

        try:
            logger.info(f"Searching Alpha Vantage for symbol: {symbol}")

            # Get company overview
            data, _ = self.fd.get_company_overview(symbol)

            if not data or "Symbol" not in data:
                return None

            return {
                "symbol": data.get("Symbol"),
                "name": data.get("Name"),
                "exchange": data.get("Exchange"),
                "currency": data.get("Currency"),
                "sector": data.get("Sector"),
                "industry": data.get("Industry"),
                "market_cap": self._parse_number(data.get("MarketCapitalization")),
                "source": "alphavantage",
                "raw_data": data,
            }

        except Exception as e:
            logger.error(f"Error searching Alpha Vantage for symbol {symbol}: {e}")
            return None

    def _parse_number(self, value: Optional[str]) -> Optional[float]:
        """Parse numeric string to float"""
        if not value or value == "None":
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None


class StockAPIClient:
    """
    Unified client for stock data retrieval
    Attempts Yahoo Finance first, falls back to Alpha Vantage
    """

    def __init__(self):
        self.yahoo = YahooFinanceClient()
        self.alpha_vantage = AlphaVantageClient()

    def search_stock(self, query: str, query_type: str = "symbol") -> Optional[Dict[str, Any]]:
        """
        Search for stock using available APIs

        Args:
            query: ISIN, WKN, or symbol to search
            query_type: Type of query ('isin', 'wkn', or 'symbol')

        Returns:
            Dictionary with stock data or None if not found
        """
        # Try Yahoo Finance first
        if query_type == "isin":
            result = self.yahoo.search_by_isin(query)
        else:
            result = self.yahoo.search_by_symbol(query)

        if result:
            return result

        # Fallback to Alpha Vantage
        logger.info("Yahoo Finance returned no results, trying Alpha Vantage...")
        if query_type != "isin":  # Alpha Vantage doesn't support ISIN directly
            result = self.alpha_vantage.search_by_symbol(query)

        return result
