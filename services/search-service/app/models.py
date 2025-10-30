"""
Database models for search service
"""
from datetime import datetime
from typing import Any

from sqlalchemy import Column, DateTime, Float, Index, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base: Any = declarative_base()


class StockCache(Base):
    """
    Stock data cache with TTL management
    Stores fetched stock data to reduce external API calls
    """

    __tablename__ = "stock_cache"

    id = Column(Integer, primary_key=True, index=True)
    # Search identifiers
    isin = Column(String(12), unique=True, index=True, nullable=True)
    wkn = Column(String(6), index=True, nullable=True)
    symbol = Column(String(20), index=True, nullable=False)

    # Stock information
    name = Column(String(255), nullable=False)
    current_price = Column(Float, nullable=True)
    currency = Column(String(10), nullable=True)
    exchange = Column(String(50), nullable=True)

    # Additional metadata
    market_cap = Column(Float, nullable=True)
    sector = Column(String(100), nullable=True)
    industry = Column(String(100), nullable=True)

    # API source tracking
    data_source = Column(String(50), nullable=False)  # 'yahoo' or 'alphavantage'
    raw_data = Column(Text, nullable=True)  # Store JSON for debugging

    # Cache management
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    expires_at = Column(DateTime, nullable=False)  # TTL: 5 minutes from creation
    cache_hits = Column(Integer, default=0, nullable=False)

    # Composite indexes for faster lookups
    __table_args__ = (
        Index("idx_isin_expires", "isin", "expires_at"),
        Index("idx_wkn_expires", "wkn", "expires_at"),
        Index("idx_symbol_expires", "symbol", "expires_at"),
    )

    def is_expired(self) -> bool:
        """Check if cache entry has expired"""
        return datetime.utcnow() > self.expires_at

    def increment_hits(self):
        """Track cache hit count"""
        self.cache_hits += 1


class APIRateLimit(Base):
    """
    Track API rate limiting
    Helps manage Yahoo Finance (5 req/sec) and Alpha Vantage (5 req/min) limits
    """

    __tablename__ = "api_rate_limits"

    id = Column(Integer, primary_key=True, index=True)
    api_name = Column(
        String(50), unique=True, index=True, nullable=False
    )  # 'yahoo' or 'alphavantage'
    requests_made = Column(Integer, default=0, nullable=False)
    window_start = Column(DateTime, default=func.now(), nullable=False)
    last_request = Column(DateTime, nullable=True)

    # Rate limit configuration
    max_requests = Column(Integer, nullable=False)  # Max requests per window
    window_seconds = Column(Integer, nullable=False)  # Time window in seconds

    __table_args__ = (Index("idx_api_window", "api_name", "window_start"),)


class SearchHistory(Base):
    """
    Track search queries for analytics and suggestions
    Helps provide autocomplete suggestions
    """

    __tablename__ = "search_history"

    id = Column(Integer, primary_key=True, index=True)
    query = Column(String(20), index=True, nullable=False)
    query_type = Column(String(10), nullable=False)  # 'isin' or 'wkn'
    result_found = Column(Integer, default=0, nullable=False)  # Boolean: 1 = found, 0 = not found
    search_count = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    last_searched = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index("idx_query_type", "query", "query_type"),
        Index("idx_search_count", "search_count"),
    )
