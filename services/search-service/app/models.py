"""
Database models for search service.

This module defines SQLAlchemy ORM models for managing stock data cache,
API rate limiting, and search history tracking.
"""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Column, DateTime, Float, Index, Integer, String, Text
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

Base: Any = declarative_base()

# Constants
CACHE_HIT_INCREMENT = 1


class StockCache(Base):
    """
    Stock data cache model with time-to-live management.

    This model stores fetched stock data to reduce external API calls
    and improve response times. Each entry has a 5-minute TTL.

    Attributes:
        id: Primary key identifier
        isin: International Securities Identification Number (12 characters)
        wkn: German securities identification number (6 characters)
        symbol: Stock ticker symbol
        name: Company name
        current_price: Current stock price
        currency: Currency code (e.g., USD, EUR)
        exchange: Stock exchange name
        market_cap: Market capitalization value
        sector: Business sector
        industry: Industry classification
        data_source: API source ('yahoo' or 'alphavantage')
        raw_data: JSON string of raw API response for debugging
        created_at: Timestamp of cache entry creation
        updated_at: Timestamp of last cache entry update
        expires_at: Timestamp when cache entry expires (TTL)
        cache_hits: Number of times this entry was served from cache
    """

    __tablename__ = "stock_cache"

    id = Column(Integer, primary_key=True, index=True)

    # Search identifiers
    isin = Column(String(12), unique=True, index=True, nullable=True)
    wkn = Column(String(6), index=True, nullable=True)
    symbol = Column(String(20), index=True, nullable=False)

    # Stock information
    name = Column(String(255), nullable=False, index=True)
    current_price = Column(Float, nullable=True)
    currency = Column(String(10), nullable=True)
    exchange = Column(String(50), nullable=True)

    # Additional metadata
    market_cap = Column(Float, nullable=True)
    sector = Column(String(100), nullable=True)
    industry = Column(String(100), nullable=True)

    # API source tracking
    data_source = Column(String(50), nullable=False)
    raw_data = Column(Text, nullable=True)

    # Cache management
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    cache_hits = Column(Integer, default=0, nullable=False)

    # Composite indexes for faster lookups
    __table_args__ = (
        Index("idx_isin_expires", "isin", "expires_at"),
        Index("idx_wkn_expires", "wkn", "expires_at"),
        Index("idx_symbol_expires", "symbol", "expires_at"),
    )

    def is_expired(self) -> bool:
        """
        Check if cache entry has expired.

        Returns:
            True if current time is past expiration time, False otherwise
        """
        return datetime.now(timezone.utc) > self.expires_at

    def increment_hits(self) -> None:
        """
        Increment cache hit counter.

        Tracks how many times this cached entry has been served to requests.
        """
        self.cache_hits += CACHE_HIT_INCREMENT


class APIRateLimit(Base):
    """
    API rate limiting tracking model.

    Manages and tracks API rate limits for external services.
    Helps manage Yahoo Finance (5 req/sec) and Alpha Vantage (5 req/min) limits.

    Attributes:
        id: Primary key identifier
        api_name: Name of the API ('yahoo' or 'alphavantage')
        requests_made: Count of requests made in current window
        window_start: Timestamp when current rate limit window started
        last_request: Timestamp of most recent request
        max_requests: Maximum requests allowed per window
        window_seconds: Duration of rate limit window in seconds
    """

    __tablename__ = "api_rate_limits"

    id = Column(Integer, primary_key=True, index=True)
    api_name = Column(String(50), unique=True, index=True, nullable=False)
    requests_made = Column(Integer, default=0, nullable=False)
    window_start = Column(DateTime, default=func.now(), nullable=False)
    last_request = Column(DateTime, nullable=True)

    # Rate limit configuration
    max_requests = Column(Integer, nullable=False)
    window_seconds = Column(Integer, nullable=False)

    __table_args__ = (Index("idx_api_window", "api_name", "window_start"),)


class SearchHistory(Base):
    """
    Search query history tracking model.

    Tracks search queries for analytics and autocomplete suggestions.
    Enables popular search query recommendations.

    Attributes:
        id: Primary key identifier
        query: Search query string
        query_type: Type of query ('isin', 'wkn', or 'symbol')
        result_found: Whether result was found (1) or not (0)
        search_count: Number of times this query has been searched
        created_at: Timestamp of first search
        last_searched: Timestamp of most recent search
    """

    __tablename__ = "search_history"

    id = Column(Integer, primary_key=True, index=True)
    query = Column(String(20), index=True, nullable=False)
    query_type = Column(String(10), nullable=False)
    result_found = Column(Integer, default=0, nullable=False)
    search_count = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    last_searched = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index("idx_query_type", "query", "query_type"),
        Index("idx_search_count", "search_count"),
    )
