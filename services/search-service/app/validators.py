"""
Input validation and Pydantic models for stock search
"""
import re
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


class SearchQuery(BaseModel):
    """Request model for stock search"""

    query: str = Field(
        ..., min_length=1, max_length=20, description="ISIN, WKN, or stock symbol to search"
    )

    @field_validator("query")
    @classmethod
    def validate_query_format(cls, v: str) -> str:
        """Validate that query matches ISIN or WKN format"""
        v = v.strip().upper()

        # ISIN format: 12 alphanumeric characters (e.g., US0378331005)
        isin_pattern = r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$"

        # WKN format: 6 alphanumeric characters (e.g., 865985)
        wkn_pattern = r"^[A-Z0-9]{6}$"

        # Generic symbol pattern (up to 10 chars)
        symbol_pattern = r"^[A-Z0-9\.\-]{1,10}$"

        if not (
            re.match(isin_pattern, v) or re.match(wkn_pattern, v) or re.match(symbol_pattern, v)
        ):
            raise ValueError(
                "Invalid format. Query must be a valid ISIN (12 chars), WKN (6 chars), or stock symbol."
            )

        return v


class StockData(BaseModel):
    """Response model for stock data"""

    symbol: str = Field(..., description="Stock ticker symbol")
    name: str = Field(..., description="Company name")
    isin: Optional[str] = Field(None, description="International Securities Identification Number")
    wkn: Optional[str] = Field(None, description="Wertpapierkennnummer (German securities code)")
    current_price: Optional[float] = Field(None, description="Current stock price")
    currency: Optional[str] = Field(None, description="Currency code (e.g., USD, EUR)")
    exchange: Optional[str] = Field(None, description="Stock exchange")
    market_cap: Optional[float] = Field(None, description="Market capitalization")
    sector: Optional[str] = Field(None, description="Business sector")
    industry: Optional[str] = Field(None, description="Industry classification")
    source: str = Field(..., description="Data source (yahoo or alphavantage)")
    cached: bool = Field(False, description="Whether data was served from cache")
    cache_age_seconds: Optional[int] = Field(None, description="Age of cached data in seconds")


class StockSearchResponse(BaseModel):
    """Response wrapper for stock search"""

    success: bool = Field(..., description="Whether the search was successful")
    data: Optional[StockData] = Field(None, description="Stock data if found")
    message: Optional[str] = Field(None, description="Error or informational message")
    suggestions: Optional[list[str]] = Field(
        None, description="Suggested stock symbols if not found"
    )
    query_type: Literal["isin", "wkn", "symbol"] = Field(..., description="Detected query type")
    response_time_ms: int = Field(..., description="Response time in milliseconds")


class ErrorResponse(BaseModel):
    """Error response model"""

    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[dict] = Field(None, description="Additional error details")


def detect_query_type(query: str) -> Literal["isin", "wkn", "symbol"]:
    """
    Detect whether query is ISIN, WKN, or symbol

    Args:
        query: Search query string

    Returns:
        Query type: 'isin', 'wkn', or 'symbol'
    """
    query = query.strip().upper()

    # ISIN: 12 chars, starts with 2 letters
    if len(query) == 12 and query[:2].isalpha() and query[2:].isalnum():
        return "isin"

    # WKN: exactly 6 alphanumeric chars
    if len(query) == 6 and query.isalnum():
        return "wkn"

    # Default to symbol
    return "symbol"


def is_valid_isin(isin: str) -> bool:
    """
    Validate ISIN format and checksum

    Args:
        isin: ISIN string to validate

    Returns:
        True if valid ISIN
    """
    if not isin or len(isin) != 12:
        return False

    # Check basic format
    if not re.match(r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$", isin):
        return False

    # Validate checksum using Luhn algorithm
    # Convert letters to numbers (A=10, B=11, ..., Z=35)
    digits = []
    for char in isin[:-1]:  # Exclude check digit
        if char.isdigit():
            digits.append(int(char))
        else:
            # Convert letter to number (A=10, B=11, etc.)
            digits.append(ord(char) - ord("A") + 10)

    # Convert to string and then to individual digits
    digit_string = "".join(str(d) for d in digits)
    digit_list = [int(d) for d in digit_string]

    # Apply Luhn algorithm
    total = 0
    for i, digit in enumerate(reversed(digit_list)):
        if i % 2 == 0:  # Every second digit from right
            doubled = digit * 2
            total += doubled if doubled < 10 else doubled - 9
        else:
            total += digit

    check_digit = (10 - (total % 10)) % 10
    return check_digit == int(isin[-1])


def is_valid_wkn(wkn: str) -> bool:
    """
    Validate WKN format

    Args:
        wkn: WKN string to validate

    Returns:
        True if valid WKN
    """
    if not wkn or len(wkn) != 6:
        return False

    return bool(re.match(r"^[A-Z0-9]{6}$", wkn))
