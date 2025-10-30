"""
HTTP Client for Search Service API
"""
import logging
from typing import Any, Dict, List

import httpx

from .config import settings

logger = logging.getLogger(__name__)


class SearchServiceClient:
    """Client for interacting with the search-service API"""

    def __init__(self):
        self.base_url = settings.SEARCH_SERVICE_URL
        self.timeout = 2.0  # 2-second timeout as per requirements

    async def search(self, query: str) -> Dict[str, Any]:
        """
        Search for stock by ISIN/WKN/Symbol

        Args:
            query: ISIN, WKN, or symbol to search

        Returns:
            Dictionary with search results or error
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                logger.info(f"Searching for: {query}")
                response = await client.get(
                    f"{self.base_url}/api/stocks/search", params={"query": query}
                )
                response.raise_for_status()
                result = response.json()

                logger.info(
                    f"Search completed: {result.get('success', False)} "
                    f"({result.get('response_time_ms', 0)}ms)"
                )

                return result

        except (httpx.TimeoutException, TimeoutError) as e:
            logger.error(f"Search timed out for query: {query} - {e}")
            return {
                "success": False,
                "message": "Search request timed out. Please try again.",
                "query_type": "unknown",
                "response_time_ms": 2000,
            }
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error during search: {e}")
            return {
                "success": False,
                "message": f"Search service error: {e.response.status_code}",
                "query_type": "unknown",
                "response_time_ms": 0,
            }
        except Exception as e:
            logger.error(f"Unexpected error during search: {e}")
            return {
                "success": False,
                "message": "An unexpected error occurred. Please try again later.",
                "query_type": "unknown",
                "response_time_ms": 0,
            }

    async def get_suggestions(self, query: str, limit: int = 5) -> List[str]:
        """
        Get autocomplete suggestions

        Args:
            query: Partial query string
            limit: Maximum number of suggestions

        Returns:
            List of suggestion strings
        """
        if not query or len(query) < 1:
            return []

        try:
            async with httpx.AsyncClient(timeout=1.0) as client:
                response = await client.get(
                    f"{self.base_url}/api/stocks/suggestions",
                    params={"query": query, "limit": limit},
                )
                response.raise_for_status()
                result = response.json()
                return result.get("suggestions", [])

        except Exception as e:
            logger.debug(f"Error getting suggestions: {e}")
            return []

    async def health_check(self) -> bool:
        """
        Check if search service is healthy

        Returns:
            True if service is healthy
        """
        try:
            async with httpx.AsyncClient(timeout=1.0) as client:
                response = await client.get(f"{self.base_url}/health")
                return response.status_code == 200
        except Exception:
            return False


# Singleton instance
search_client = SearchServiceClient()
