"""
Tests for domain exceptions.

Simple tests to ensure exceptions work correctly.
"""

from app.domain.exceptions import (CacheException, DataIntegrityException,
                                   ExternalServiceException,
                                   StockNotFoundException, ValidationException)


class TestExceptions:
    """Test custom exceptions."""

    def test_validation_exception(self):
        """Test ValidationException."""
        exc = ValidationException("field", "value", "error message")
        assert "field" in str(exc)
        assert "error message" in str(exc)

    def test_stock_not_found_exception(self):
        """Test StockNotFoundException."""
        exc = StockNotFoundException("AAPL", "symbol")
        assert "AAPL" in str(exc)
        assert "symbol" in str(exc)

    def test_external_service_exception(self):
        """Test ExternalServiceException."""
        exc = ExternalServiceException("yahoo_finance", "API Error")
        assert "yahoo_finance" in str(exc)
        assert "API Error" in str(exc)

    def test_cache_exception(self):
        """Test CacheException."""
        exc = CacheException("redis", "Connection failed")
        assert "redis" in str(exc)
        assert "Connection failed" in str(exc)

    def test_data_integrity_exception(self):
        """Test DataIntegrityException."""
        exc = DataIntegrityException("Invalid data format", {"field": "value"})
        assert "Invalid data format" in str(exc)
