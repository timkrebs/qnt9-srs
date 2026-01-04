"""
Unit tests for domain entities.

Tests for Stock, StockIdentifier, StockPrice, and StockMetadata.
"""

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from app.domain.entities import (DataSource, IdentifierType, Stock,
                                 StockIdentifier, StockMetadata, StockPrice)


class TestStockIdentifier:
    """Tests for StockIdentifier value object."""

    def test_valid_isin(self):
        """Test valid ISIN creation."""
        identifier = StockIdentifier(isin="US0378331005")
        assert identifier.isin == "US0378331005"
        assert identifier.get_primary_identifier() == (
            IdentifierType.ISIN,
            "US0378331005",
        )

    def test_invalid_isin_format(self):
        """Test invalid ISIN format raises ValueError."""
        with pytest.raises(ValueError, match="Invalid ISIN format"):
            StockIdentifier(isin="INVALID")

    def test_valid_wkn(self):
        """Test valid WKN creation."""
        identifier = StockIdentifier(wkn="865985")
        assert identifier.wkn == "865985"
        assert identifier.get_primary_identifier() == (IdentifierType.WKN, "865985")

    def test_invalid_wkn_format(self):
        """Test invalid WKN format raises ValueError."""
        with pytest.raises(ValueError, match="Invalid WKN format"):
            StockIdentifier(wkn="12345")  # Too short

    def test_valid_symbol(self):
        """Test valid symbol creation."""
        identifier = StockIdentifier(symbol="AAPL")
        assert identifier.symbol == "AAPL"

    def test_detect_type_isin(self):
        """Test automatic type detection for ISIN."""
        assert StockIdentifier.detect_type("US0378331005") == IdentifierType.ISIN

    def test_detect_type_wkn(self):
        """Test automatic type detection for WKN."""
        assert StockIdentifier.detect_type("865985") == IdentifierType.WKN

    def test_detect_type_symbol(self):
        """Test automatic type detection for symbol."""
        assert StockIdentifier.detect_type("AAPL") == IdentifierType.SYMBOL

    def test_detect_type_name(self):
        """Test automatic type detection for company name."""
        assert StockIdentifier.detect_type("Apple Inc") == IdentifierType.NAME

    def test_at_least_one_identifier_required(self):
        """Test that at least one identifier must be provided."""
        with pytest.raises(ValueError, match="At least one identifier"):
            StockIdentifier()


class TestStockPrice:
    """Tests for StockPrice value object."""

    def test_valid_price(self):
        """Test valid price creation."""
        price = StockPrice(current=Decimal("175.50"), currency="USD")
        assert price.current == Decimal("175.50")
        assert price.currency == "USD"

    def test_price_must_be_positive(self):
        """Test that price must be positive."""
        with pytest.raises(ValueError, match="must be positive"):
            StockPrice(current=Decimal("-10.00"), currency="USD")

    def test_currency_must_be_3_letters(self):
        """Test that currency must be 3-letter code."""
        with pytest.raises(ValueError, match="3-letter code"):
            StockPrice(current=Decimal("100.00"), currency="DOLLAR")

    def test_calculate_change_percent(self):
        """Test percentage change calculation."""
        price = StockPrice(
            current=Decimal("110.00"), currency="USD", previous_close=Decimal("100.00")
        )
        change_pct = price.calculate_change_percent()
        assert change_pct == Decimal("10.0")

    def test_calculate_change_percent_no_previous(self):
        """Test change calculation with no previous close."""
        price = StockPrice(current=Decimal("100.00"), currency="USD")
        assert price.calculate_change_percent() is None


class TestStockMetadata:
    """Tests for StockMetadata value object."""

    def test_metadata_creation(self):
        """Test metadata creation with various fields."""
        metadata = StockMetadata(
            exchange="NASDAQ",
            sector="Technology",
            industry="Consumer Electronics",
            market_cap=Decimal("2800000000000"),
        )
        assert metadata.exchange == "NASDAQ"
        assert metadata.sector == "Technology"
        assert metadata.market_cap == Decimal("2800000000000")


class TestStock:
    """Tests for Stock aggregate root."""

    @pytest.fixture
    def sample_stock(self):
        """Create a sample stock for testing."""
        identifier = StockIdentifier(
            isin="US0378331005", wkn="865985", symbol="AAPL", name="Apple Inc."
        )

        price = StockPrice(
            current=Decimal("175.50"), currency="USD", previous_close=Decimal("174.00")
        )

        metadata = StockMetadata(exchange="NASDAQ", sector="Technology")

        return Stock(
            identifier=identifier,
            price=price,
            metadata=metadata,
            data_source=DataSource.YAHOO_FINANCE,
            last_updated=datetime.now(timezone.utc),
        )

    def test_stock_creation(self, sample_stock):
        """Test stock aggregate creation."""
        assert sample_stock.identifier.symbol == "AAPL"
        assert sample_stock.price.current == Decimal("175.50")
        assert sample_stock.data_source == DataSource.YAHOO_FINANCE

    def test_is_stale_fresh_data(self, sample_stock):
        """Test stale check for fresh data."""
        sample_stock.cache_age_seconds = 60
        assert not sample_stock.is_stale(max_age_seconds=300)

    def test_is_stale_old_data(self, sample_stock):
        """Test stale check for old data."""
        sample_stock.cache_age_seconds = 600
        assert sample_stock.is_stale(max_age_seconds=300)

    def test_to_dict(self, sample_stock):
        """Test conversion to dictionary."""
        data = sample_stock.to_dict()

        assert data["identifier"]["symbol"] == "AAPL"
        assert data["price"]["current"] == 175.50
        assert data["metadata"]["exchange"] == "NASDAQ"
        assert data["data_source"] == "yahoo"
