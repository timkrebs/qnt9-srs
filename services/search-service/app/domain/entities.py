"""
Domain entities for stock data.

Core business objects representing stocks, prices, and related data.
These entities are framework-agnostic and contain only business logic.
"""

import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional


class IdentifierType(str, Enum):
    """Types of stock identifiers."""

    ISIN = "isin"
    WKN = "wkn"
    SYMBOL = "symbol"
    NAME = "name"


class DataSource(str, Enum):
    """External data sources for stock information."""

    MASSIVE = "massive"
    YAHOO_FINANCE = "yahoo"  # Deprecated - kept for backward compatibility
    ALPHA_VANTAGE = "alphavantage"
    CACHE = "cache"


@dataclass(frozen=True)
class StockIdentifier:
    """
    Value object representing stock identifiers.

    Ensures validity of ISIN, WKN, and symbol formats.
    Immutable to guarantee consistency.
    """

    isin: Optional[str] = None
    wkn: Optional[str] = None
    symbol: Optional[str] = None
    name: Optional[str] = None

    # Validation patterns
    ISIN_PATTERN = re.compile(r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")
    WKN_PATTERN = re.compile(r"^[A-Z0-9]{6}$")
    SYMBOL_PATTERN = re.compile(r"^[A-Z0-9\.\-]{1,20}$")

    def __post_init__(self):
        """Validate identifiers on creation."""
        if self.isin and not self.ISIN_PATTERN.match(self.isin):
            raise ValueError(f"Invalid ISIN format: {self.isin}")
        if self.wkn and not self.WKN_PATTERN.match(self.wkn):
            raise ValueError(f"Invalid WKN format: {self.wkn}")
        if self.symbol and not self.SYMBOL_PATTERN.match(self.symbol):
            raise ValueError(f"Invalid symbol format: {self.symbol}")
        if not any([self.isin, self.wkn, self.symbol, self.name]):
            raise ValueError("At least one identifier must be provided")

    # Common ticker symbols (to disambiguate from company names)
    KNOWN_TICKER_SYMBOLS = {
        "AAPL",
        "MSFT",
        "GOOGL",
        "GOOG",
        "AMZN",
        "TSLA",
        "META",
        "NVDA",
        "BRK",
        "JPM",
        "V",
        "JNJ",
        "WMT",
        "PG",
        "MA",
        "HD",
        "DIS",
        "PYPL",
        "NFLX",
        "ADBE",
        "CRM",
        "INTC",
        "CSCO",
        "PFE",
        "ABT",
        "TMO",
        "NKE",
        "COST",
        "AVGO",
        "CMCSA",
        "PEP",
        "ORCL",
        "T",
        "VZ",
        "MRK",
        "QCOM",
    }

    @classmethod
    def detect_type(cls, query: str) -> IdentifierType:
        """
        Detect the type of identifier from a query string.

        Detection order (most specific to least specific):
        1. ISIN: Exactly 12 chars, starts with 2 letters
        2. WKN: Exactly 6 chars with at least one digit
        3. SYMBOL: Known ticker symbols or 1-4 char codes
        4. NAME: Everything else, including words like "Apple", "Amazon"

        Args:
            query: The search query (will be normalized)

        Returns:
            The detected identifier type
        """
        query = query.strip()
        if not query:
            return IdentifierType.NAME

        query_upper = query.upper()

        # ISIN: 12 characters, strict pattern (e.g., US0378331005)
        if len(query_upper) == 12 and cls.ISIN_PATTERN.match(query_upper):
            return IdentifierType.ISIN

        # WKN: Exactly 6 characters with at least one digit (e.g., 865985, A0AET0)
        # This prevents false positives like "AMAZON" being detected as WKN
        if len(query_upper) == 6 and cls.WKN_PATTERN.match(query_upper):
            if any(c.isdigit() for c in query_upper):
                return IdentifierType.WKN

        # NAME: Contains spaces (e.g., "Deutsche Bank", "Apple Inc")
        if " " in query:
            return IdentifierType.NAME

        # SYMBOL: Check if it's a known ticker symbol first
        if query_upper in cls.KNOWN_TICKER_SYMBOLS:
            return IdentifierType.SYMBOL

        # SYMBOL: Very short codes (1-4 chars) are likely symbols
        # This covers most stock tickers while excluding company names
        if len(query_upper) <= 4 and cls.SYMBOL_PATTERN.match(query_upper):
            return IdentifierType.SYMBOL

        # If 5+ chars and purely alphabetic, likely a company name
        # Examples: "Apple", "Amazon", "Tesla", "Google"
        if len(query_upper) >= 5 and query_upper.isalpha():
            return IdentifierType.NAME

        # SYMBOL: 5 chars with special characters (e.g., "BRK.B")
        if len(query_upper) == 5 and cls.SYMBOL_PATTERN.match(query_upper):
            if not query_upper.isalpha():  # Has dots, hyphens, etc.
                return IdentifierType.SYMBOL
            return IdentifierType.NAME  # Pure 5-letter word is likely a name

        # NAME: Alphabetic strings with hyphens or ampersands (e.g., "T-Mobile", "AT&T")
        if query.replace("-", "").replace("&", "").isalpha():
            return IdentifierType.NAME

        return IdentifierType.NAME

    def get_primary_identifier(self) -> tuple[IdentifierType, str]:
        """
        Get the primary identifier for lookup.

        Returns:
            Tuple of (identifier_type, value)
        """
        if self.isin:
            return (IdentifierType.ISIN, self.isin)
        elif self.wkn:
            return (IdentifierType.WKN, self.wkn)
        elif self.symbol:
            return (IdentifierType.SYMBOL, self.symbol)
        else:
            return (IdentifierType.NAME, self.name or "")


@dataclass
class StockPrice:
    """
    Value object for stock pricing information.

    Contains current price, changes, and trading metrics.
    """

    current: Decimal
    currency: str
    change_absolute: Optional[Decimal] = None
    change_percent: Optional[Decimal] = None
    previous_close: Optional[Decimal] = None
    open_price: Optional[Decimal] = None
    day_high: Optional[Decimal] = None
    day_low: Optional[Decimal] = None
    week_52_high: Optional[Decimal] = None
    week_52_low: Optional[Decimal] = None
    volume: Optional[int] = None
    avg_volume: Optional[int] = None
    timestamp: Optional[datetime] = None

    def __post_init__(self):
        """Validate price data."""
        if self.current <= 0:
            raise ValueError("Current price must be positive")
        if len(self.currency) != 3:
            raise ValueError("Currency must be 3-letter code (e.g., USD, EUR)")

    def calculate_change_percent(self) -> Optional[Decimal]:
        """Calculate percentage change from previous close."""
        if self.previous_close and self.previous_close > 0:
            return ((self.current - self.previous_close) / self.previous_close) * 100
        return None


@dataclass
class StockMetadata:
    """
    Company and trading metadata.

    Contains non-price information about the stock and company.
    """

    exchange: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    market_cap: Optional[Decimal] = None
    pe_ratio: Optional[Decimal] = None
    dividend_yield: Optional[Decimal] = None
    beta: Optional[Decimal] = None
    description: Optional[str] = None
    employees: Optional[int] = None
    founded: Optional[int] = None
    headquarters: Optional[str] = None
    website: Optional[str] = None


@dataclass
class Stock:
    """
    Aggregate root for stock information.

    Combines identifier, price, and metadata into a complete stock entity.
    """

    identifier: StockIdentifier
    price: StockPrice
    metadata: StockMetadata
    data_source: DataSource
    last_updated: datetime
    cache_age_seconds: Optional[int] = None

    def is_stale(self, max_age_seconds: int = 300) -> bool:
        """
        Check if stock data is stale.

        Args:
            max_age_seconds: Maximum acceptable age in seconds

        Returns:
            True if data is older than max_age_seconds
        """
        if not self.cache_age_seconds:
            return False
        return self.cache_age_seconds > max_age_seconds

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "identifier": {
                "isin": self.identifier.isin,
                "wkn": self.identifier.wkn,
                "symbol": self.identifier.symbol,
                "name": self.identifier.name,
            },
            "price": {
                "current": float(self.price.current) if self.price.current else None,
                "currency": self.price.currency,
                "change_absolute": (
                    float(self.price.change_absolute)
                    if self.price.change_absolute
                    else None
                ),
                "change_percent": (
                    float(self.price.change_percent)
                    if self.price.change_percent
                    else None
                ),
                "previous_close": (
                    float(self.price.previous_close)
                    if self.price.previous_close
                    else None
                ),
                "open": float(self.price.open_price) if self.price.open_price else None,
                "day_high": float(self.price.day_high) if self.price.day_high else None,
                "day_low": float(self.price.day_low) if self.price.day_low else None,
                "week_52_high": (
                    float(self.price.week_52_high) if self.price.week_52_high else None
                ),
                "week_52_low": (
                    float(self.price.week_52_low) if self.price.week_52_low else None
                ),
                "volume": self.price.volume,
                "avg_volume": self.price.avg_volume,
                "timestamp": (
                    self.price.timestamp.isoformat() if self.price.timestamp else None
                ),
            },
            "metadata": {
                "exchange": self.metadata.exchange,
                "sector": self.metadata.sector,
                "industry": self.metadata.industry,
                "market_cap": (
                    float(self.metadata.market_cap)
                    if self.metadata.market_cap
                    else None
                ),
                "pe_ratio": (
                    float(self.metadata.pe_ratio) if self.metadata.pe_ratio else None
                ),
                "dividend_yield": (
                    float(self.metadata.dividend_yield)
                    if self.metadata.dividend_yield
                    else None
                ),
                "beta": float(self.metadata.beta) if self.metadata.beta else None,
                "description": self.metadata.description,
                "employees": self.metadata.employees,
                "founded": self.metadata.founded,
                "headquarters": self.metadata.headquarters,
                "website": self.metadata.website,
            },
            "data_source": self.data_source.value,
            "last_updated": self.last_updated.isoformat(),
            "cache_age_seconds": self.cache_age_seconds,
        }
