"""add search optimization

Revision ID: 005_add_search_optimization
Revises: 004_fix_search_history_schema
Create Date: 2025-11-21

This migration adds comprehensive search optimization infrastructure:
1. Enables PostgreSQL pg_trgm extension for fuzzy matching
2. Creates stock_search_index table with normalized search data
3. Adds GIN indices for full-text and trigram search
4. Implements automatic search_vector maintenance via triggers
5. Populates initial data from stock_cache
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "005_add_search_optimization"
down_revision: Union[str, None] = "004_fix_search_history_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Apply search optimization changes.
    """
    # 1. Enable pg_trgm extension for fuzzy matching
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # 2. Create stock_search_index table (if not exists)
    # Check if table exists first
    connection = op.get_bind()
    inspector = sa.inspect(connection)

    if "stock_search_index" not in inspector.get_table_names():
        op.create_table(
            "stock_search_index",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("symbol", sa.String(length=20), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("exchange", sa.String(length=50), nullable=True),
            sa.Column("security_type", sa.String(length=50), nullable=True),
            sa.Column("market_cap", sa.Float(), nullable=True),
            sa.Column("avg_volume", sa.BigInteger(), nullable=True),
            sa.Column("sector", sa.String(length=100), nullable=True),
            sa.Column("industry", sa.String(length=100), nullable=True),
            sa.Column("isin", sa.String(length=12), nullable=True),
            sa.Column("wkn", sa.String(length=6), nullable=True),
            sa.Column("popularity_score", sa.Float(), nullable=False, server_default="0"),
            sa.Column("search_vector", postgresql.TSVECTOR(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )

        # 3. Create indices for optimal search performance

        # Primary search indices
        op.create_index("idx_search_symbol", "stock_search_index", ["symbol"])
        op.create_index("idx_search_name", "stock_search_index", ["name"])
        op.create_index("idx_search_isin", "stock_search_index", ["isin"])
        op.create_index("idx_search_wkn", "stock_search_index", ["wkn"])

        # Composite index for symbol + exchange uniqueness
        op.create_index(
            "idx_search_symbol_exchange", "stock_search_index", ["symbol", "exchange"], unique=True
        )

        # Popularity ranking index (DESC for top results first)
        op.create_index(
            "idx_search_popularity", "stock_search_index", [sa.text("popularity_score DESC")]
        )

        # GIN index for full-text search on search_vector
        op.create_index(
            "idx_search_vector_gin", "stock_search_index", ["search_vector"], postgresql_using="gin"
        )

        # GIN index for trigram fuzzy matching on name
        op.create_index(
            "idx_search_name_trigram",
            "stock_search_index",
            ["name"],
            postgresql_using="gin",
            postgresql_ops={"name": "gin_trgm_ops"},
        )

        # GIN index for trigram fuzzy matching on symbol
        op.create_index(
            "idx_search_symbol_trigram",
            "stock_search_index",
            ["symbol"],
            postgresql_using="gin",
            postgresql_ops={"symbol": "gin_trgm_ops"},
        )

        # 4. Create trigger function to maintain search_vector
        op.execute(
            """
            CREATE OR REPLACE FUNCTION update_search_vector() 
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.search_vector := 
                    setweight(to_tsvector('english', COALESCE(NEW.symbol, '')), 'A') ||
                    setweight(to_tsvector('english', COALESCE(NEW.name, '')), 'B') ||
                    setweight(to_tsvector('english', COALESCE(NEW.exchange, '')), 'C') ||
                    setweight(to_tsvector('english', COALESCE(NEW.sector, '')), 'D');
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
        """
        )

        # 5. Create trigger on INSERT and UPDATE
        op.execute(
            """
            CREATE TRIGGER trigger_update_search_vector
            BEFORE INSERT OR UPDATE ON stock_search_index
            FOR EACH ROW
            EXECUTE FUNCTION update_search_vector();
        """
        )

        # 6. Populate initial data from stock_cache
        # This calculates initial popularity based on cache hits and market cap
        op.execute(
            """
            INSERT INTO stock_search_index 
                (symbol, name, exchange, market_cap, sector, industry, isin, wkn, popularity_score)
            SELECT DISTINCT ON (symbol, exchange)
                symbol,
                name,
                exchange,
                market_cap,
                sector,
                industry,
                isin,
                wkn,
                -- Popularity calculation: normalize cache_hits (0-100) + normalize market_cap (0-100)
                LEAST(cache_hits::float / NULLIF((SELECT MAX(cache_hits) FROM stock_cache), 0) * 100, 100) +
                LEAST(COALESCE(market_cap, 0)::float / NULLIF((SELECT MAX(market_cap) FROM stock_cache WHERE market_cap IS NOT NULL), 0) * 100, 100)
                AS popularity_score
            FROM stock_cache
            WHERE symbol IS NOT NULL
            ORDER BY symbol, exchange, created_at DESC
            ON CONFLICT (symbol, exchange) DO UPDATE SET
                name = EXCLUDED.name,
                market_cap = EXCLUDED.market_cap,
                sector = EXCLUDED.sector,
                industry = EXCLUDED.industry,
                popularity_score = EXCLUDED.popularity_score,
                updated_at = now();
        """
        )

    # 7. Update search_history to track popularity (always run)
    # Add index on query for faster aggregation
    existing_indexes = [idx["name"] for idx in inspector.get_indexes("search_history")]
    if "idx_history_query_popularity" not in existing_indexes:
        op.create_index(
            "idx_history_query_popularity",
            "search_history",
            ["query", "result_found", "search_count"],
        )


def downgrade() -> None:
    """
    Rollback search optimization changes.
    """
    # Drop indices from search_history
    op.drop_index("idx_history_query_popularity", table_name="search_history")

    # Drop trigger and function
    op.execute("DROP TRIGGER IF EXISTS trigger_update_search_vector ON stock_search_index")
    op.execute("DROP FUNCTION IF EXISTS update_search_vector()")

    # Drop indices
    op.drop_index("idx_search_symbol_trigram", table_name="stock_search_index")
    op.drop_index("idx_search_name_trigram", table_name="stock_search_index")
    op.drop_index("idx_search_vector_gin", table_name="stock_search_index")
    op.drop_index("idx_search_popularity", table_name="stock_search_index")
    op.drop_index("idx_search_symbol_exchange", table_name="stock_search_index")
    op.drop_index("idx_search_wkn", table_name="stock_search_index")
    op.drop_index("idx_search_isin", table_name="stock_search_index")
    op.drop_index("idx_search_name", table_name="stock_search_index")
    op.drop_index("idx_search_symbol", table_name="stock_search_index")

    # Drop table
    op.drop_table("stock_search_index")

    # Note: We don't drop pg_trgm extension as other tables might be using it
    # To manually drop: DROP EXTENSION IF EXISTS pg_trgm;
