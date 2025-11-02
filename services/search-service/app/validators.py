"""
Input validation and Pydantic models for stock search.

This module provides request/response models and validation functions
for the stock search API, including ISIN, WKN, and symbol validation.
"""

import re
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

# Validation patterns
ISIN_PATTERN = r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$"
WKN_PATTERN = r"^[A-Z0-9]{6}$"
SYMBOL_PATTERN = r"^[A-Z0-9\.\-]{1,10}$"

# Name search constants
MIN_NAME_SEARCH_LENGTH = 3
MAX_NAME_SEARCH_RESULTS = 10

# ISIN validation constants
ISIN_LENGTH = 12
ISIN_COUNTRY_CODE_LENGTH = 2
ISIN_CHECKSUM_BASE = 10
LETTER_TO_NUMBER_OFFSET = ord("A") - 10


class SearchQuery(BaseModel):
    """
    Request model for stock search validation.

    Validates that input matches ISIN, WKN, or stock symbol format.

    Attributes:
        query: Search string (ISIN, WKN, or stock symbol)
    """

    query: str = Field(
        ...,
        min_length=1,
        max_length=20,
        description="ISIN, WKN, or stock symbol to search",
    )

    @field_validator("query")
    @classmethod
    def validate_query_format(cls, v: str) -> str:
        """
        Validate that query matches ISIN, WKN, or symbol format.

        Args:
            v: Input query string

        Returns:
            Normalized (uppercase, stripped) query string

        Raises:
            ValueError: If query doesn't match any valid format
        """
        v = v.strip().upper()

        if not (
            re.match(ISIN_PATTERN, v)
            or re.match(WKN_PATTERN, v)
            or re.match(SYMBOL_PATTERN, v)
        ):
            raise ValueError(
                "Invalid format. Query must be a valid ISIN (12 chars), "
                "WKN (6 chars), or stock symbol."
            )

        return v


class StockData(BaseModel):
    """
    Response model for stock data.

    Contains comprehensive stock information from external APIs.

    Attributes:
        symbol: Stock ticker symbol
        name: Company name
        isin: International Securities Identification Number
        wkn: German securities identification number
        current_price: Current stock price
        currency: Currency code (e.g., USD, EUR)
        exchange: Stock exchange name
        market_cap: Market capitalization
        sector: Business sector
        industry: Industry classification
        source: Data source API name
        cached: Whether data was served from cache
        cache_age_seconds: Age of cached data in seconds
    """

    symbol: str = Field(..., description="Stock ticker symbol")
    name: str = Field(..., description="Company name")
    isin: Optional[str] = Field(
        None, description="International Securities Identification Number"
    )
    wkn: Optional[str] = Field(
        None, description="Wertpapierkennnummer (German securities code)"
    )
    current_price: Optional[float] = Field(None, description="Current stock price")
    currency: Optional[str] = Field(None, description="Currency code (e.g., USD, EUR)")
    exchange: Optional[str] = Field(None, description="Stock exchange")
    market_cap: Optional[float] = Field(None, description="Market capitalization")
    sector: Optional[str] = Field(None, description="Business sector")
    industry: Optional[str] = Field(None, description="Industry classification")
    source: str = Field(..., description="Data source (yahoo or alphavantage)")
    cached: bool = Field(False, description="Whether data was served from cache")
    cache_age_seconds: Optional[int] = Field(
        None, description="Age of cached data in seconds"
    )


class StockSearchResponse(BaseModel):
    """
    Response wrapper for stock search results.

    Provides a standardized response structure for stock search operations.

    Attributes:
        success: Whether the search was successful
        data: Stock data if found
        message: Error or informational message
        suggestions: Suggested stock symbols if not found
        query_type: Detected query type
        response_time_ms: Response time in milliseconds
    """

    success: bool = Field(..., description="Whether the search was successful")
    data: Optional[StockData] = Field(None, description="Stock data if found")
    message: Optional[str] = Field(None, description="Error or informational message")
    suggestions: Optional[list[str]] = Field(
        None, description="Suggested stock symbols if not found"
    )
    query_type: Literal["isin", "wkn", "symbol", "name"] = Field(
        ..., description="Detected query type"
    )
    response_time_ms: int = Field(..., description="Response time in milliseconds")


class ErrorResponse(BaseModel):
    """
    Error response model.

    Standardized error response structure for API errors.

    Attributes:
        error: Error type identifier
        message: Human-readable error message
        details: Additional error details
    """

    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[dict] = Field(None, description="Additional error details")


class NameSearchQuery(BaseModel):
    """
    Request model for company name search validation.

    Validates company name search queries with minimum length requirement.

    Attributes:
        query: Company name search string (min 3 characters)
    """

    query: str = Field(
        ...,
        min_length=MIN_NAME_SEARCH_LENGTH,
        max_length=100,
        description="Company name to search (minimum 3 characters)",
    )

    @field_validator("query")
    @classmethod
    def validate_name_query(cls, v: str) -> str:
        """
        Validate and normalize company name query.

        Args:
            v: Input query string

        Returns:
            Normalized query string (stripped whitespace)

        Raises:
            ValueError: If query is too short or contains only whitespace
        """
        v = v.strip()

        if len(v) < MIN_NAME_SEARCH_LENGTH:
            raise ValueError(
                f"Query must be at least {MIN_NAME_SEARCH_LENGTH} characters long"
            )

        if not v:
            raise ValueError("Query cannot be empty or only whitespace")

        return v


class StockSearchResult(BaseModel):
    """
    Single stock search result for name search.

    Compact representation of stock data for search results listing.

    Attributes:
        symbol: Stock ticker symbol
        name: Company name
        isin: International Securities Identification Number
        wkn: German securities identification number
        current_price: Current stock price
        currency: Currency code
        exchange: Stock exchange name
        relevance_score: Search relevance score (0.0 to 1.0)
    """

    symbol: str = Field(..., description="Stock ticker symbol")
    name: str = Field(..., description="Company name")
    isin: Optional[str] = Field(None, description="ISIN code")
    wkn: Optional[str] = Field(None, description="WKN code")
    current_price: Optional[float] = Field(None, description="Current stock price")
    currency: Optional[str] = Field(None, description="Currency code")
    exchange: Optional[str] = Field(None, description="Stock exchange")
    relevance_score: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Search relevance score (0.0 to 1.0)"
    )


class NameSearchResponse(BaseModel):
    """
    Response model for company name search.

    Returns list of matching stocks with relevance ranking.

    Attributes:
        success: Whether the search was successful
        results: List of matching stock results
        total_results: Total number of results found
        message: Optional informational message
        query: Original search query
        response_time_ms: Response time in milliseconds
    """

    success: bool = Field(..., description="Whether the search was successful")
    results: list[StockSearchResult] = Field(
        default_factory=list, description="List of matching stock results"
    )
    total_results: int = Field(..., description="Total number of results found")
    message: Optional[str] = Field(None, description="Optional informational message")
    query: str = Field(..., description="Original search query")
    response_time_ms: int = Field(..., description="Response time in milliseconds")


def detect_query_type(query: str) -> Literal["isin", "wkn", "symbol"]:
    """
    Detect whether query is ISIN, WKN, or symbol.

    Detection rules:
    - ISIN: 12 characters, starts with 2 letters
    - WKN: Exactly 6 alphanumeric characters
    - Symbol: Everything else

    Args:
        query: Search query string

    Returns:
        Query type: 'isin', 'wkn', or 'symbol'
    """
    query = query.strip().upper()

    if (
        len(query) == ISIN_LENGTH
        and query[:ISIN_COUNTRY_CODE_LENGTH].isalpha()
        and query[ISIN_COUNTRY_CODE_LENGTH:].isalnum()
    ):
        return "isin"

    if len(query) == 6 and query.isalnum():
        return "wkn"

    return "symbol"


def is_valid_isin(isin: str) -> bool:
    """
    Validate ISIN format and checksum using Luhn algorithm.

    ISIN format: 2-letter country code + 9-character national code + 1 check digit
    Example: US0378331005 (Apple Inc.)

    Args:
        isin: ISIN string to validate

    Returns:
        True if valid ISIN with correct checksum, False otherwise
    """
    if not isin or len(isin) != ISIN_LENGTH:
        return False

    if not re.match(ISIN_PATTERN, isin):
        return False

    # Validate checksum using Luhn algorithm
    digits = []
    for char in isin[:-1]:
        if char.isdigit():
            digits.append(int(char))
        else:
            digits.append(ord(char) - LETTER_TO_NUMBER_OFFSET)

    # Convert to string and then to individual digits
    digit_string = "".join(str(d) for d in digits)
    digit_list = [int(d) for d in digit_string]

    # Apply Luhn algorithm
    total = 0
    for i, digit in enumerate(reversed(digit_list)):
        if i % 2 == 0:
            doubled = digit * 2
            total += doubled if doubled < 10 else doubled - 9
        else:
            total += digit

    check_digit = (
        ISIN_CHECKSUM_BASE - (total % ISIN_CHECKSUM_BASE)
    ) % ISIN_CHECKSUM_BASE
    return check_digit == int(isin[-1])


def is_valid_wkn(wkn: str) -> bool:
    """
    Validate WKN (Wertpapierkennnummer) format.

    WKN is a 6-character alphanumeric German securities identification number.
    Example: 865985 (Apple Inc. in German markets)

    Args:
        wkn: WKN string to validate

    Returns:
        True if valid WKN format, False otherwise
    """
    if not wkn or len(wkn) != 6:
        return False

    return bool(re.match(WKN_PATTERN, wkn))


class PricePoint(BaseModel):
    """
    Single price data point for historical chart.

    Attributes:
        timestamp: ISO 8601 timestamp
        price: Stock price at this timestamp
        volume: Trading volume (optional)
    """

    timestamp: str = Field(..., description="ISO 8601 timestamp")
    price: float = Field(..., description="Stock price")
    volume: Optional[int] = Field(None, description="Trading volume")


class PriceChange(BaseModel):
    """
    Price change information with percentage and absolute values.

    Attributes:
        absolute: Absolute price change
        percentage: Percentage price change
        direction: Direction of change (up, down, neutral)
    """

    absolute: float = Field(..., description="Absolute price change")
    percentage: float = Field(..., description="Percentage price change")
    direction: Literal["up", "down", "neutral"] = Field(
        ..., description="Direction of price change"
    )


class WeekRange52(BaseModel):
    """
    52-week high and low price range.

    Attributes:
        high: 52-week high price
        low: 52-week low price
        high_date: Date when high was reached (optional)
        low_date: Date when low was reached (optional)
    """

    high: float = Field(..., description="52-week high price")
    low: float = Field(..., description="52-week low price")
    high_date: Optional[str] = Field(
        None, description="Date of 52-week high (ISO 8601)"
    )
    low_date: Optional[str] = Field(None, description="Date of 52-week low (ISO 8601)")


class StockReportData(BaseModel):
    """
    Comprehensive stock report data model.

    Contains all information required for stock report display including
    real-time prices, historical data, and key metrics.

    Attributes:
        symbol: Stock ticker symbol
        name: Company name
        isin: International Securities Identification Number
        wkn: German securities identification number
        current_price: Current stock price
        currency: Currency code (e.g., USD, EUR)
        exchange: Stock exchange name
        price_change_1d: 1-day price change information
        week_52_range: 52-week high/low prices
        market_cap: Market capitalization
        sector: Business sector
        industry: Industry classification
        price_history_7d: 7-day price history for chart
        last_updated: ISO 8601 timestamp of last data update
        data_source: Source of data (yahoo or alphavantage)
        cached: Whether data was served from cache
        cache_timestamp: Timestamp when data was cached (ISO 8601)
    """

    symbol: str = Field(..., description="Stock ticker symbol")
    name: str = Field(..., description="Company name")
    isin: Optional[str] = Field(None, description="ISIN code")
    wkn: Optional[str] = Field(None, description="WKN code")
    current_price: float = Field(..., description="Current stock price")
    currency: str = Field(..., description="Currency code")
    exchange: str = Field(..., description="Stock exchange name")
    price_change_1d: PriceChange = Field(..., description="1-day price change")
    week_52_range: WeekRange52 = Field(..., description="52-week high/low range")
    market_cap: Optional[float] = Field(None, description="Market capitalization")
    sector: Optional[str] = Field(None, description="Business sector")
    industry: Optional[str] = Field(None, description="Industry classification")
    price_history_7d: list[PricePoint] = Field(
        ..., description="7-day price history for chart"
    )
    last_updated: str = Field(..., description="Last update timestamp (ISO 8601)")
    data_source: str = Field(..., description="Data source (yahoo or alphavantage)")
    cached: bool = Field(False, description="Whether data was served from cache")
    cache_timestamp: Optional[str] = Field(
        None, description="Cache timestamp (ISO 8601)"
    )


class StockReportResponse(BaseModel):
    """
    Response model for stock report endpoint.

    Provides comprehensive stock report with all required metrics.

    Attributes:
        success: Whether the request was successful
        data: Stock report data if successful
        message: Error or informational message
        response_time_ms: Response time in milliseconds
    """

    success: bool = Field(..., description="Whether the request was successful")
    data: Optional[StockReportData] = Field(None, description="Stock report data")
    message: Optional[str] = Field(None, description="Error or informational message")
    response_time_ms: int = Field(..., description="Response time in milliseconds")
