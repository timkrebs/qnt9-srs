"""
Add user features for authentication and favorites.

Revision ID: 003_add_user_features
Revises: 002_add_core_tables
Create Date: 2025-11-20

Changes:
- Add user_id column to search_history table
- Create user_favorites table
- Add indexes for efficient queries
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic
revision = "003_add_user_features"
down_revision = "002_add_core_tables"
branch_labels = None
depends_on = None


def upgrade():
    """
    Add user-specific features to support authentication and favorites.
    """
    # Add user_id column to search_history table
    # This allows tracking search history per user
    op.add_column(
        "search_history",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
    )

    # Create index on user_id for efficient user history queries
    op.create_index("idx_search_history_user_id", "search_history", ["user_id"])

    # Create user_favorites table
    # Stores user's favorite stocks for quick access
    op.create_table(
        "user_favorites",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("symbol", sa.String(length=10), nullable=False),
        sa.Column("added_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "symbol", name="uq_user_favorites_user_symbol"),
    )

    # Create indexes for user_favorites
    op.create_index("idx_user_favorites_user_id", "user_favorites", ["user_id"])

    op.create_index("idx_user_favorites_symbol", "user_favorites", ["symbol"])

    # Create composite index for efficient lookups
    op.create_index("idx_user_favorites_user_symbol", "user_favorites", ["user_id", "symbol"])


def downgrade():
    """
    Remove user-specific features.
    """
    # Drop user_favorites table and its indexes
    op.drop_index("idx_user_favorites_user_symbol", table_name="user_favorites")
    op.drop_index("idx_user_favorites_symbol", table_name="user_favorites")
    op.drop_index("idx_user_favorites_user_id", table_name="user_favorites")
    op.drop_table("user_favorites")

    # Drop user_id column from search_history
    op.drop_index("idx_search_history_user_id", table_name="search_history")
    op.drop_column("search_history", "user_id")
