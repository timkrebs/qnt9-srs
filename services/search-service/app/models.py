"""
Database models for search service.

This module defines SQLAlchemy ORM models for managing stock data cache,
API rate limiting, and search history tracking.
"""

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (BigInteger, Column, DateTime, Float, Index, Integer,
                        String, Text)
from sqlalchemy.dialects.postgresql import TSVECTOR, UUID
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
    updated_at = Column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )
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
        user_id: Optional user ID for tracking user-specific history
        created_at: Timestamp of first search
        last_searched: Timestamp of most recent search
    """

    __tablename__ = "search_history"

    id = Column(Integer, primary_key=True, index=True)
    query = Column(String(20), index=True, nullable=False)
    query_type = Column(String(10), nullable=False)
    result_found = Column(Integer, default=0, nullable=False)
    search_count = Column(Integer, default=1, nullable=False)
    user_id = Column(UUID(as_uuid=True), index=True, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    last_searched = Column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        Index("idx_query_type", "query", "query_type"),
        Index("idx_search_count", "search_count"),
        Index("idx_user_id", "user_id"),
    )


class StockReportCache(Base):
    """
    Stock report data cache model with detailed historical information.

    Caches comprehensive stock report data including historical prices,
    52-week ranges, and price changes to reduce API calls for report pages.

    Attributes:
        id: Primary key identifier
        symbol: Stock ticker symbol
        isin: International Securities Identification Number
        wkn: German securities identification number
        name: Company name
        current_price: Current stock price
        currency: Currency code
        exchange: Stock exchange name
        market_cap: Market capitalization
        sector: Business sector
        industry: Industry classification
        price_change_absolute: 1-day absolute price change
        price_change_percentage: 1-day percentage price change
        price_change_direction: Direction of price change (up/down/neutral)
        week_52_high: 52-week high price
        week_52_low: 52-week low price
        week_52_high_date: Date of 52-week high
        week_52_low_date: Date of 52-week low
        price_history_7d: JSON string of 7-day price history
        data_source: API source name
        raw_data: JSON string of raw API response
        created_at: Timestamp of cache entry creation
        updated_at: Timestamp of last update
        expires_at: Timestamp when cache expires (TTL)
        cache_hits: Number of times served from cache
    """

    __tablename__ = "stock_report_cache"

    id = Column(Integer, primary_key=True, index=True)

    # Stock identifiers
    symbol = Column(String(20), unique=True, index=True, nullable=False)
    isin = Column(String(12), index=True, nullable=True)
    wkn = Column(String(6), nullable=True)

    # Basic stock information
    name = Column(String(255), nullable=False)
    current_price = Column(Float, nullable=False)
    currency = Column(String(10), nullable=False)
    exchange = Column(String(50), nullable=False)

    # Additional metadata
    market_cap = Column(Float, nullable=True)
    sector = Column(String(100), nullable=True)
    industry = Column(String(100), nullable=True)

    # Price change (1-day)
    price_change_absolute = Column(Float, nullable=True)
    price_change_percentage = Column(Float, nullable=True)
    price_change_direction = Column(String(10), nullable=True)

    # 52-week range
    week_52_high = Column(Float, nullable=True)
    week_52_low = Column(Float, nullable=True)
    week_52_high_date = Column(String(30), nullable=True)
    week_52_low_date = Column(String(30), nullable=True)

    # Historical data (stored as JSON)
    price_history_7d = Column(Text, nullable=True)

    # API source tracking
    data_source = Column(String(50), nullable=False)
    raw_data = Column(Text, nullable=True)

    # Cache management
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )
    expires_at = Column(DateTime, nullable=False)
    cache_hits = Column(Integer, default=0, nullable=False)

    # Indexes for faster lookups
    __table_args__ = (
        Index("idx_report_symbol_expires", "symbol", "expires_at"),
        Index("idx_isin_expires_report", "isin", "expires_at"),
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


class UserFavorite(Base):
    """
    User favorite stocks model.

    Tracks user's favorite stocks for quick access.

    Attributes:
        id: Primary key identifier (UUID)
        user_id: User UUID from auth-service
        symbol: Stock ticker symbol
        added_at: Timestamp when favorite was added
    """

    __tablename__ = "user_favorites"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    symbol = Column(String(10), nullable=False, index=True)
    added_at = Column(DateTime, default=func.now(), nullable=False)

    __table_args__ = (
        Index("idx_user_favorites_user_id", "user_id"),
        Index("idx_user_favorites_symbol", "symbol"),
        Index("idx_user_favorites_user_symbol", "user_id", "symbol", unique=True),
    )


class SymbolMapping(Base):
    """
    Symbol mapping model for ISIN/WKN to ticker symbol resolution.

    Stores mappings between international identifiers and stock ticker symbols
    to enable fast lookups without external API calls.

    Attributes:
        id: Primary key identifier
        identifier_type: Type of identifier (isin, wkn, or name)
        identifier_value: The identifier value (e.g., US0378331005, 865985)
        yahoo_symbol: Corresponding ticker symbol (e.g., AAPL, TSLA)
        stock_name: Company name for reference
        exchange: Stock exchange (e.g., NASDAQ, NYSE, XETRA)
        priority: Priority for multiple mappings (higher = preferred)
        is_active: Whether this mapping is currently active
        verified_at: Last time this mapping was verified to work
        created_at: Timestamp of mapping creation
        updated_at: Timestamp of last update
    """

    __tablename__ = "symbol_mappings"

    id = Column(Integer, primary_key=True, index=True)

    identifier_type = Column(String(10), nullable=False, index=True)
    identifier_value = Column(String(50), nullable=False, index=True)
    yahoo_symbol = Column(String(20), nullable=False)

    stock_name = Column(String(255), nullable=True)
    exchange = Column(String(50), nullable=True)

    priority = Column(Integer, default=0, nullable=False)
    is_active = Column(Integer, default=1, nullable=False)
    verified_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        Index("idx_mapping_type_value", "identifier_type", "identifier_value"),
        Index("idx_mapping_yahoo_symbol", "yahoo_symbol"),
        Index("idx_mapping_active", "is_active"),
    )


class StockSearchIndex(Base):
    """
    Optimized stock search index model.

    Denormalized table optimized for ultra-fast search with full-text
    and fuzzy matching capabilities. Includes pre-computed popularity scores
    and PostgreSQL tsvector for intelligent search ranking.

    This table is designed for read-heavy workloads with comprehensive indices
    for exact, prefix, and fuzzy matching. The search_vector column is
    automatically maintained via database triggers.

    Attributes:
        id: Primary key identifier
        symbol: Stock ticker symbol (e.g., AAPL, TSLA)
        name: Company name (e.g., Apple Inc.)
        exchange: Stock exchange (e.g., NASDAQ, NYSE)
        security_type: Security type (e.g., Common Stock, ETF, REIT)
        market_cap: Market capitalization in USD
        avg_volume: Average daily trading volume
        sector: Business sector (e.g., Technology, Healthcare)
        industry: Industry classification (e.g., Consumer Electronics)
        isin: International Securities Identification Number
        wkn: German securities identification number
        popularity_score: Computed popularity score (0-200) based on:
            - Search frequency (0-100)
            - Market cap percentile (0-100)
        search_vector: PostgreSQL tsvector for full-text search
            - Symbol weighted 'A' (highest)
            - Name weighted 'B'
            - Exchange weighted 'C'
            - Sector weighted 'D' (lowest)
        created_at: Timestamp of index entry creation
        updated_at: Timestamp of last update
    """

    __tablename__ = "stock_search_index"

    id = Column(Integer, primary_key=True, index=True)

    # Core identifiers
    symbol = Column(String(20), nullable=False, index=True)
    name = Column(String(255), nullable=False, index=True)
    exchange = Column(String(50), nullable=True)
    security_type = Column(String(50), nullable=True)

    # Market data
    market_cap = Column(Float, nullable=True)
    avg_volume = Column(BigInteger, nullable=True)
    sector = Column(String(100), nullable=True)
    industry = Column(String(100), nullable=True)

    # Alternative identifiers
    isin = Column(String(12), nullable=True, index=True)
    wkn = Column(String(6), nullable=True, index=True)

    # Search optimization fields
    popularity_score = Column(Float, nullable=False, default=0, server_default="0")
    search_vector = Column(TSVECTOR, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )

    # Composite indices defined in migration
    __table_args__ = (
        Index("idx_search_symbol", "symbol"),
        Index("idx_search_name", "name"),
        Index("idx_search_isin", "isin"),
        Index("idx_search_wkn", "wkn"),
        Index("idx_search_symbol_exchange", "symbol", "exchange", unique=True),
        Index("idx_search_popularity", "popularity_score"),
        # GIN indices for full-text and trigram search defined in migration
    )
