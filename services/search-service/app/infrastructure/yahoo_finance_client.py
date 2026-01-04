"""
Yahoo Finance API client implementation.

Provides stock data retrieval with circuit breaker, rate limiting,
and retry logic. Includes ISIN resolution via OpenFIGI API.
"""

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional

import httpx
import yfinance as yf
from tenacity import (retry, retry_if_exception_type,
                      retry_if_not_exception_type, stop_after_attempt,
                      wait_exponential)

from ..domain.entities import (DataSource, Stock, StockIdentifier,
                               StockMetadata, StockPrice)
from ..domain.exceptions import (ExternalServiceException,
                                 StockNotFoundException)
from .circuit_breaker import CircuitBreaker
from .rate_limiter import RateLimiter
from .stock_api_client import IStockAPIClient

logger = logging.getLogger(__name__)


class YahooFinanceClient(IStockAPIClient):
    """
    Yahoo Finance API client with fault tolerance.

    Features:
    - Circuit breaker for failure protection
    - Rate limiting to respect API limits
    - Automatic retry with exponential backoff
    - Symbol mapping for ISIN/WKN lookup
    """

    # Company name to Yahoo symbol mappings for popular stocks
    SYMBOL_MAPPINGS = {
        "APPLE": ["AAPL"],
        "MICROSOFT": ["MSFT"],
        "GOOGLE": ["GOOGL", "GOOG"],
        "ALPHABET": ["GOOGL", "GOOG"],
        "AMAZON": ["AMZN"],
        "TESLA": ["TSLA"],
        "META": ["META"],
        "NVIDIA": ["NVDA"],
        "BMW": ["BMW.DE"],
        "VOLKSWAGEN": ["VOW.DE", "VOW3.DE"],
        "MERCEDES": ["MBG.DE"],
        "SAP": ["SAP.DE"],
        "SIEMENS": ["SIE.DE"],
        "DEUTSCHE BANK": ["DBK.DE"],
        "ALLIANZ": ["ALV.DE"],
    }

    # ISIN to Yahoo symbol mappings for known ISINs
    # This helps avoid slow Yahoo Search API calls
    ISIN_MAPPINGS = {
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
        "DE0007164600": "SAP.DE",
        "DE0007236101": "SIE.DE",
        "DE0005140008": "DBK.DE",
        "DE0008404005": "ALV.DE",
    }

    # WKN to Yahoo symbol mappings for German stocks
    WKN_MAPPINGS = {
        "865985": "AAPL",  # Apple
        "870747": "MSFT",  # Microsoft
        "A14Y6F": "GOOGL",  # Alphabet/Google
        "906866": "AMZN",  # Amazon
        "A1CX3T": "TSLA",  # Tesla
        "A1JWVX": "META",  # Meta/Facebook
        "918422": "NVDA",  # NVIDIA
        "519000": "BMW.DE",  # BMW
        "766403": "VOW3.DE",  # Volkswagen
        "710000": "MBG.DE",  # Mercedes-Benz
        "716460": "SAP.DE",  # SAP
        "723610": "SIE.DE",  # Siemens
        "514000": "DBK.DE",  # Deutsche Bank
        "840400": "ALV.DE",  # Allianz
    }

    def __init__(
        self,
        timeout_seconds: float = 10.0,
        max_retries: int = 3,
        rate_limit_requests: int = 5,
        rate_limit_window: int = 1,
    ):
        """
        Initialize Yahoo Finance client.

        Args:
            timeout_seconds: Request timeout (increased to 10s for ISIN lookups)
            max_retries: Maximum retry attempts
            rate_limit_requests: Max requests per window
            rate_limit_window: Rate limit window in seconds
        """
        self.timeout = timeout_seconds
        self.max_retries = max_retries

        # Initialize circuit breaker
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=5, recovery_timeout=60, name="yahoo_finance"
        )

        # Initialize rate limiter
        self.rate_limiter = RateLimiter(
            max_requests=rate_limit_requests,
            window_seconds=rate_limit_window,
            name="yahoo_finance",
        )

    async def fetch_stock(self, identifier: StockIdentifier) -> Optional[Stock]:
        """Fetch stock data from Yahoo Finance."""
        try:
            # Determine Yahoo symbol
            yahoo_symbol = self._resolve_yahoo_symbol(identifier)

            if not yahoo_symbol:
                logger.warning(f"Could not resolve Yahoo symbol for {identifier}")
                return None

            # Fetch with circuit breaker and rate limiting
            return self.circuit_breaker.call(
                self._fetch_with_retry, yahoo_symbol, identifier
            )

        except StockNotFoundException:
            return None
        except Exception as e:
            logger.error(f"Error fetching stock from Yahoo Finance: {e}")
            raise ExternalServiceException("yahoo_finance", str(e))

    async def search_by_name(self, name: str, limit: int = 10) -> List[Stock]:
        """
        Search stocks by company name.

        Uses Yahoo Finance Search API for worldwide stock search.
        Implements multiple fallback strategies for maximum coverage.

        Args:
            name: Company name to search for
            limit: Maximum number of results to return

        Returns:
            List of Stock entities matching the search
        """
        try:
            results = []

            # Strategy 1: Yahoo Finance Search API (most reliable)
            logger.info(f"Searching Yahoo Finance for: {name}")

            try:
                search_results = yf.Search(
                    name, max_results=limit * 3
                )  # Get more to filter

                if hasattr(search_results, "quotes") and search_results.quotes:
                    logger.info(
                        f"Yahoo Search API returned {len(search_results.quotes)} results"
                    )

                    for quote in search_results.quotes:
                        # Filter for equities and ETFs only
                        quote_type = quote.get("quoteType", "").upper()
                        if quote_type not in {"EQUITY", "ETF"}:
                            continue

                        symbol = quote.get("symbol")
                        if not symbol:
                            continue

                        try:
                            # Create identifier and fetch full data
                            identifier = StockIdentifier(
                                symbol=symbol,
                                name=quote.get("longname") or quote.get("shortname"),
                            )
                            stock = await self.fetch_stock(identifier)

                            if stock:
                                results.append(stock)

                                if len(results) >= limit:
                                    break

                        except Exception as e:
                            logger.debug(f"Error fetching {symbol}: {e}")
                            continue

                    if results:
                        logger.info(f"Found {len(results)} stocks via Yahoo Search API")
                        return results

            except AttributeError:
                logger.warning("yf.Search not available in this yfinance version")
            except Exception as e:
                logger.warning(f"Yahoo Search API error: {e}")

            # Strategy 2: Check hardcoded mappings for popular companies
            logger.info(f"Trying hardcoded symbol mappings for: {name}")
            name_upper = name.upper()

            for company, symbols in self.SYMBOL_MAPPINGS.items():
                # Check if query matches company name (partial or full)
                if (
                    name_upper in company
                    or company in name_upper
                    or any(word in company for word in name_upper.split())
                    or any(word in name_upper for word in company.split())
                ):
                    for symbol in symbols[:limit]:
                        try:
                            identifier = StockIdentifier(symbol=symbol)
                            stock = await self.fetch_stock(identifier)

                            if stock:
                                results.append(stock)
                                logger.info(f"Found {symbol} via hardcoded mapping")

                                if len(results) >= limit:
                                    break

                        except Exception as e:
                            logger.debug(f"Error fetching {symbol}: {e}")
                            continue

                    if results:
                        break

            # Strategy 3: Try direct symbol search (user might have entered a symbol)
            if not results and len(name) <= 10:
                logger.info(f"Trying direct symbol search for: {name}")
                try:
                    identifier = StockIdentifier(symbol=name.upper())
                    stock = await self.fetch_stock(identifier)
                    if stock:
                        results.append(stock)
                        logger.info("Found via direct symbol search")
                except Exception as e:
                    logger.debug(f"Direct symbol search failed: {e}")

            logger.info(f"Total results found for '{name}': {len(results)}")
            return results[:limit]

        except Exception as e:
            logger.error(f"Error searching by name: {e}", exc_info=True)
            return []

    def get_health_status(self) -> dict:
        """Get client health status with circuit breaker details."""
        cb_status = self.circuit_breaker.get_status()
        return {
            "service": "yahoo_finance",
            "healthy": cb_status["state"] != "open",
            "circuit_breaker": cb_status,
            "rate_limiter": self.rate_limiter.get_current_usage(),
            "timeout_seconds": self.timeout,
            "max_retries": self.max_retries,
        }

    def _resolve_yahoo_symbol(self, identifier: StockIdentifier) -> Optional[str]:
        """
        Resolve identifier to Yahoo Finance symbol.

        Strategy (optimized for speed):
        1. If symbol is provided, use it directly
        2. If ISIN is provided, check hardcoded mappings first (fast)
        3. If WKN is provided, check hardcoded mappings first (fast)
        4. If ISIN/WKN not in mappings, try Yahoo Search API (slower)
        5. Use first valid result without additional verification (to avoid timeouts)

        Args:
            identifier: Stock identifier with ISIN, WKN, Symbol, or Name

        Returns:
            Yahoo Finance symbol or None if not found
        """
        # Direct symbol - use as is
        if identifier.symbol:
            return identifier.symbol

        # Check ISIN hardcoded mappings first (fast path)
        if identifier.isin and identifier.isin in self.ISIN_MAPPINGS:
            symbol = self.ISIN_MAPPINGS[identifier.isin]
            logger.info(
                f"Resolved ISIN {identifier.isin} to {symbol} via hardcoded mapping"
            )
            return symbol

        # Check WKN hardcoded mappings (fast path)
        if identifier.wkn and identifier.wkn in self.WKN_MAPPINGS:
            symbol = self.WKN_MAPPINGS[identifier.wkn]
            logger.info(
                f"Resolved WKN {identifier.wkn} to {symbol} via hardcoded mapping"
            )
            return symbol

        # Try to resolve ISIN/WKN via Yahoo Search API
        search_query = None
        query_type = None

        if identifier.isin:
            search_query = identifier.isin
            query_type = "ISIN"
        elif identifier.wkn:
            search_query = identifier.wkn
            query_type = "WKN"
        elif identifier.name:
            # For names, we'll use the search_by_name method instead
            return None

        if search_query:
            logger.info(
                f"Attempting to resolve {query_type} {search_query} using Yahoo Search API"
            )
            try:
                # Use Yahoo Finance Search to find symbol by ISIN/WKN
                search_results = yf.Search(search_query, max_results=10)

                if hasattr(search_results, "quotes") and search_results.quotes:
                    logger.info(
                        f"Yahoo Search returned {len(search_results.quotes)} results for {search_query}"
                    )

                    # Filter for equities and ETFs, return first match
                    for quote in search_results.quotes:
                        quote_type = quote.get("quoteType", "").upper()
                        if quote_type not in {"EQUITY", "ETF", "MUTUALFUND"}:
                            continue

                        symbol = quote.get("symbol")
                        if not symbol:
                            continue

                        # For ISIN/WKN searches, take the first valid equity/ETF match
                        # We don't verify ISIN in the ticker data to avoid slow API calls
                        logger.info(
                            f"Resolved {query_type} {search_query} to symbol {symbol}"
                        )
                        return symbol

                    logger.warning(
                        f"No valid equity/ETF found in search results for {search_query}"
                    )
                else:
                    logger.warning(
                        f"Yahoo Search returned no results for {search_query}"
                    )

            except AttributeError:
                logger.warning("yf.Search not available, trying OpenFIGI fallback")
                # Try OpenFIGI for ISIN lookup
                if identifier.isin:
                    openfigi_symbol = self._resolve_isin_via_openfigi(identifier.isin)
                    if openfigi_symbol:
                        return openfigi_symbol
            except Exception as e:
                logger.warning(f"Yahoo Search API failed for {search_query}: {e}")
                # Try OpenFIGI for ISIN lookup
                if identifier.isin:
                    openfigi_symbol = self._resolve_isin_via_openfigi(identifier.isin)
                    if openfigi_symbol:
                        return openfigi_symbol

        logger.warning(f"No symbol mapping found for {identifier}")
        return None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        reraise=False,
    )
    def _resolve_isin_via_openfigi(self, isin: str) -> Optional[str]:
        """
        Resolve ISIN to ticker symbol using OpenFIGI API.

        OpenFIGI is a free service by Bloomberg that maps ISINs to ticker symbols.
        https://www.openfigi.com/api

        Implements retry logic with exponential backoff for network errors.

        Args:
            isin: International Securities Identification Number

        Returns:
            Ticker symbol or None if not found
        """
        try:
            logger.info(f"Attempting ISIN resolution via OpenFIGI for {isin}")

            url = "https://api.openfigi.com/v3/mapping"
            headers = {"Content-Type": "application/json"}
            payload = [{"idType": "ID_ISIN", "idValue": isin}]

            # Use httpx for async support (if in async context, use sync client for now)
            with httpx.Client(timeout=5.0) as client:
                response = client.post(url, json=payload, headers=headers)

                if response.status_code == 200:
                    data = response.json()

                    if data and len(data) > 0 and "data" in data[0]:
                        figi_data = data[0]["data"]

                        # Look for ticker in the response
                        for item in figi_data:
                            ticker = item.get("ticker")
                            market_sector = item.get("marketSector", "").upper()

                            # Prefer equity listings
                            if ticker and market_sector in {"EQUITY", "CORP"}:
                                # For US stocks, use ticker as-is
                                # For other markets, may need exchange suffix
                                exchange_code = item.get("exchCode", "")

                                # Map common exchange codes to Yahoo Finance format
                                if exchange_code == "GY":  # Germany
                                    ticker = f"{ticker}.DE"
                                elif exchange_code == "LN":  # London
                                    ticker = f"{ticker}.L"
                                elif exchange_code == "FP":  # France
                                    ticker = f"{ticker}.PA"
                                elif exchange_code == "IM":  # Italy
                                    ticker = f"{ticker}.MI"

                                logger.info(
                                    f"OpenFIGI resolved ISIN {isin} to {ticker}"
                                )
                                return ticker

                        # If no equity found, return first ticker
                        if figi_data and figi_data[0].get("ticker"):
                            ticker = figi_data[0]["ticker"]
                            logger.info(
                                f"OpenFIGI resolved ISIN {isin} to {ticker} (non-equity)"
                            )
                            return ticker
                else:
                    logger.warning(
                        f"OpenFIGI API returned status {response.status_code} for ISIN {isin}"
                    )

        except Exception as e:
            logger.warning(f"OpenFIGI ISIN lookup failed for {isin}: {e}")

        return None

    def _openfigi_to_yahoo_symbol(self, ticker: str, exchange_code: str) -> str:
        """
        Convert OpenFIGI ticker/exchange to Yahoo Finance format.

        Args:
            ticker: Stock ticker from OpenFIGI
            exchange_code: Exchange code from OpenFIGI

        Returns:
            Yahoo Finance compatible symbol
        """
        # Common exchange code mappings
        exchange_suffix_map = {
            "GY": ".DE",  # Germany (XETRA)
            "GF": ".F",  # Germany (Frankfurt)
            "LN": ".L",  # London
            "FP": ".PA",  # France (Paris)
            "IM": ".MI",  # Italy (Milan)
            "SM": ".MC",  # Spain (Madrid)
            "NA": ".AS",  # Netherlands (Amsterdam)
            "SW": ".SW",  # Switzerland
            "US": "",  # United States (no suffix)
            "UN": "",  # United States (no suffix)
        }

        suffix = exchange_suffix_map.get(exchange_code, "")
        return f"{ticker}{suffix}"

    @retry(
        retry=retry_if_not_exception_type(StockNotFoundException),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        reraise=True,
    )
    def _fetch_with_retry(
        self, yahoo_symbol: str, identifier: StockIdentifier
    ) -> Stock:
        """
        Fetch stock data with retry logic.

        Args:
            yahoo_symbol: Yahoo Finance symbol
            identifier: Original identifier

        Returns:
            Stock entity

        Raises:
            StockNotFoundException: If stock not found
            ExternalServiceException: If API fails
        """
        # Check rate limit
        self.rate_limiter.acquire()

        logger.info(f"Fetching from Yahoo Finance: {yahoo_symbol}")

        try:
            ticker = yf.Ticker(yahoo_symbol)
            info = ticker.info

            # Validate response
            if not info or "symbol" not in info:
                raise StockNotFoundException(yahoo_symbol, "symbol")

            # Map to domain entity
            stock = self._map_to_entity(info, identifier, yahoo_symbol)

            logger.info(f"Successfully fetched {yahoo_symbol} from Yahoo Finance")
            return stock

        except Exception as e:
            logger.error(f"Yahoo Finance fetch failed for {yahoo_symbol}: {e}")
            raise

    def _map_to_entity(
        self, info: dict, identifier: StockIdentifier, yahoo_symbol: str
    ) -> Stock:
        """Map Yahoo Finance response to Stock entity."""
        # Build complete identifier
        complete_identifier = StockIdentifier(
            isin=identifier.isin,
            wkn=identifier.wkn,
            symbol=yahoo_symbol,
            name=info.get("longName") or info.get("shortName"),
        )

        # Build price data
        current_price = info.get("currentPrice") or info.get("regularMarketPrice")
        if not current_price:
            raise StockNotFoundException(yahoo_symbol, "price data unavailable")

        price = StockPrice(
            current=Decimal(str(current_price)),
            currency=info.get("currency", "USD"),
            change_absolute=(
                Decimal(str(info["regularMarketChange"]))
                if info.get("regularMarketChange")
                else None
            ),
            change_percent=(
                Decimal(str(info["regularMarketChangePercent"]))
                if info.get("regularMarketChangePercent")
                else None
            ),
            previous_close=(
                Decimal(str(info["previousClose"]))
                if info.get("previousClose")
                else None
            ),
            open_price=(
                Decimal(str(info["regularMarketOpen"]))
                if info.get("regularMarketOpen")
                else None
            ),
            day_high=(
                Decimal(str(info["regularMarketDayHigh"]))
                if info.get("regularMarketDayHigh")
                else None
            ),
            day_low=(
                Decimal(str(info["regularMarketDayLow"]))
                if info.get("regularMarketDayLow")
                else None
            ),
            week_52_high=(
                Decimal(str(info["fiftyTwoWeekHigh"]))
                if info.get("fiftyTwoWeekHigh")
                else None
            ),
            week_52_low=(
                Decimal(str(info["fiftyTwoWeekLow"]))
                if info.get("fiftyTwoWeekLow")
                else None
            ),
            volume=info.get("regularMarketVolume"),
            avg_volume=info.get("averageVolume"),
        )

        # Build metadata
        metadata = StockMetadata(
            exchange=info.get("exchange"),
            sector=info.get("sector"),
            industry=info.get("industry"),
            market_cap=(
                Decimal(str(info["marketCap"])) if info.get("marketCap") else None
            ),
            pe_ratio=(
                Decimal(str(info["trailingPE"])) if info.get("trailingPE") else None
            ),
            dividend_yield=(
                Decimal(str(info["dividendYield"]))
                if info.get("dividendYield")
                else None
            ),
            beta=Decimal(str(info["beta"])) if info.get("beta") else None,
            description=info.get("longBusinessSummary"),
            employees=info.get("fullTimeEmployees"),
            website=info.get("website"),
        )

        return Stock(
            identifier=complete_identifier,
            price=price,
            metadata=metadata,
            data_source=DataSource.YAHOO_FINANCE,
            last_updated=datetime.now(timezone.utc),
        )
