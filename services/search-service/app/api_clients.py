"""
External API clients for stock data retrieval.

This module implements Yahoo Finance and Alpha Vantage integration with
rate limiting, retry logic, and automatic fallback mechanisms.
"""

import logging
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import yfinance as yf
from alpha_vantage.fundamentaldata import FundamentalData
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

# Rate limiting constants
YAHOO_MAX_REQUESTS = 5
YAHOO_WINDOW_SECONDS = 1
ALPHA_VANTAGE_MAX_REQUESTS = 5
ALPHA_VANTAGE_WINDOW_SECONDS = 60

# API timeout constants
DEFAULT_TIMEOUT_SECONDS = 2.0

# Retry constants
MAX_RETRY_ATTEMPTS = 3
RETRY_MIN_WAIT_SECONDS = 1
RETRY_MAX_WAIT_SECONDS = 4
ALPHA_VANTAGE_RETRY_MIN_SECONDS = 2
ALPHA_VANTAGE_RETRY_MAX_SECONDS = 8

# Ticker search constants
MAX_TICKER_CANDIDATES = 50
MIN_TICKER_LENGTH = 1
MAX_TICKER_ABBREVIATION_LENGTH = 4
TICKER_PREFIX_LENGTH_MIN = 3
TICKER_PREFIX_LENGTH_MAX = 4

# API response validation
MIN_COMPANY_NAME_LENGTH = 1
VALID_QUOTE_TYPES = {"EQUITY", "ETF"}

# Company name to ticker symbol mappings for popular stocks
COMPANY_TICKER_MAPPINGS = {
    "APPLE": ["AAPL"],
    "AMAZON": ["AMZN"],
    "MICROSOFT": ["MSFT"],
    "GOOGLE": ["GOOGL", "GOOG"],
    "ALPHABET": ["GOOGL", "GOOG"],
    "FACEBOOK": ["META"],
    "META": ["META"],
    "TESLA": ["TSLA"],
    "NVIDIA": ["NVDA"],
    "NETFLIX": ["NFLX"],
    "INTEL": ["INTC"],
    "AMD": ["AMD"],
    "CISCO": ["CSCO"],
    "ORACLE": ["ORCL"],
    "IBM": ["IBM"],
    "SAP": ["SAP"],
    "SIEMENS": ["SIE.DE", "SIEGY"],
    "VOLKSWAGEN": ["VOW.DE", "VOW3.DE", "VWAGY"],
    "BMW": ["BMW.DE", "BMWYY"],
    "MERCEDES": ["MBG.DE", "DDAIF"],
    "DAIMLER": ["MBG.DE", "DDAIF"],
    "BAYER": ["BAYN.DE", "BAYRY"],
    "BASF": ["BAS.DE", "BASFY"],
    "ALLIANZ": ["ALV.DE", "ALIZF"],
    "DEUTSCHE BANK": ["DBK.DE", "DB"],
    "LUFTHANSA": ["LHA.DE", "DLAKY"],
    "ADIDAS": ["ADS.DE", "ADDYY"],
}


class RateLimiter:
    """
    In-memory rate limiter for API requests.

    Implements a sliding window rate limiting algorithm to prevent
    exceeding API rate limits.

    Attributes:
        max_requests: Maximum number of requests allowed per window
        window_seconds: Time window duration in seconds
        requests: List of request timestamps within current window
    """

    def __init__(self, max_requests: int, window_seconds: int):
        """
        Initialize rate limiter.

        Args:
            max_requests: Maximum requests allowed per window
            window_seconds: Duration of rate limit window in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: List[datetime] = []

    def is_allowed(self) -> bool:
        """
        Check if request is allowed under current rate limit.

        Automatically removes requests outside the current window
        and adds current request if allowed.

        Returns:
            True if request is allowed, False if rate limit exceeded
        """
        now = datetime.now(timezone.utc)
        self._cleanup_old_requests(now)

        if len(self.requests) >= self.max_requests:
            return False

        self.requests.append(now)
        return True

    def wait_time(self) -> float:
        """
        Calculate seconds to wait before next request is allowed.

        Returns:
            Seconds to wait (0.0 if request would be allowed now)
        """
        if not self.requests:
            return 0.0

        now = datetime.now(timezone.utc)
        oldest = self.requests[0]
        window_end = oldest + timedelta(seconds=self.window_seconds)

        if now >= window_end:
            return 0.0

        return (window_end - now).total_seconds()

    def _cleanup_old_requests(self, now: datetime) -> None:
        """
        Remove requests outside the current time window.

        Args:
            now: Current timestamp
        """
        cutoff_time = now - timedelta(seconds=self.window_seconds)
        self.requests = [req for req in self.requests if req > cutoff_time]


class YahooFinanceClient:
    """
    Yahoo Finance API client with rate limiting and retry logic.

    Implements automatic retries with exponential backoff and enforces
    rate limit of 5 requests per second.

    Attributes:
        rate_limiter: Rate limiter instance
        timeout: Request timeout in seconds
    """

    def __init__(self):
        """Initialize Yahoo Finance client with rate limiting."""
        self.rate_limiter = RateLimiter(
            max_requests=YAHOO_MAX_REQUESTS, window_seconds=YAHOO_WINDOW_SECONDS
        )
        self.timeout = DEFAULT_TIMEOUT_SECONDS

    @retry(
        stop=stop_after_attempt(MAX_RETRY_ATTEMPTS),
        wait=wait_exponential(multiplier=1, min=RETRY_MIN_WAIT_SECONDS, max=RETRY_MAX_WAIT_SECONDS),
    )
    def search_by_isin(self, isin: str) -> Optional[Dict[str, Any]]:
        """
        Search for stock by ISIN using Yahoo Finance.

        Note: Yahoo Finance doesn't directly support ISIN search, so this
        method attempts to convert ISIN to ticker symbol first.

        Args:
            isin: International Securities Identification Number (12 characters)

        Returns:
            Stock data dictionary or None if not found
        """
        self._wait_for_rate_limit()

        try:
            logger.info(f"Searching Yahoo Finance for ISIN: {isin}")
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
        Search for stock by ticker symbol.

        Args:
            symbol: Stock ticker symbol

        Returns:
            Stock data dictionary or None if not found
        """
        self._wait_for_rate_limit()

        try:
            logger.info(f"Searching Yahoo Finance for symbol: {symbol}")
            return self._get_stock_data(symbol)

        except Exception as e:
            logger.error(f"Error searching Yahoo Finance for symbol {symbol}: {e}")
            return None

    def search_by_name(self, query: str, limit: int = 10) -> list[Dict[str, Any]]:
        """
        Search for stocks by company name using Yahoo Finance API.

        Uses yfinance library's Ticker search functionality to find stocks
        matching the company name query. This is more reliable than the
        web API which has strict rate limits.

        Strategy:
        1. Generate potential ticker symbols from company name
        2. Fetch stock info for each candidate ticker
        3. Validate that company name matches the query
        4. Return matching results up to the limit

        Args:
            query: Company name to search for
            limit: Maximum number of results to return (default: 10)

        Returns:
            List of stock data dictionaries matching the search query
        """
        self._wait_for_rate_limit()

        try:
            logger.info(f"Searching Yahoo Finance for company name: {query}")

            results = []
            potential_tickers = self._generate_ticker_candidates(query)

            for ticker_symbol in potential_tickers[:limit]:
                result = self._try_fetch_ticker(ticker_symbol, query)
                if result:
                    results.append(result)

                    if len(results) >= limit:
                        break

            logger.info(f"Yahoo Finance name search for '{query}' returned {len(results)} results")
            return results

        except Exception as e:
            logger.error(f"Error searching Yahoo Finance by name: {e}")
            return []

    def _try_fetch_ticker(self, ticker_symbol: str, query: str) -> Optional[Dict[str, Any]]:
        """
        Try to fetch and validate ticker information.

        Args:
            ticker_symbol: Ticker symbol to fetch
            query: Original company name query for validation

        Returns:
            Stock data dictionary if valid match, None otherwise
        """
        try:
            ticker = yf.Ticker(ticker_symbol)
            info = ticker.info

            company_name = info.get("longName", "")
            short_name = info.get("shortName", "")

            if not self._has_valid_name(company_name, short_name):
                return None

            if not self._matches_query(query, company_name, short_name):
                return None

            return {
                "symbol": ticker_symbol,
                "name": company_name or short_name,
                "exchange": info.get("exchange", ""),
                "quote_type": info.get("quoteType", "EQUITY"),
                "source": "yfinance_ticker",
            }

        except Exception as e:
            logger.debug(f"Could not fetch info for ticker {ticker_symbol}: {e}")
            return None

    def _has_valid_name(self, company_name: str, short_name: str) -> bool:
        """
        Check if company has at least one valid name.

        Args:
            company_name: Long company name
            short_name: Short company name

        Returns:
            True if at least one name is valid
        """
        return bool(company_name or short_name)

    def _matches_query(self, query: str, company_name: str, short_name: str) -> bool:
        """
        Check if company name matches the search query.

        Args:
            query: Original search query
            company_name: Long company name
            short_name: Short company name

        Returns:
            True if query matches either name
        """
        query_lower = query.lower()
        name_lower = company_name.lower()
        short_lower = short_name.lower()

        return (
            query_lower in name_lower
            or query_lower in short_lower
            or name_lower.startswith(query_lower)
            or short_lower.startswith(query_lower)
        )

    def _generate_ticker_candidates(self, query: str) -> list[str]:
        """
        Generate potential ticker symbols from company name.

        Uses multiple strategies to generate potential ticker symbols:
        1. Direct ticker match
        2. Known company-to-ticker mappings
        3. Abbreviation from first letters
        4. Common prefix patterns (3-4 characters)

        Args:
            query: Company name or partial name

        Returns:
            List of unique potential ticker symbols in priority order
        """
        if not query or len(query) < MIN_TICKER_LENGTH:
            return []

        candidates = []
        query_upper = query.upper()

        # Strategy 1: Direct match (e.g., "AAPL" -> "AAPL")
        candidates.append(query_upper)

        # Strategy 2: Known mappings for popular companies
        candidates.extend(self._get_mapped_tickers(query_upper))

        # Strategy 3: Abbreviation from first letters of words
        abbreviation = self._create_abbreviation(query_upper)
        if abbreviation:
            candidates.append(abbreviation)

        # Strategy 4: Common prefix patterns (3-4 characters)
        candidates.extend(self._get_prefix_candidates(query_upper))

        # Remove duplicates while preserving order
        return self._remove_duplicates(candidates)

    def _get_mapped_tickers(self, query_upper: str) -> list[str]:
        """
        Get ticker symbols from known company name mappings.

        Args:
            query_upper: Uppercase company name query

        Returns:
            List of ticker symbols from mappings
        """
        mapped_tickers = []
        for company_name, tickers in COMPANY_TICKER_MAPPINGS.items():
            if company_name in query_upper or query_upper in company_name:
                mapped_tickers.extend(tickers)
        return mapped_tickers

    def _create_abbreviation(self, query_upper: str) -> Optional[str]:
        """
        Create ticker abbreviation from first letters of words.

        Args:
            query_upper: Uppercase company name query

        Returns:
            Abbreviation string or None if single word

        Examples:
            "DEUTSCHE BANK" -> "DB"
            "SAP" -> None (single word)
        """
        words = query_upper.split()
        if len(words) > 1:
            return "".join(word[0] for word in words if word)
        return None

    def _get_prefix_candidates(self, query_upper: str) -> list[str]:
        """
        Generate ticker candidates from common prefix patterns.

        Args:
            query_upper: Uppercase company name query

        Returns:
            List of prefix-based ticker candidates
        """
        prefixes = []
        if len(query_upper) >= TICKER_PREFIX_LENGTH_MIN:
            prefixes.append(query_upper[:TICKER_PREFIX_LENGTH_MIN])
        if len(query_upper) >= TICKER_PREFIX_LENGTH_MAX:
            prefixes.append(query_upper[:TICKER_PREFIX_LENGTH_MAX])
        return prefixes

    def _remove_duplicates(self, items: list[str]) -> list[str]:
        """
        Remove duplicate items while preserving order.

        Args:
            items: List with potential duplicates

        Returns:
            List with duplicates removed, order preserved
        """
        seen = set()
        unique_items = []
        for item in items:
            if item and item not in seen:
                seen.add(item)
                unique_items.append(item)
        return unique_items

    def _wait_for_rate_limit(self) -> None:
        """Wait if rate limit has been exceeded."""
        if not self.rate_limiter.is_allowed():
            wait = self.rate_limiter.wait_time()
            logger.warning(f"Yahoo Finance rate limit reached. Waiting {wait:.2f}s")
            time.sleep(wait)

    def _get_stock_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve stock data from Yahoo Finance.

        Args:
            symbol: Stock ticker symbol

        Returns:
            Dictionary with stock data or None if not found
        """
        try:
            stock = yf.Ticker(symbol)
            info = stock.info

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
        Attempt to convert ISIN to ticker symbol.

        Note: This is a simplified implementation. Production systems
        would need a mapping database or dedicated ISIN lookup service.

        Args:
            isin: ISIN code

        Returns:
            Ticker symbol or None if conversion fails
        """
        try:
            stock = yf.Ticker(isin)
            info = stock.info
            if info and "symbol" in info:
                return info["symbol"]
        except Exception:
            pass

        return None


class AlphaVantageClient:
    """
    Alpha Vantage API client with rate limiting.

    Implements free tier rate limit of 5 requests per minute with
    automatic retry logic and exponential backoff.

    Attributes:
        api_key: Alpha Vantage API key
        rate_limiter: Rate limiter instance
        fd: FundamentalData client instance
        timeout: Request timeout in seconds
    """

    def __init__(self):
        """Initialize Alpha Vantage client with rate limiting."""
        self.api_key = os.getenv("ALPHA_VANTAGE_API_KEY", "demo")
        if self.api_key == "demo":
            logger.warning("Using Alpha Vantage demo API key. Rate limits apply.")

        self.rate_limiter = RateLimiter(
            max_requests=ALPHA_VANTAGE_MAX_REQUESTS,
            window_seconds=ALPHA_VANTAGE_WINDOW_SECONDS,
        )
        self.fd = FundamentalData(key=self.api_key, output_format="json")
        self.timeout = DEFAULT_TIMEOUT_SECONDS

    @retry(
        stop=stop_after_attempt(MAX_RETRY_ATTEMPTS),
        wait=wait_exponential(
            multiplier=1, min=ALPHA_VANTAGE_RETRY_MIN_SECONDS, max=ALPHA_VANTAGE_RETRY_MAX_SECONDS
        ),
    )
    def search_by_symbol(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Search for stock by ticker symbol using Alpha Vantage.

        Args:
            symbol: Stock ticker symbol

        Returns:
            Stock data dictionary or None if not found
        """
        self._wait_for_rate_limit()

        try:
            logger.info(f"Searching Alpha Vantage for symbol: {symbol}")

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

    def _wait_for_rate_limit(self) -> None:
        """Wait if rate limit has been exceeded."""
        if not self.rate_limiter.is_allowed():
            wait = self.rate_limiter.wait_time()
            logger.warning(f"Alpha Vantage rate limit reached. Waiting {wait:.2f}s")
            time.sleep(wait)

    def _parse_number(self, value: Optional[str]) -> Optional[float]:
        """
        Parse numeric string to float.

        Args:
            value: String representation of number

        Returns:
            Parsed float value or None if parsing fails
        """
        if not value or value == "None":
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None


class StockAPIClient:
    """
    Unified client for stock data retrieval with automatic fallback.

    Attempts Yahoo Finance first (faster, more comprehensive data),
    then falls back to Alpha Vantage if Yahoo fails.

    Attributes:
        yahoo: Yahoo Finance client instance
        alpha_vantage: Alpha Vantage client instance
    """

    def __init__(self):
        """Initialize unified stock API client."""
        self.yahoo = YahooFinanceClient()
        self.alpha_vantage = AlphaVantageClient()

    def search_stock(self, query: str, query_type: str = "symbol") -> Optional[Dict[str, Any]]:
        """
        Search for stock using available APIs with automatic fallback.

        Strategy:
        1. Try Yahoo Finance (primary source)
        2. If Yahoo fails, try Alpha Vantage (fallback)

        Note: Alpha Vantage doesn't support ISIN search directly.

        Args:
            query: ISIN, WKN, or symbol to search
            query_type: Type of query ('isin', 'wkn', or 'symbol')

        Returns:
            Stock data dictionary or None if not found in any source
        """
        result = self._search_yahoo(query, query_type)
        if result:
            return result

        if query_type != "isin":
            logger.info("Yahoo Finance returned no results, trying Alpha Vantage...")
            result = self.alpha_vantage.search_by_symbol(query)

        return result

    def _search_yahoo(self, query: str, query_type: str) -> Optional[Dict[str, Any]]:
        """
        Search Yahoo Finance based on query type.

        Args:
            query: Search query
            query_type: Type of query ('isin', 'wkn', or 'symbol')

        Returns:
            Stock data dictionary or None
        """
        if query_type == "isin":
            return self.yahoo.search_by_isin(query)
        else:
            return self.yahoo.search_by_symbol(query)

    def search_by_name(self, query: str, limit: int = 10) -> list[Dict[str, Any]]:
        """
        Search for stocks by company name.

        Uses Yahoo Finance search functionality to find stocks matching
        the company name query. Returns basic search results that can be
        enriched with full stock data if needed.

        Args:
            query: Company name to search for
            limit: Maximum number of results to return (default: 10)

        Returns:
            List of stock data dictionaries matching the search query
        """
        try:
            logger.info(f"Searching for company name: {query}")

            # Use Yahoo Finance search (primary source)
            results = self.yahoo.search_by_name(query, limit=limit)

            if results:
                logger.info(f"Found {len(results)} results from Yahoo Finance")
            else:
                logger.info("No results found from Yahoo Finance")

            return results

        except Exception as e:
            logger.error(f"Error searching by name: {e}")
            return []

    def enrich_search_result(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Enrich a search result with full stock data.

        Takes a symbol from a search result and fetches complete
        stock information including price, market cap, etc.

        Args:
            symbol: Stock ticker symbol to enrich

        Returns:
            Complete stock data dictionary or None if not found
        """
        try:
            return self.search_stock(symbol, query_type="symbol")
        except Exception as e:
            logger.error(f"Error enriching search result for {symbol}: {e}")
            return None
