"""
Add stock_report_cache table for comprehensive report data caching.

Revision ID: 001_add_stock_report_cache
Revises: 
Create Date: 2025-11-02 12:00:00.000000
"""

from alembic import op
from sqlalchemy import Column, DateTime, Float, Integer, String, Text
from sqlalchemy.sql import func

# revision identifiers, used by Alembic.
revision = "001_add_stock_report_cache"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """
    Create stock_report_cache table for storing comprehensive stock report data.

    This table extends the basic stock cache with additional fields for:
    - 1-day price change (absolute, percentage, direction)
    - 52-week high/low range with dates
    - 7-day historical price data (JSON)
    - Extended metadata fields
    """
    op.create_table(
        "stock_report_cache",
        Column("id", Integer, primary_key=True, index=True),
        # Stock identifiers
        Column("symbol", String(20), unique=True, index=True, nullable=False),
        Column("isin", String(12), index=True, nullable=True),
        Column("wkn", String(6), nullable=True),
        # Basic stock information
        Column("name", String(255), nullable=False),
        Column("current_price", Float, nullable=False),
        Column("currency", String(10), nullable=False),
        Column("exchange", String(50), nullable=False),
        # Additional metadata
        Column("market_cap", Float, nullable=True),
        Column("sector", String(100), nullable=True),
        Column("industry", String(100), nullable=True),
        # Price change (1-day)
        Column("price_change_absolute", Float, nullable=True),
        Column("price_change_percentage", Float, nullable=True),
        Column("price_change_direction", String(10), nullable=True),
        # 52-week range
        Column("week_52_high", Float, nullable=True),
        Column("week_52_low", Float, nullable=True),
        Column("week_52_high_date", String(30), nullable=True),
        Column("week_52_low_date", String(30), nullable=True),
        # Historical data (stored as JSON)
        Column("price_history_7d", Text, nullable=True),
        # API source tracking
        Column("data_source", String(50), nullable=False),
        Column("raw_data", Text, nullable=True),
        # Cache management
        Column("created_at", DateTime, default=func.now(), nullable=False),
        Column(
            "updated_at",
            DateTime,
            default=func.now(),
            onupdate=func.now(),
            nullable=False,
        ),
        Column("expires_at", DateTime, nullable=False),
        Column("cache_hits", Integer, default=0, nullable=False),
    )

    # Create composite indexes for faster lookups
    op.create_index(
        "idx_symbol_expires", "stock_report_cache", ["symbol", "expires_at"]
    )

    op.create_index(
        "idx_isin_expires_report", "stock_report_cache", ["isin", "expires_at"]
    )


def downgrade():
    """
    Drop stock_report_cache table and its indexes.
    """
    op.drop_index("idx_isin_expires_report", table_name="stock_report_cache")
    op.drop_index("idx_symbol_expires", table_name="stock_report_cache")
    op.drop_table("stock_report_cache")
