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
    query_type: Literal["isin", "wkn", "symbol"] = Field(
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
