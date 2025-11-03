"""
Business logic service layer for stock search operations.

This module contains the core business logic for processing search requests,
coordinating between cache, API clients, and response building.
"""

import logging
from typing import Any, Dict, List, Optional

from .api_clients import StockAPIClient
from .cache import CacheManager
from .helpers import (
    build_cached_response,
    build_not_found_response,
    build_success_response,
    get_search_suggestions,
    is_potential_company_name,
    validate_query_format,
    validate_search_query,
)
from .validators import detect_query_type

logger = logging.getLogger(__name__)

# Constants
DEFAULT_NAME_SEARCH_LIMIT = 5


class StockSearchService:
    """
    Service class for stock search operations.
    
    Coordinates between cache, external APIs, and response building
    to provide comprehensive stock search functionality.
    """
    
    def __init__(self, api_client: StockAPIClient, cache_manager: CacheManager):
        """
        Initialize stock search service.
        
        Args:
            api_client: API client for external stock data
            cache_manager: Cache manager for data persistence
        """
        self.api_client = api_client
        self.cache_manager = cache_manager
    
    def search_by_identifier(
        self,
        query: str,
        query_type: str,
        start_time: float,
    ) -> Dict[str, Any]:
        """
        Search for stock by identifier (ISIN, WKN, or Symbol).
        
        Args:
            query: Search query string
            query_type: Type of identifier
            start_time: Request start timestamp
            
        Returns:
            Stock search response dictionary
        """
        # Validate format
        validate_query_format(query, query_type)
        
        # Check cache
        cached_data = self.cache_manager.get_cached_stock(query)
        if cached_data:
            cache_age = self.cache_manager.get_cache_age(cached_data)
            return build_cached_response(
                cached_data,
                query_type,
                start_time,
                cache_age,
            )
        
        # Fetch from API
        logger.info(f"Cache miss - fetching from API: {query}")
        stock_data = self.api_client.search_stock(query, query_type)
        
        if not stock_data:
            suggestions = get_search_suggestions(query, query_type)
            self.cache_manager.record_search(query, found=False)
            return build_not_found_response(
                query,
                query_type,
                start_time,
                suggestions,
            )
        
        # Save and return
        self.cache_manager.save_to_cache(stock_data, query)
        self.cache_manager.record_search(query, found=True)
        
        return build_success_response(stock_data, query_type, start_time)
    
    def search_by_company_name(
        self,
        query: str,
        start_time: float,
        limit: int = DEFAULT_NAME_SEARCH_LIMIT,
    ) -> Dict[str, Any]:
        """
        Search for stock by company name.
        
        Performs name search to find matching symbol, then fetches
        complete stock data for that symbol.
        
        Args:
            query: Company name to search
            start_time: Request start timestamp
            limit: Maximum number of search results to consider
            
        Returns:
            Stock search response dictionary with complete data
        """
        logger.info(f"Company name search: {query}")
        
        # Search for matching companies
        search_results = self._search_companies(query, limit)
        
        if not search_results:
            return build_not_found_response(
                query,
                "name",
                start_time,
                ["Try a different company name", "Use stock symbol for precise search"],
            )
        
        # Get best match
        best_match = search_results[0]
        symbol = best_match['symbol']
        
        logger.info(f"Found symbol {symbol} for query '{query}', fetching data...")
        
        # Fetch complete data for symbol
        stock_data = self.api_client.search_stock(symbol, query_type="symbol")
        
        if stock_data:
            self.cache_manager.save_to_cache(stock_data, symbol)
            self.cache_manager.record_search(query, found=True)
            return build_success_response(stock_data, "name", start_time)
        
        # Fallback to basic search result
        logger.warning(f"Could not fetch full data for {symbol}, using search result")
        return self._build_basic_response(best_match, query, start_time)
    
    def _search_companies(
        self,
        query: str,
        limit: int,
    ) -> List[Dict[str, Any]]:
        """
        Search for companies by name using API.
        
        Args:
            query: Company name query
            limit: Maximum results to return
            
        Returns:
            List of company search results
        """
        try:
            # Check cache for name search results
            cached_results = self.cache_manager.get_name_search_cache(query)
            if cached_results:
                logger.info(f"Name search cache hit for: {query}")
                return cached_results[:limit]
            
            # Fetch from API
            results = self.api_client.search_by_name(query, limit=limit)
            
            # Cache results
            if results:
                self.cache_manager.save_name_search_cache(query, results)
            
            return results
            
        except Exception as e:
            logger.error(f"Company search error for '{query}': {e}")
            return []
    
    def _build_basic_response(
        self,
        search_result: Dict[str, Any],
        query: str,
        start_time: float,
    ) -> Dict[str, Any]:
        """
        Build response from basic search result when full data unavailable.
        
        Args:
            search_result: Basic search result data
            query: Original query
            start_time: Request start timestamp
            
        Returns:
            Stock search response dictionary
        """
        stock_data = {
            'symbol': search_result['symbol'],
            'name': search_result['name'],
            'isin': search_result.get('isin'),
            'wkn': search_result.get('wkn'),
            'current_price': search_result.get('current_price'),
            'currency': search_result.get('currency'),
            'exchange': search_result.get('exchange', ''),
            'source': 'yahoo_search',
            'cached': False,
        }
        
        self.cache_manager.save_to_cache(stock_data, stock_data['symbol'])
        self.cache_manager.record_search(query, found=True)
        
        return build_success_response(stock_data, "name", start_time)
