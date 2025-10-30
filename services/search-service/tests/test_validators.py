"""
Unit tests for validators module
"""

import pytest
from pydantic import ValidationError

from app.validators import SearchQuery, detect_query_type, is_valid_isin, is_valid_wkn


class TestQueryTypeDetection:
    """Test query type detection logic"""

    def test_detect_isin(self):
        """Test ISIN detection"""
        assert detect_query_type("US0378331005") == "isin"
        assert detect_query_type("DE0005140008") == "isin"
        assert detect_query_type("GB0002374006") == "isin"

    def test_detect_wkn(self):
        """Test WKN detection"""
        assert detect_query_type("865985") == "wkn"
        assert detect_query_type("514000") == "wkn"
        assert detect_query_type("A1JWVX") == "wkn"

    def test_detect_symbol(self):
        """Test symbol detection"""
        assert detect_query_type("AAPL") == "symbol"
        assert detect_query_type("MSFT") == "symbol"
        assert detect_query_type("TSLA") == "symbol"
        assert detect_query_type("BRK.B") == "symbol"


class TestISINValidation:
    """Test ISIN validation logic"""

    def test_valid_isin(self):
        """Test valid ISIN codes"""
        assert is_valid_isin("US0378331005") is True  # Apple
        assert is_valid_isin("DE0005140008") is True  # Deutsche Bank
        assert is_valid_isin("GB0002374006") is True  # Diageo

    def test_invalid_isin_format(self):
        """Test invalid ISIN formats"""
        assert is_valid_isin("123456789012") is False  # Numbers only
        assert is_valid_isin("US037833100") is False  # Too short
        assert is_valid_isin("US03783310051") is False  # Too long
        assert is_valid_isin("1S0378331005") is False  # Starts with number
        assert is_valid_isin("") is False  # Empty
        assert is_valid_isin(None) is False  # None

    def test_invalid_isin_checksum(self):
        """Test ISIN with invalid checksum"""
        assert is_valid_isin("US0378331006") is False  # Wrong check digit
        assert is_valid_isin("US0378331004") is False  # Wrong check digit


class TestWKNValidation:
    """Test WKN validation logic"""

    def test_valid_wkn(self):
        """Test valid WKN codes"""
        assert is_valid_wkn("865985") is True  # Apple
        assert is_valid_wkn("514000") is True  # Deutsche Bank
        assert is_valid_wkn("A1JWVX") is True  # Alibaba

    def test_invalid_wkn_format(self):
        """Test invalid WKN formats"""
        assert is_valid_wkn("86598") is False  # Too short
        assert is_valid_wkn("8659851") is False  # Too long
        assert is_valid_wkn("") is False  # Empty
        assert is_valid_wkn(None) is False  # None
        assert is_valid_wkn("86598!") is False  # Special characters


class TestSearchQueryModel:
    """Test SearchQuery Pydantic model"""

    def test_valid_queries(self):
        """Test valid search queries"""
        # ISIN
        query = SearchQuery(query="US0378331005")
        assert query.query == "US0378331005"

        # WKN
        query = SearchQuery(query="865985")
        assert query.query == "865985"

        # Symbol
        query = SearchQuery(query="AAPL")
        assert query.query == "AAPL"

    def test_query_normalization(self):
        """Test that queries are normalized to uppercase"""
        query = SearchQuery(query="  aapl  ")
        assert query.query == "AAPL"

        query = SearchQuery(query="us0378331005")
        assert query.query == "US0378331005"

    def test_invalid_query_length(self):
        """Test query length validation"""
        with pytest.raises(ValidationError):
            SearchQuery(query="")  # Too short

        with pytest.raises(ValidationError):
            SearchQuery(query="A" * 21)  # Too long

    def test_invalid_query_format(self):
        """Test invalid query formats"""
        with pytest.raises(ValidationError):
            SearchQuery(query="INVALID@QUERY!")  # Special characters

        with pytest.raises(ValidationError):
            SearchQuery(query="ABC#123")  # Invalid special character
