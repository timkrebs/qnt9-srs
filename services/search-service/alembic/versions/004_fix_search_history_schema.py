"""fix search_history schema to match model

Revision ID: 004_fix_search_history_schema
Revises: 003_add_user_features
Create Date: 2025-11-21 11:22:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "004_fix_search_history_schema"
down_revision = "003_add_user_features"
branch_labels = None
depends_on = None


def upgrade():
    """
    Update search_history table to match the model definition.

    Changes:
    - Drop old columns: result_symbol, result_isin, result_wkn, success, cache_hit,
      data_source, response_time_ms, error_message
    - Add new columns: result_found, created_at, last_searched
    - Change query column from String(255) to String(20)
    - Change query_type column from String(20) to String(10)
    - Rename timestamp columns
    """

    # Drop old columns that are not in the model
    op.drop_column("search_history", "result_symbol")
    op.drop_column("search_history", "result_isin")
    op.drop_column("search_history", "result_wkn")
    op.drop_column("search_history", "success")
    op.drop_column("search_history", "cache_hit")
    op.drop_column("search_history", "data_source")
    op.drop_column("search_history", "response_time_ms")
    op.drop_column("search_history", "error_message")

    # Rename timestamp columns to match model
    op.alter_column("search_history", "searched_at", new_column_name="created_at")
    op.alter_column(
        "search_history", "last_searched_at", new_column_name="last_searched"
    )

    # Add result_found column
    op.add_column(
        "search_history",
        sa.Column("result_found", sa.Integer(), nullable=False, server_default="0"),
    )

    # Note: user_id already exists from migration 003_add_user_features

    # Alter column types to match model
    op.alter_column(
        "search_history",
        "query",
        existing_type=sa.String(255),
        type_=sa.String(20),
        existing_nullable=False,
    )

    op.alter_column(
        "search_history",
        "query_type",
        existing_type=sa.String(20),
        type_=sa.String(10),
        existing_nullable=False,
    )


def downgrade():
    """Revert changes back to old schema."""

    # Drop result_found column
    op.drop_column("search_history", "result_found")

    # Rename timestamp columns back
    op.alter_column("search_history", "created_at", new_column_name="searched_at")
    op.alter_column(
        "search_history", "last_searched", new_column_name="last_searched_at"
    )

    # Add old columns back
    op.add_column(
        "search_history", sa.Column("result_symbol", sa.String(20), nullable=True)
    )
    op.add_column(
        "search_history", sa.Column("result_isin", sa.String(12), nullable=True)
    )
    op.add_column(
        "search_history", sa.Column("result_wkn", sa.String(6), nullable=True)
    )
    op.add_column(
        "search_history",
        sa.Column("success", sa.Boolean(), nullable=False, server_default="true"),
    )
    op.add_column(
        "search_history",
        sa.Column("cache_hit", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "search_history", sa.Column("data_source", sa.String(50), nullable=True)
    )
    op.add_column(
        "search_history", sa.Column("response_time_ms", sa.Integer(), nullable=True)
    )
    op.add_column(
        "search_history", sa.Column("error_message", sa.Text(), nullable=True)
    )

    # Revert column types
    op.alter_column(
        "search_history",
        "query",
        existing_type=sa.String(20),
        type_=sa.String(255),
        existing_nullable=False,
    )

    op.alter_column(
        "search_history",
        "query_type",
        existing_type=sa.String(10),
        type_=sa.String(20),
        existing_nullable=False,
    )
