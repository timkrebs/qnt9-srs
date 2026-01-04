"""add stock cache and search history tables

Revision ID: 002_add_core_tables
Revises: 001_add_stock_report_cache
Create Date: 2025-11-11 12:00:00.000000

"""

from alembic import op
from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text
from sqlalchemy.sql import func

# revision identifiers, used by Alembic.
revision = "002_add_core_tables"
down_revision = "001_add_stock_report_cache"
branch_labels = None
depends_on = None


def upgrade():
    # First, rename index on stock_report_cache to avoid conflict
    op.drop_index("idx_symbol_expires", table_name="stock_report_cache")
    op.create_index(
        "idx_report_symbol_expires", "stock_report_cache", ["symbol", "expires_at"]
    )
    op.drop_index("idx_isin_expires_report", table_name="stock_report_cache")
    op.create_index(
        "idx_report_isin_expires", "stock_report_cache", ["isin", "expires_at"]
    )

    # Create stock_cache table
    op.create_table(
        "stock_cache",
        Column("id", Integer, primary_key=True, index=True),
        Column("isin", String(12), index=True, nullable=True),
        Column("wkn", String(6), index=True, nullable=True),
        Column("symbol", String(20), index=True, nullable=True),
        Column("name", String(255), index=True, nullable=True),
        Column("current_price", Float, nullable=True),
        Column("currency", String(10), nullable=True),
        Column("exchange", String(50), nullable=True),
        Column("market_cap", Float, nullable=True),
        Column("sector", String(100), nullable=True),
        Column("industry", String(100), nullable=True),
        Column("data_source", String(50), nullable=True),
        Column("raw_data", Text, nullable=True),
        Column("created_at", DateTime, default=func.now(), nullable=False),
        Column(
            "updated_at",
            DateTime,
            default=func.now(),
            onupdate=func.now(),
            nullable=False,
        ),
        Column("expires_at", DateTime, nullable=True),
        Column("cache_hits", Integer, default=0, nullable=False),
    )

    # Create composite indexes for stock_cache
    op.create_index("idx_symbol_expires", "stock_cache", ["symbol", "expires_at"])
    op.create_index("idx_isin_expires", "stock_cache", ["isin", "expires_at"])
    op.create_index("idx_wkn_expires", "stock_cache", ["wkn", "expires_at"])

    # Create search_history table
    op.create_table(
        "search_history",
        Column("id", Integer, primary_key=True, index=True),
        Column("query", String(255), index=True, nullable=False),
        Column("query_type", String(20), nullable=False),
        Column("result_symbol", String(20), nullable=True),
        Column("result_isin", String(12), nullable=True),
        Column("result_wkn", String(6), nullable=True),
        Column("success", Boolean, default=True, nullable=False),
        Column("cache_hit", Boolean, default=False, nullable=False),
        Column("data_source", String(50), nullable=True),
        Column("response_time_ms", Integer, nullable=True),
        Column("error_message", Text, nullable=True),
        Column("searched_at", DateTime, default=func.now(), nullable=False),
        Column("search_count", Integer, default=1, nullable=False),
        Column(
            "last_searched_at",
            DateTime,
            default=func.now(),
            onupdate=func.now(),
            nullable=False,
        ),
    )

    # Create composite indexes for search_history
    op.create_index("idx_query_type", "search_history", ["query", "query_type"])
    op.create_index("idx_search_count", "search_history", ["search_count"])

    # Create api_rate_limits table
    op.create_table(
        "api_rate_limits",
        Column("id", Integer, primary_key=True, index=True),
        Column("api_name", String(50), index=True, nullable=False),
        Column("window_start", DateTime, nullable=False),
        Column("request_count", Integer, default=0, nullable=False),
        Column("last_request_at", DateTime, nullable=True),
    )

    # Create composite index for api_rate_limits
    op.create_index("idx_api_window", "api_rate_limits", ["api_name", "window_start"])


def downgrade():
    # Drop api_rate_limits
    op.drop_index("idx_api_window", table_name="api_rate_limits")
    op.drop_table("api_rate_limits")

    # Drop search_history
    op.drop_index("idx_search_count", table_name="search_history")
    op.drop_index("idx_query_type", table_name="search_history")
    op.drop_table("search_history")

    # Drop stock_cache
    op.drop_index("idx_wkn_expires", table_name="stock_cache")
    op.drop_index("idx_isin_expires", table_name="stock_cache")
    op.drop_index("idx_symbol_expires", table_name="stock_cache")
    op.drop_table("stock_cache")

    # Restore original indexes on stock_report_cache
    op.drop_index("idx_report_symbol_expires", table_name="stock_report_cache")
    op.create_index(
        "idx_symbol_expires", "stock_report_cache", ["symbol", "expires_at"]
    )
    op.drop_index("idx_report_isin_expires", table_name="stock_report_cache")
    op.create_index(
        "idx_isin_expires_report", "stock_report_cache", ["isin", "expires_at"]
    )
