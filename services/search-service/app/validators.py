"""
Validation models and functions for search service.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

# Constants
MAX_NAME_SEARCH_RESULTS = 50


# Request Models
class SearchQuery(BaseModel):
    """Search query model."""

    query: str = Field(..., min_length=1, max_length=100)


class NameSearchQuery(BaseModel):
    """Name-based search query model."""

    query: str = Field(..., min_length=1, max_length=100)
    limit: int = Field(default=10, ge=1, le=MAX_NAME_SEARCH_RESULTS)


# Response Models
class ErrorResponse(BaseModel):
    """Error response model."""

    error: str
    details: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class PricePoint(BaseModel):
    """Price point model."""

    timestamp: datetime
    price: float
    volume: Optional[int] = None


class WeekRange52(BaseModel):
    """52-week range model."""

    high: float
    low: float
    current: float


class PriceChange(BaseModel):
    """Price change model."""

    change_percent: float
    change_absolute: float
    period: str  # "1d", "1w", "1m", etc.


class StockData(BaseModel):
    """Stock data model."""

    symbol: str
    name: str
    isin: Optional[str] = None
    wkn: Optional[str] = None
    current_price: Optional[float] = None
    currency: Optional[str] = None
    exchange: Optional[str] = None
    market_cap: Optional[float] = None
    pe_ratio: Optional[float] = None
    dividend_yield: Optional[float] = None
    fifty_two_week_high: Optional[float] = None
    fifty_two_week_low: Optional[float] = None
    price_changes: Optional[List[PriceChange]] = None
    last_updated: Optional[datetime] = None


class StockReportData(BaseModel):
    """Stock report data model."""

    symbol: str
    name: str
    isin: Optional[str] = None
    wkn: Optional[str] = None
    current_price: Optional[float] = None
    currency: Optional[str] = None
    exchange: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    description: Optional[str] = None
    market_cap: Optional[float] = None
    pe_ratio: Optional[float] = None
    eps: Optional[float] = None
    dividend_yield: Optional[float] = None
    beta: Optional[float] = None
    fifty_two_week_high: Optional[float] = None
    fifty_two_week_low: Optional[float] = None
    average_volume: Optional[int] = None
    price_history: Optional[List[PricePoint]] = None
    price_changes: Optional[List[PriceChange]] = None
    last_updated: Optional[datetime] = None


class StockReportResponse(BaseModel):
    """Stock report response model."""

    data: StockReportData
    cache_hit: bool = False
    source: str = "api"


class NameSearchResponse(BaseModel):
    """Name search response model."""

    results: List[StockData]
    count: int
    query: str
    cache_hit: bool = False


class StockSearchResponse(BaseModel):
    """Stock search response model."""

    data: Optional[StockData] = None
    found: bool = False
    query: str
    query_type: str
    cache_hit: bool = False
    source: str = "api"


# Validation Functions
def detect_query_type(query: str) -> str:
    """
    Detect the type of search query.

    Args:
        query: The search query string

    Returns:
        One of: "isin", "wkn", "symbol", "name"
    """
    query = query.strip().upper()

    # ISIN: 12 characters, starts with 2 letters
    if len(query) == 12 and query[:2].isalpha() and query[2:].isalnum():
        return "isin"

    # WKN: 6 characters, alphanumeric
    if len(query) == 6 and query.isalnum():
        return "wkn"

    # Symbol: Short alphanumeric (1-10 chars)
    if 1 <= len(query) <= 10 and query.replace(".", "").isalnum():
        return "symbol"

    # Default to name search
    return "name"


def is_valid_isin(isin: str) -> bool:
    """
    Validate ISIN format.

    Args:
        isin: The ISIN string to validate

    Returns:
        True if valid ISIN format, False otherwise
    """
    if not isin or len(isin) != 12:
        return False

    isin = isin.upper()
    return isin[:2].isalpha() and isin[2:].isalnum()


def is_valid_wkn(wkn: str) -> bool:
    """
    Validate WKN format.

    Args:
        wkn: The WKN string to validate

    Returns:
        True if valid WKN format, False otherwise
    """
    if not wkn or len(wkn) != 6:
        return False

    return wkn.upper().isalnum()
