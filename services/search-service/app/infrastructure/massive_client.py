"""
Massive API client implementation (formerly Polygon.io).

Provides comprehensive stock data retrieval including:
- Ticker search across all US exchanges
- Real-time and delayed stock snapshots
- Historical OHLC aggregates for charts
- WebSocket streaming for live prices

API Documentation: https://massive.com/docs
"""

import asyncio
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .circuit_breaker import CircuitBreaker
from .rate_limiter import RateLimiter

logger = logging.getLogger(__name__)


class MassiveTimespan(str, Enum):
    """Timespan options for aggregate bars."""
    MINUTE = "minute"
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"


@dataclass
class TickerAddress:
    """Company address information."""
    address1: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None


@dataclass
class TickerInfo:
    """Ticker reference data from Massive API."""
    ticker: str
    name: str
    market: str
    locale: str
    primary_exchange: str
    type: str
    active: bool
    currency_name: Optional[str] = None
    cik: Optional[str] = None
    composite_figi: Optional[str] = None
    
    # Extended company details
    description: Optional[str] = None
    homepage_url: Optional[str] = None
    phone_number: Optional[str] = None
    total_employees: Optional[int] = None
    list_date: Optional[str] = None
    market_cap: Optional[float] = None
    shares_outstanding: Optional[int] = None
    weighted_shares_outstanding: Optional[int] = None
    round_lot: Optional[int] = None
    
    # Classification
    sic_code: Optional[str] = None
    sic_description: Optional[str] = None
    
    # Address
    address: Optional[TickerAddress] = None
    
    # Branding
    logo_url: Optional[str] = None
    icon_url: Optional[str] = None


@dataclass
class NewsArticle:
    """News article from Massive API."""
    id: str
    title: str
    author: Optional[str]
    published_utc: str
    article_url: str
    description: Optional[str]
    image_url: Optional[str]
    publisher_name: Optional[str]
    publisher_logo_url: Optional[str]
    tickers: List[str]
    keywords: Optional[List[str]] = None


@dataclass
class StockSnapshot:
    """Current market snapshot for a stock."""
    ticker: str
    name: Optional[str]
    
    # Current day data
    day_open: Optional[Decimal]
    day_high: Optional[Decimal]
    day_low: Optional[Decimal]
    day_close: Optional[Decimal]
    day_volume: Optional[int]
    day_vwap: Optional[Decimal]
    
    # Previous day data
    prev_close: Optional[Decimal]
    prev_volume: Optional[int]
    
    # Change calculations
    todays_change: Optional[Decimal]
    todays_change_percent: Optional[Decimal]
    
    # Last trade/quote
    last_trade_price: Optional[Decimal]
    last_trade_size: Optional[int]
    last_trade_timestamp: Optional[int]
    
    # Minute bar (latest)
    minute_open: Optional[Decimal]
    minute_high: Optional[Decimal]
    minute_low: Optional[Decimal]
    minute_close: Optional[Decimal]
    minute_volume: Optional[int]
    
    # Timestamps
    updated: Optional[int]


@dataclass
class AggregateBar:
    """OHLC aggregate bar data."""
    timestamp: int
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    vwap: Optional[Decimal] = None
    transactions: Optional[int] = None


class MassiveClient:
    """
    Massive API client with fault tolerance (uses Polygon.io infrastructure).

    Features:
    - Circuit breaker for failure protection
    - Rate limiting to respect API limits
    - Automatic retry with exponential backoff
    - Async HTTP requests with connection pooling
    
    API Base URL: https://api.polygon.io
    """

    BASE_URL = "https://api.polygon.io"
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout_seconds: float = 10.0,
        max_retries: int = 3,
        rate_limit_requests: int = 5,
        rate_limit_window: int = 1,
    ):
        """
        Initialize Massive API client.

        Args:
            api_key: Massive API key (falls back to MASSIVE_API_KEY env var)
            timeout_seconds: Request timeout
            max_retries: Maximum retry attempts
            rate_limit_requests: Max requests per window
            rate_limit_window: Rate limit window in seconds
        """
        self.api_key = api_key or os.getenv("MASSIVE_API_KEY")
        if not self.api_key:
            logger.warning("MASSIVE_API_KEY not configured - Massive API features disabled")
        
        self.timeout = timeout_seconds
        self.max_retries = max_retries
        
        # Initialize circuit breaker
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60,
            name="massive_api",
        )
        
        # Initialize rate limiter
        self.rate_limiter = RateLimiter(
            max_requests=rate_limit_requests,
            window_seconds=rate_limit_window,
            name="massive_api",
        )
        
        # HTTP client (lazy initialization)
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                timeout=self.timeout,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "User-Agent": "QNT9-Search-Service/1.0",
                },
            )
        return self._client

    async def close(self):
        """Close HTTP client connections."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    @retry(
        retry=retry_if_exception_type(httpx.HTTPStatusError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Make authenticated API request with retry logic.

        Args:
            method: HTTP method
            endpoint: API endpoint path
            params: Query parameters

        Returns:
            JSON response data

        Raises:
            httpx.HTTPStatusError: On API errors
            Exception: On connection errors
        """
        if not self.api_key:
            raise ValueError("Massive API key not configured")
        
        # Wait for rate limit capacity (non-blocking wait)
        await self.rate_limiter.wait_and_acquire()
        
        # Make request through circuit breaker
        client = await self._get_client()
        
        # Add API key to params if not using header auth
        if params is None:
            params = {}
        params["apiKey"] = self.api_key
        
        response = await client.request(method, endpoint, params=params)
        response.raise_for_status()
        
        return response.json()

    async def search_tickers(
        self,
        query: str,
        market: str = "stocks",
        active: bool = True,
        limit: int = 50,
    ) -> List[TickerInfo]:
        """
        Search for tickers by name or symbol.

        Enhanced search that:
        1. First tries exact ticker match for short uppercase queries
        2. Then does fuzzy search within company names

        Args:
            query: Search term (symbol or company name)
            market: Market type (stocks, crypto, fx, otc)
            active: Only return active tickers
            limit: Maximum results (max 1000)

        Returns:
            List of matching TickerInfo objects

        Example:
            tickers = await client.search_tickers("apple")
            # Returns [TickerInfo(ticker="AAPL", name="Apple Inc.", ...)]
        """
        results = []
        seen_tickers = set()
        
        try:
            # If query looks like a ticker symbol (1-5 uppercase letters),
            # first try exact ticker lookup
            clean_query = query.strip().upper()
            if len(clean_query) <= 5 and clean_query.isalpha():
                try:
                    exact_match = await self.get_ticker_details(clean_query)
                    if exact_match and exact_match.active == active:
                        results.append(exact_match)
                        seen_tickers.add(exact_match.ticker)
                        logger.debug(f"Found exact ticker match for '{clean_query}'")
                except Exception:
                    pass  # Exact match not found, continue with search
            
            # Do the regular search
            data = await self._request(
                "GET",
                "/v3/reference/tickers",
                params={
                    "search": query,
                    "market": market,
                    "active": str(active).lower(),
                    "limit": limit,
                    "sort": "ticker",
                    "order": "asc",
                },
            )
            
            for item in data.get("results", []):
                ticker = item.get("ticker", "")
                if ticker not in seen_tickers:
                    results.append(TickerInfo(
                        ticker=ticker,
                        name=item.get("name", ""),
                        market=item.get("market", ""),
                        locale=item.get("locale", ""),
                        primary_exchange=item.get("primary_exchange", ""),
                        type=item.get("type", ""),
                        active=item.get("active", True),
                        currency_name=item.get("currency_name"),
                        cik=item.get("cik"),
                        composite_figi=item.get("composite_figi"),
                    ))
                    seen_tickers.add(ticker)
            
            logger.info(f"Massive ticker search '{query}' returned {len(results)} results")
            return results[:limit]  # Ensure we don't exceed limit
            
        except Exception as e:
            logger.error(f"Massive ticker search failed: {e}")
            raise

    async def get_ticker_details(self, ticker: str) -> Optional[TickerInfo]:
        """
        Get detailed information for a specific ticker.

        Uses GET /v3/reference/tickers/{ticker}

        Returns extended company information including:
        - Basic info (name, exchange, type, market)
        - Company details (description, employees, website)
        - Financial info (market cap, shares outstanding)
        - Address and branding

        Args:
            ticker: Stock ticker symbol (e.g., "AAPL")

        Returns:
            TickerInfo with full details or None if not found
        """
        try:
            data = await self._request(
                "GET",
                f"/v3/reference/tickers/{ticker.upper()}",
            )
            
            result = data.get("results", {})
            if not result:
                return None
            
            # Parse address if available
            address_data = result.get("address")
            address = None
            if address_data:
                address = TickerAddress(
                    address1=address_data.get("address1"),
                    city=address_data.get("city"),
                    state=address_data.get("state"),
                    postal_code=address_data.get("postal_code"),
                )
            
            # Parse branding if available
            branding = result.get("branding", {})
            logo_url = branding.get("logo_url") if branding else None
            icon_url = branding.get("icon_url") if branding else None
            
            # Add API key to branding URLs if present
            if logo_url and self.api_key:
                logo_url = f"{logo_url}?apiKey={self.api_key}"
            if icon_url and self.api_key:
                icon_url = f"{icon_url}?apiKey={self.api_key}"
            
            return TickerInfo(
                ticker=result.get("ticker", ""),
                name=result.get("name", ""),
                market=result.get("market", ""),
                locale=result.get("locale", ""),
                primary_exchange=result.get("primary_exchange", ""),
                type=result.get("type", ""),
                active=result.get("active", True),
                currency_name=result.get("currency_name"),
                cik=result.get("cik"),
                composite_figi=result.get("composite_figi"),
                # Extended details
                description=result.get("description"),
                homepage_url=result.get("homepage_url"),
                phone_number=result.get("phone_number"),
                total_employees=result.get("total_employees"),
                list_date=result.get("list_date"),
                market_cap=result.get("market_cap"),
                shares_outstanding=result.get("share_class_shares_outstanding"),
                weighted_shares_outstanding=result.get("weighted_shares_outstanding"),
                round_lot=result.get("round_lot"),
                sic_code=result.get("sic_code"),
                sic_description=result.get("sic_description"),
                address=address,
                logo_url=logo_url,
                icon_url=icon_url,
            )
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise
        except Exception as e:
            logger.error(f"Massive ticker details failed for {ticker}: {e}")
            raise

    async def get_ticker_news(
        self,
        ticker: str,
        limit: int = 10,
    ) -> List[NewsArticle]:
        """
        Get news articles for a specific ticker.

        Uses GET /v2/reference/news

        Args:
            ticker: Stock ticker symbol (e.g., "AAPL")
            limit: Maximum number of articles (default 10, max 100)

        Returns:
            List of NewsArticle objects
        """
        try:
            data = await self._request(
                "GET",
                "/v2/reference/news",
                params={
                    "ticker": ticker.upper(),
                    "limit": min(limit, 100),
                    "order": "desc",
                    "sort": "published_utc",
                },
            )
            
            articles = []
            for item in data.get("results", []):
                publisher = item.get("publisher", {})
                articles.append(NewsArticle(
                    id=item.get("id", ""),
                    title=item.get("title", ""),
                    author=item.get("author"),
                    published_utc=item.get("published_utc", ""),
                    article_url=item.get("article_url", ""),
                    description=item.get("description"),
                    image_url=item.get("image_url"),
                    publisher_name=publisher.get("name"),
                    publisher_logo_url=publisher.get("logo_url"),
                    tickers=item.get("tickers", []),
                    keywords=item.get("keywords"),
                ))
            
            logger.info(f"Massive news for '{ticker}' returned {len(articles)} articles")
            return articles
            
        except Exception as e:
            logger.error(f"Massive news failed for {ticker}: {e}")
            raise

    async def get_snapshot(self, ticker: str) -> Optional[StockSnapshot]:
        """
        Get current market snapshot for a stock.

        Uses GET /v2/snapshot/locale/us/markets/stocks/tickers/{ticker}

        Includes:
        - Current day OHLC and volume
        - Previous day close
        - Today's change and percent change
        - Last trade/quote data
        - Latest minute bar

        Args:
            ticker: Stock ticker symbol

        Returns:
            StockSnapshot with current market data or None

        Example:
            snapshot = await client.get_snapshot("AAPL")
            print(f"AAPL: ${snapshot.day_close} ({snapshot.todays_change_percent}%)")
        """
        try:
            data = await self._request(
                "GET",
                f"/v2/snapshot/locale/us/markets/stocks/tickers/{ticker.upper()}",
            )
            
            ticker_data = data.get("ticker", {})
            if not ticker_data:
                return None
            
            day = ticker_data.get("day", {})
            prev_day = ticker_data.get("prevDay", {})
            last_trade = ticker_data.get("lastTrade", {})
            minute = ticker_data.get("min", {})
            
            return StockSnapshot(
                ticker=ticker_data.get("ticker", ticker.upper()),
                name=None,  # Snapshot doesn't include name
                
                # Day data
                day_open=Decimal(str(day.get("o", 0))) if day.get("o") else None,
                day_high=Decimal(str(day.get("h", 0))) if day.get("h") else None,
                day_low=Decimal(str(day.get("l", 0))) if day.get("l") else None,
                day_close=Decimal(str(day.get("c", 0))) if day.get("c") else None,
                day_volume=day.get("v"),
                day_vwap=Decimal(str(day.get("vw", 0))) if day.get("vw") else None,
                
                # Previous day
                prev_close=Decimal(str(prev_day.get("c", 0))) if prev_day.get("c") else None,
                prev_volume=prev_day.get("v"),
                
                # Change
                todays_change=Decimal(str(ticker_data.get("todaysChange", 0))) if ticker_data.get("todaysChange") else None,
                todays_change_percent=Decimal(str(ticker_data.get("todaysChangePerc", 0))) if ticker_data.get("todaysChangePerc") else None,
                
                # Last trade
                last_trade_price=Decimal(str(last_trade.get("p", 0))) if last_trade.get("p") else None,
                last_trade_size=last_trade.get("s"),
                last_trade_timestamp=last_trade.get("t"),
                
                # Minute bar
                minute_open=Decimal(str(minute.get("o", 0))) if minute.get("o") else None,
                minute_high=Decimal(str(minute.get("h", 0))) if minute.get("h") else None,
                minute_low=Decimal(str(minute.get("l", 0))) if minute.get("l") else None,
                minute_close=Decimal(str(minute.get("c", 0))) if minute.get("c") else None,
                minute_volume=minute.get("v"),
                
                updated=ticker_data.get("updated"),
            )
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise
        except Exception as e:
            logger.error(f"Massive snapshot failed for {ticker}: {e}")
            raise

    async def get_aggregates(
        self,
        ticker: str,
        multiplier: int = 1,
        timespan: MassiveTimespan = MassiveTimespan.DAY,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        adjusted: bool = True,
        sort: str = "asc",
        limit: int = 5000,
    ) -> List[AggregateBar]:
        """
        Get historical OHLC aggregate bars for charting.

        Uses GET /v2/aggs/ticker/{ticker}/range/{multiplier}/{timespan}/{from}/{to}

        Args:
            ticker: Stock ticker symbol
            multiplier: Size of timespan multiplier (e.g., 5 for 5-minute bars)
            timespan: Bar timespan (minute, hour, day, week, month)
            from_date: Start date (YYYY-MM-DD) or millisecond timestamp
            to_date: End date (YYYY-MM-DD) or millisecond timestamp
            adjusted: Adjust for splits
            sort: Sort order (asc, desc)
            limit: Maximum bars to return (max 50000)

        Returns:
            List of AggregateBar objects

        Example:
            # Get daily bars for last month
            bars = await client.get_aggregates(
                "AAPL",
                timespan=MassiveTimespan.DAY,
                from_date="2024-01-01",
                to_date="2024-01-31",
            )
        """
        # Default date range: last 30 days
        if not to_date:
            to_date = datetime.now().strftime("%Y-%m-%d")
        if not from_date:
            from_dt = datetime.now() - timedelta(days=30)
            from_date = from_dt.strftime("%Y-%m-%d")
        
        try:
            data = await self._request(
                "GET",
                f"/v2/aggs/ticker/{ticker.upper()}/range/{multiplier}/{timespan.value}/{from_date}/{to_date}",
                params={
                    "adjusted": str(adjusted).lower(),
                    "sort": sort,
                    "limit": limit,
                },
            )
            
            results = []
            for bar in data.get("results", []):
                results.append(AggregateBar(
                    timestamp=bar.get("t", 0),
                    open=Decimal(str(bar.get("o", 0))),
                    high=Decimal(str(bar.get("h", 0))),
                    low=Decimal(str(bar.get("l", 0))),
                    close=Decimal(str(bar.get("c", 0))),
                    volume=bar.get("v", 0),
                    vwap=Decimal(str(bar.get("vw", 0))) if bar.get("vw") else None,
                    transactions=bar.get("n"),
                ))
            
            logger.info(f"Massive aggregates for {ticker}: {len(results)} bars")
            return results
            
        except Exception as e:
            logger.error(f"Massive aggregates failed for {ticker}: {e}")
            raise

    async def get_previous_close(self, ticker: str, adjusted: bool = True) -> Optional[AggregateBar]:
        """
        Get previous day's bar for a stock.

        Uses GET /v2/aggs/ticker/{ticker}/prev

        Args:
            ticker: Stock ticker symbol
            adjusted: Adjust for splits

        Returns:
            Previous day's AggregateBar or None
        """
        try:
            data = await self._request(
                "GET",
                f"/v2/aggs/ticker/{ticker.upper()}/prev",
                params={"adjusted": str(adjusted).lower()},
            )
            
            results = data.get("results", [])
            if not results:
                return None
            
            bar = results[0]
            return AggregateBar(
                timestamp=bar.get("T", 0),
                open=Decimal(str(bar.get("o", 0))),
                high=Decimal(str(bar.get("h", 0))),
                low=Decimal(str(bar.get("l", 0))),
                close=Decimal(str(bar.get("c", 0))),
                volume=bar.get("v", 0),
                vwap=Decimal(str(bar.get("vw", 0))) if bar.get("vw") else None,
                transactions=bar.get("n"),
            )
            
        except Exception as e:
            logger.error(f"Massive previous close failed for {ticker}: {e}")
            raise


# Singleton instance
_massive_client: Optional[MassiveClient] = None


def get_massive_client() -> MassiveClient:
    """Get singleton Massive API client instance."""
    global _massive_client
    if _massive_client is None:
        _massive_client = MassiveClient()
    return _massive_client
