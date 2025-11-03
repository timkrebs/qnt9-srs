"""
Helper functions for stock search operations.

This module contains utility functions for query validation,
response building, and search query analysis.
"""

import logging
import time
from typing import Any, Dict, List, Optional

from .validators import (
    SearchQuery,
    StockData,
    StockSearchResponse,
    detect_query_type,
    is_valid_isin,
    is_valid_wkn,
)

logger = logging.getLogger(__name__)

# Constants
MAX_RESPONSE_TIME_MS = 2000
MIN_COMPANY_NAME_LENGTH = 3
MAX_SYMBOL_LENGTH_THRESHOLD = 5
ISIN_LENGTH = 12


def is_potential_company_name(query: str) -> bool:
    """
    Determine if query appears to be a company name rather than an identifier.
    
    A query is considered a potential company name if it meets criteria
    indicating natural language input rather than structured identifiers.
    
    Criteria for company name:
        - Length >= 3 characters
        - Contains at least one letter
        - Has spaces, lowercase letters, or length > 5 characters
        - Does not match ISIN format (12 chars starting with 2 letters)
        - Not a short all-uppercase string (likely a symbol)
    
    Args:
        query: Search query string to analyze
        
    Returns:
        True if query appears to be a company name, False if likely an identifier
        
    Examples:
        >>> is_potential_company_name("Amazon")
        True
        >>> is_potential_company_name("Apple Inc")
        True
        >>> is_potential_company_name("microsoft")
        True
        >>> is_potential_company_name("AAPL")
        False
        >>> is_potential_company_name("US0378331005")
        False
    """
    if len(query) < MIN_COMPANY_NAME_LENGTH:
        return False
    
    if not any(c.isalpha() for c in query):
        return False
    
    # Strong indicators of company name
    if ' ' in query:
        return True
    
    if any(c.islower() for c in query):
        return True
    
    if len(query) > MAX_SYMBOL_LENGTH_THRESHOLD and query.isalpha():
        return True
    
    # Exclude ISIN format
    if _matches_isin_format(query):
        return False
    
    # Exclude short uppercase symbols
    if _is_short_symbol(query):
        return False
    
    return True


def _matches_isin_format(query: str) -> bool:
    """
    Check if query matches ISIN format structure.
    
    Args:
        query: Query string to check
        
    Returns:
        True if query matches ISIN format (12 chars, 2 letters + 10 alphanumeric)
    """
    return (
        len(query) == ISIN_LENGTH
        and query[:2].isalpha()
        and query[2:].isalnum()
    )


def _is_short_symbol(query: str) -> bool:
    """
    Check if query appears to be a short stock symbol.
    
    Args:
        query: Query string to check
        
    Returns:
        True if query looks like a stock symbol (short, uppercase, alphabetic)
    """
    return (
        query.isupper()
        and len(query) <= MAX_SYMBOL_LENGTH_THRESHOLD
        and query.isalpha()
    )


def validate_search_query(query: str) -> SearchQuery:
    """
    Validate and normalize search query using Pydantic model.
    
    Args:
        query: Raw search query string
        
    Returns:
        Validated SearchQuery instance
        
    Raises:
        ValidationError: If query format is invalid
    """
    return SearchQuery(query=query)


def validate_query_format(query: str, query_type: str) -> None:
    """
    Validate query format matches expected type.
    
    Args:
        query: Query string to validate
        query_type: Expected type ('isin', 'wkn', 'symbol', 'name')
        
    Raises:
        ValueError: If query doesn't match expected format
    """
    if query_type == "isin" and not is_valid_isin(query):
        raise ValueError(f"Invalid ISIN format: {query}")
    
    if query_type == "wkn" and not is_valid_wkn(query):
        raise ValueError(f"Invalid WKN format: {query}")


def build_success_response(
    stock_data: Dict[str, Any],
    query_type: str,
    start_time: float,
) -> StockSearchResponse:
    """
    Build successful search response with stock data.
    
    Args:
        stock_data: Stock information dictionary
        query_type: Type of query performed
        start_time: Request start timestamp
        
    Returns:
        StockSearchResponse with success status and data
    """
    response_time_ms = int((time.time() - start_time) * 1000)
    
    return StockSearchResponse(
        success=True,
        data=StockData(**stock_data),
        message="Data retrieved from external API",
        query_type=query_type,
        response_time_ms=response_time_ms,
    )


def build_cached_response(
    cached_data: Dict[str, Any],
    query_type: str,
    start_time: float,
    cache_age_seconds: int,
) -> StockSearchResponse:
    """
    Build response with cached stock data.
    
    Args:
        cached_data: Cached stock information
        query_type: Type of query performed
        start_time: Request start timestamp
        cache_age_seconds: Age of cached data in seconds
        
    Returns:
        StockSearchResponse with cached flag and age
    """
    response_time_ms = int((time.time() - start_time) * 1000)
    
    logger.info(f"Cache hit - age: {cache_age_seconds}s")
    
    stock_data_dict = dict(cached_data)
    stock_data_dict['cached'] = True
    stock_data_dict['cache_age_seconds'] = cache_age_seconds
    
    return StockSearchResponse(
        success=True,
        data=StockData(**stock_data_dict),
        message=f"Data retrieved from cache ({cache_age_seconds}s old)",
        query_type=query_type,
        response_time_ms=response_time_ms,
    )


def build_not_found_response(
    query: str,
    query_type: str,
    start_time: float,
    suggestions: Optional[List[str]] = None,
) -> StockSearchResponse:
    """
    Build response for stock not found scenario.
    
    Args:
        query: Original search query
        query_type: Type of query performed
        start_time: Request start timestamp
        suggestions: Optional list of suggested alternatives
        
    Returns:
        StockSearchResponse with success=False and suggestions
    """
    response_time_ms = int((time.time() - start_time) * 1000)
    
    logger.warning(f"Stock not found for query: {query} (type: {query_type})")
    
    return StockSearchResponse(
        success=False,
        data=None,
        message=f"No stock found for {query_type}: {query}",
        suggestions=suggestions or [],
        query_type=query_type,
        response_time_ms=response_time_ms,
    )


def get_search_suggestions(query: str, query_type: str) -> List[str]:
    """
    Generate search suggestions for failed queries.
    
    Args:
        query: Failed search query
        query_type: Type of failed query
        
    Returns:
        List of suggestion strings for the user
    """
    suggestions = []
    
    if query_type == "isin":
        suggestions.append("Check if ISIN is correct (12 characters, 2 letters + 10 alphanumeric)")
        suggestions.append("Try searching by WKN or stock symbol instead")
    elif query_type == "wkn":
        suggestions.append("Check if WKN is correct (6 alphanumeric characters)")
        suggestions.append("Try searching by ISIN or stock symbol instead")
    elif query_type == "symbol":
        suggestions.append("Try searching by company name (e.g., 'Apple', 'Microsoft')")
        suggestions.append("Check if symbol is correct (e.g., AAPL for Apple)")
    else:
        suggestions.append("Try a different company name or stock symbol")
        suggestions.append("Use ISIN or WKN for more precise search")
    
    return suggestions
