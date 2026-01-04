"""Add symbol mappings table

Revision ID: 006_add_symbol_mappings
Revises: 005_add_search_optimization
Create Date: 2026-01-04 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

revision = "006_add_symbol_mappings"
down_revision = "005_add_search_optimization"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create symbol_mappings table and populate with initial data."""
    op.create_table(
        "symbol_mappings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("identifier_type", sa.String(length=10), nullable=False),
        sa.Column("identifier_value", sa.String(length=50), nullable=False),
        sa.Column("yahoo_symbol", sa.String(length=20), nullable=False),
        sa.Column("stock_name", sa.String(length=255), nullable=True),
        sa.Column("exchange", sa.String(length=50), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("verified_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "idx_mapping_type_value",
        "symbol_mappings",
        ["identifier_type", "identifier_value"],
    )
    op.create_index("idx_mapping_yahoo_symbol", "symbol_mappings", ["yahoo_symbol"])
    op.create_index("idx_mapping_active", "symbol_mappings", ["is_active"])
    op.create_index(
        op.f("ix_symbol_mappings_id"), "symbol_mappings", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_symbol_mappings_identifier_type"),
        "symbol_mappings",
        ["identifier_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_symbol_mappings_identifier_value"),
        "symbol_mappings",
        ["identifier_value"],
        unique=False,
    )

    conn = op.get_bind()

    isin_mappings = [
        ("isin", "US0378331005", "AAPL", "Apple Inc.", "NASDAQ", 100),
        ("isin", "US5949181045", "MSFT", "Microsoft Corporation", "NASDAQ", 100),
        ("isin", "US02079K3059", "GOOGL", "Alphabet Inc.", "NASDAQ", 100),
        ("isin", "US0231351067", "AMZN", "Amazon.com Inc.", "NASDAQ", 100),
        ("isin", "US88160R1014", "TSLA", "Tesla Inc.", "NASDAQ", 100),
        ("isin", "US30303M1027", "META", "Meta Platforms Inc.", "NASDAQ", 100),
        ("isin", "US67066G1040", "NVDA", "NVIDIA Corporation", "NASDAQ", 100),
        ("isin", "DE0005190003", "BMW.DE", "Bayerische Motoren Werke AG", "XETRA", 100),
        ("isin", "DE0007664039", "VOW3.DE", "Volkswagen AG", "XETRA", 100),
        ("isin", "DE0007100000", "MBG.DE", "Mercedes-Benz Group AG", "XETRA", 100),
        ("isin", "DE0007164600", "SAP.DE", "SAP SE", "XETRA", 100),
        ("isin", "DE0007236101", "SIE.DE", "Siemens AG", "XETRA", 100),
        ("isin", "DE0005140008", "DBK.DE", "Deutsche Bank AG", "XETRA", 100),
        ("isin", "DE0008404005", "ALV.DE", "Allianz SE", "XETRA", 100),
    ]

    wkn_mappings = [
        ("wkn", "865985", "AAPL", "Apple Inc.", "NASDAQ", 100),
        ("wkn", "870747", "MSFT", "Microsoft Corporation", "NASDAQ", 100),
        ("wkn", "A14Y6F", "GOOGL", "Alphabet Inc.", "NASDAQ", 100),
        ("wkn", "906866", "AMZN", "Amazon.com Inc.", "NASDAQ", 100),
        ("wkn", "A1CX3T", "TSLA", "Tesla Inc.", "NASDAQ", 100),
        ("wkn", "A1JWVX", "META", "Meta Platforms Inc.", "NASDAQ", 100),
        ("wkn", "918422", "NVDA", "NVIDIA Corporation", "NASDAQ", 100),
        ("wkn", "519000", "BMW.DE", "Bayerische Motoren Werke AG", "XETRA", 100),
        ("wkn", "766403", "VOW3.DE", "Volkswagen AG", "XETRA", 100),
        ("wkn", "710000", "MBG.DE", "Mercedes-Benz Group AG", "XETRA", 100),
        ("wkn", "716460", "SAP.DE", "SAP SE", "XETRA", 100),
        ("wkn", "723610", "SIE.DE", "Siemens AG", "XETRA", 100),
        ("wkn", "514000", "DBK.DE", "Deutsche Bank AG", "XETRA", 100),
        ("wkn", "840400", "ALV.DE", "Allianz SE", "XETRA", 100),
    ]

    name_mappings = [
        ("name", "APPLE", "AAPL", "Apple Inc.", "NASDAQ", 100),
        ("name", "MICROSOFT", "MSFT", "Microsoft Corporation", "NASDAQ", 100),
        ("name", "GOOGLE", "GOOGL", "Alphabet Inc.", "NASDAQ", 100),
        ("name", "ALPHABET", "GOOGL", "Alphabet Inc.", "NASDAQ", 90),
        ("name", "AMAZON", "AMZN", "Amazon.com Inc.", "NASDAQ", 100),
        ("name", "TESLA", "TSLA", "Tesla Inc.", "NASDAQ", 100),
        ("name", "META", "META", "Meta Platforms Inc.", "NASDAQ", 100),
        ("name", "NVIDIA", "NVDA", "NVIDIA Corporation", "NASDAQ", 100),
        ("name", "BMW", "BMW.DE", "Bayerische Motoren Werke AG", "XETRA", 100),
        ("name", "VOLKSWAGEN", "VOW.DE", "Volkswagen AG", "XETRA", 100),
        ("name", "MERCEDES", "MBG.DE", "Mercedes-Benz Group AG", "XETRA", 100),
        ("name", "SAP", "SAP.DE", "SAP SE", "XETRA", 100),
        ("name", "SIEMENS", "SIE.DE", "Siemens AG", "XETRA", 100),
        ("name", "DEUTSCHE BANK", "DBK.DE", "Deutsche Bank AG", "XETRA", 100),
        ("name", "ALLIANZ", "ALV.DE", "Allianz SE", "XETRA", 100),
    ]

    all_mappings = isin_mappings + wkn_mappings + name_mappings

    for mapping in all_mappings:
        (
            identifier_type,
            identifier_value,
            yahoo_symbol,
            stock_name,
            exchange,
            priority,
        ) = mapping
        conn.execute(
            text(
                """
                INSERT INTO symbol_mappings 
                (identifier_type, identifier_value, yahoo_symbol, stock_name, exchange, priority, is_active)
                VALUES (:type, :value, :symbol, :name, :exchange, :priority, 1)
                """
            ),
            {
                "type": identifier_type,
                "value": identifier_value,
                "symbol": yahoo_symbol,
                "name": stock_name,
                "exchange": exchange,
                "priority": priority,
            },
        )


def downgrade() -> None:
    """Drop symbol_mappings table."""
    op.drop_index(
        op.f("ix_symbol_mappings_identifier_value"), table_name="symbol_mappings"
    )
    op.drop_index(
        op.f("ix_symbol_mappings_identifier_type"), table_name="symbol_mappings"
    )
    op.drop_index(op.f("ix_symbol_mappings_id"), table_name="symbol_mappings")
    op.drop_index("idx_mapping_active", table_name="symbol_mappings")
    op.drop_index("idx_mapping_yahoo_symbol", table_name="symbol_mappings")
    op.drop_index("idx_mapping_type_value", table_name="symbol_mappings")
    op.drop_table("symbol_mappings")
