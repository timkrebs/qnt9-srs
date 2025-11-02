"""
HTTP client module for search service API.

Provides an async client for interacting with the search-service backend,
including search operations, suggestions, and health checks.
"""

from typing import Any, Dict, List, Optional

import httpx

from .config import settings
from .logging_config import get_logger

logger = get_logger(__name__)


class SearchServiceClient:
    """
    Client for interacting with the search-service API.

    Provides methods for stock search, autocomplete suggestions,
    and service health checks. All methods are async and include
    proper timeout and error handling.

    Attributes:
        base_url: Base URL of the search service
        timeout: Request timeout in seconds
        suggestion_timeout: Timeout for suggestion requests in seconds
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> None:
        """
        Initialize search service client.

        Args:
            base_url: Base URL of the search service (defaults to settings)
            timeout: Request timeout in seconds (defaults to settings)
        """
        self.base_url = base_url or settings.SEARCH_SERVICE_URL
        self.timeout = timeout or settings.REQUEST_TIMEOUT
        self.suggestion_timeout = 1.0

    async def search(self, query: str) -> Dict[str, Any]:
        """
        Search for stock by ISIN, WKN, or symbol.

        Performs a stock search using the provided query string.
        Handles timeouts and connection errors gracefully.

        Args:
            query: ISIN, WKN, or symbol to search for

        Returns:
            Dictionary containing search results with the following structure:
            {
                "success": bool,
                "data": dict (if successful),
                "message": str (if error),
                "query_type": str,
                "response_time_ms": int
            }

        Example:
            >>> client = SearchServiceClient()
            >>> result = await client.search("DE0005140008")
            >>> if result["success"]:
            ...     print(f"Found: {result['data']['name']}")
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                logger.info(f"Searching for stock: {query}")

                response = await client.get(
                    f"{self.base_url}/api/stocks/search",
                    params={"query": query},
                )
                response.raise_for_status()
                result = response.json()

                logger.info(
                    f"Search completed successfully: {result.get('success', False)} "
                    f"({result.get('response_time_ms', 0)}ms)"
                )

                return result

        except (httpx.TimeoutException, TimeoutError) as error:
            logger.error(f"Search timed out for query '{query}': {error}")
            return {
                "success": False,
                "message": "Search request timed out. Please try again.",
                "query_type": "unknown",
                "response_time_ms": int(self.timeout * 1000),
            }

        except httpx.HTTPStatusError as error:
            logger.error(
                f"HTTP error during search for query '{query}': "
                f"{error.response.status_code}"
            )
            return {
                "success": False,
                "message": f"Search service error: {error.response.status_code}",
                "detail": str(error),
                "query_type": "unknown",
                "response_time_ms": 0,
            }

        except httpx.ConnectError as error:
            logger.error(f"Connection error to search service: {error}")
            return {
                "success": False,
                "message": "Cannot connect to search service. Please try again later.",
                "detail": "Service unavailable",
                "query_type": "unknown",
                "response_time_ms": 0,
            }

        except Exception as error:
            logger.exception(f"Unexpected error during search for query '{query}'")
            return {
                "success": False,
                "message": "An unexpected error occurred. Please try again later.",
                "detail": str(error),
                "query_type": "unknown",
                "response_time_ms": 0,
            }

    async def get_suggestions(
        self,
        query: str,
        limit: int = 5,
    ) -> List[Any]:
        """
        Get autocomplete suggestions for partial query.

        Retrieves search suggestions based on previous successful searches
        to improve user experience with autocomplete functionality.

        Args:
            query: Partial search query string
            limit: Maximum number of suggestions to return

        Returns:
            List of suggestion objects. Returns empty list on error.
            Each suggestion contains query and metadata.

        Example:
            >>> client = SearchServiceClient()
            >>> suggestions = await client.get_suggestions("DE", limit=5)
            >>> for suggestion in suggestions:
            ...     print(suggestion["query"])
        """
        if not query or len(query) < 1:
            logger.debug("Empty query provided for suggestions")
            return []

        try:
            async with httpx.AsyncClient(timeout=self.suggestion_timeout) as client:
                logger.debug(f"Fetching suggestions for query: {query}")

                response = await client.get(
                    f"{self.base_url}/api/stocks/suggestions",
                    params={"query": query, "limit": limit},
                )
                response.raise_for_status()
                result = response.json()
                suggestions = result.get("suggestions", [])

                logger.debug(f"Retrieved {len(suggestions)} suggestions")
                return suggestions

        except Exception as error:
            logger.debug(f"Error getting suggestions for query '{query}': {error}")
            return []

    async def health_check(self) -> bool:
        """
        Check if search service is healthy and responding.

        Performs a health check by calling the service's health endpoint.
        Used for dependency monitoring and startup validation.

        Returns:
            True if service is healthy, False otherwise

        Example:
            >>> client = SearchServiceClient()
            >>> is_healthy = await client.health_check()
            >>> if not is_healthy:
            ...     print("Search service is down!")
        """
        try:
            async with httpx.AsyncClient(timeout=1.0) as client:
                response = await client.get(f"{self.base_url}/health")
                is_healthy = response.status_code == 200

                if is_healthy:
                    logger.debug("Search service health check: OK")
                else:
                    logger.warning(
                        f"Search service health check failed: {response.status_code}"
                    )

                return is_healthy

        except Exception as error:
            logger.warning(f"Search service health check failed: {error}")
            return False


# Singleton instance for application-wide use
search_client = SearchServiceClient()
