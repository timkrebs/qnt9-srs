"""
HTTP client module for search service API.

Provides an async client for interacting with the search-service backend,
including search operations, suggestions, and health checks. Implements
comprehensive logging, error handling, and request tracing for production use.
"""

import time
from typing import Any, Dict, List, Optional

import httpx

from .config import settings
from .logging_config import get_logger, get_request_id

logger = get_logger(__name__)


class SearchServiceError(Exception):
    """
    Base exception for search service errors.

    Attributes:
        message: Error message
        status_code: HTTP status code if applicable
        details: Additional error details
    """

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Initialize search service error.

        Args:
            message: Error message
            status_code: HTTP status code if applicable
            details: Additional error details
        """
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class SearchServiceClient:
    """
    Client for interacting with the search-service API.

    Provides methods for stock search, autocomplete suggestions,
    and service health checks. All methods are async and include
    proper timeout, error handling, and distributed tracing support.

    Uses a persistent HTTP client with connection pooling for improved
    performance (reduces TCP connection overhead by ~50-100ms per request).

    Attributes:
        base_url: Base URL of the search service
        timeout: Request timeout in seconds
        suggestion_timeout: Timeout for suggestion requests in seconds
        _client: Persistent httpx.AsyncClient with connection pooling
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
        self.suggestion_timeout = 3.0

        # Persistent HTTP client with connection pooling for performance
        # Limits: max 20 keepalive connections, max 100 total connections
        self._client: Optional[httpx.AsyncClient] = None

        logger.info(
            f"Initialized SearchServiceClient: base_url={self.base_url}, "
            f"timeout={self.timeout}s"
        )

    async def _get_client(self) -> httpx.AsyncClient:
        """
        Get or create the persistent HTTP client with connection pooling.

        Returns:
            Configured httpx.AsyncClient instance
        """
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                limits=httpx.Limits(
                    max_keepalive_connections=20,
                    max_connections=100,
                    keepalive_expiry=30.0,
                ),
                http2=True,  # Enable HTTP/2 for multiplexing
            )
            logger.debug("Created new HTTP client with connection pooling")
        return self._client

    async def close(self) -> None:
        """
        Close the HTTP client and release connections.

        Should be called during application shutdown.
        """
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
            logger.debug("Closed HTTP client")

    def _get_request_headers(self) -> Dict[str, str]:
        """
        Get common request headers including request ID for tracing.

        Returns:
            Dictionary of HTTP headers
        """
        headers = {
            "User-Agent": "QNT9-Frontend/1.0",
            "Accept": "application/json",
        }

        request_id = get_request_id()
        if request_id:
            headers["X-Request-ID"] = request_id

        return headers

    async def search(self, query: str) -> Dict[str, Any]:
        """
        Search for stock by ISIN, WKN, or symbol.

        Performs a stock search using the provided query string.
        Handles timeouts and connection errors gracefully with detailed logging.

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
        """
        start_time = time.perf_counter()

        logger.info(
            "Initiating stock search",
            extra={
                "extra_fields": {
                    "query": query,
                    "query_length": len(query),
                    "backend_url": self.base_url,
                    "timeout": self.timeout,
                }
            },
        )

        try:
            client = await self._get_client()
            request_url = f"{self.base_url}/api/v1/search"

            logger.debug(
                "Sending search request to backend",
                extra={
                    "extra_fields": {
                        "url": request_url,
                        "params": {"query": query},
                        "headers": self._get_request_headers(),
                    }
                },
            )

            response = await client.get(
                request_url,
                params={"query": query},
                headers=self._get_request_headers(),
            )

            duration_ms = (time.perf_counter() - start_time) * 1000

            logger.info(
                "Received response from search service",
                extra={
                    "extra_fields": {
                        "status_code": response.status_code,
                        "duration_ms": duration_ms,
                        "response_size": len(response.content),
                    }
                },
            )

            response.raise_for_status()
            result = response.json()

            if result.get("success"):
                stock_data = result.get("data", {})
                logger.info(
                    "Search successful",
                    extra={
                        "extra_fields": {
                            "query": query,
                            "stock_name": stock_data.get("name"),
                            "stock_symbol": stock_data.get("symbol"),
                            "query_type": result.get("query_type"),
                            "backend_response_time_ms": result.get("response_time_ms", 0),
                            "total_time_ms": duration_ms,
                        }
                    },
                )
            else:
                logger.warning(
                    "Search returned no results",
                    extra={
                        "extra_fields": {
                            "query": query,
                            "message": result.get("message"),
                            "duration_ms": duration_ms,
                        }
                    },
                )

            return result

        except (httpx.TimeoutException, TimeoutError) as error:
            duration_ms = (time.perf_counter() - start_time) * 1000

            logger.error(
                "Search request timed out",
                extra={
                    "extra_fields": {
                        "query": query,
                        "timeout": self.timeout,
                        "duration_ms": duration_ms,
                        "backend_url": self.base_url,
                        "error_type": type(error).__name__,
                    }
                },
            )

            return {
                "success": False,
                "message": f"Search request timed out after {self.timeout}s. "
                "The backend service may be overloaded or unresponsive.",
                "query_type": "unknown",
                "response_time_ms": int(duration_ms),
                "error_details": {
                    "error_type": "timeout",
                    "timeout_seconds": self.timeout,
                },
            }

        except httpx.HTTPStatusError as error:
            duration_ms = (time.perf_counter() - start_time) * 1000

            logger.error(
                "HTTP error from search service",
                extra={
                    "extra_fields": {
                        "query": query,
                        "status_code": error.response.status_code,
                        "response_body": error.response.text[:500],
                        "duration_ms": duration_ms,
                        "backend_url": self.base_url,
                    }
                },
            )

            return {
                "success": False,
                "message": f"Search service returned error: {error.response.status_code}",
                "detail": error.response.text[:200],
                "query_type": "unknown",
                "response_time_ms": int(duration_ms),
                "error_details": {
                    "error_type": "http_error",
                    "status_code": error.response.status_code,
                },
            }

        except httpx.ConnectError as error:
            duration_ms = (time.perf_counter() - start_time) * 1000

            logger.error(
                "Connection error to search service",
                extra={
                    "extra_fields": {
                        "query": query,
                        "backend_url": self.base_url,
                        "duration_ms": duration_ms,
                        "error_type": type(error).__name__,
                        "error_message": str(error),
                    }
                },
                exc_info=True,
            )

            return {
                "success": False,
                "message": "Cannot connect to search service. "
                "The backend may be offline or unreachable.",
                "detail": f"Connection failed to {self.base_url}",
                "query_type": "unknown",
                "response_time_ms": int(duration_ms),
                "error_details": {
                    "error_type": "connection_error",
                    "backend_url": self.base_url,
                },
            }

        except httpx.RequestError as error:
            duration_ms = (time.perf_counter() - start_time) * 1000

            logger.error(
                "Request error during search",
                extra={
                    "extra_fields": {
                        "query": query,
                        "backend_url": self.base_url,
                        "duration_ms": duration_ms,
                        "error_type": type(error).__name__,
                        "error_message": str(error),
                    }
                },
                exc_info=True,
            )

            return {
                "success": False,
                "message": "Network error occurred while communicating with search service.",
                "detail": str(error),
                "query_type": "unknown",
                "response_time_ms": int(duration_ms),
                "error_details": {
                    "error_type": "request_error",
                },
            }

        except Exception as error:
            duration_ms = (time.perf_counter() - start_time) * 1000

            logger.exception(
                "Unexpected error during search",
                extra={
                    "extra_fields": {
                        "query": query,
                        "duration_ms": duration_ms,
                        "error_type": type(error).__name__,
                    }
                },
            )

            return {
                "success": False,
                "message": "An unexpected error occurred. Please try again later.",
                "detail": str(error)[:200],
                "query_type": "unknown",
                "response_time_ms": int(duration_ms),
                "error_details": {
                    "error_type": "unexpected_error",
                },
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
        """
        if not query or len(query) < 1:
            logger.debug("Empty query provided for suggestions")
            return []

        start_time = time.perf_counter()

        try:
            client = await self._get_client()
            logger.debug(
                "Fetching suggestions",
                extra={
                    "extra_fields": {
                        "query": query,
                        "limit": limit,
                        "timeout": self.suggestion_timeout,
                    }
                },
            )

            response = await client.get(
                f"{self.base_url}/api/v1/suggestions",
                params={"query": query, "limit": limit},
                headers=self._get_request_headers(),
                timeout=self.suggestion_timeout,
            )

            duration_ms = (time.perf_counter() - start_time) * 1000

            response.raise_for_status()
            result = response.json()
            suggestions = result.get("suggestions", [])

            logger.debug(
                "Retrieved suggestions",
                extra={
                    "extra_fields": {
                        "query": query,
                        "suggestions_count": len(suggestions),
                        "duration_ms": duration_ms,
                    }
                },
            )

            return suggestions

        except Exception as error:
            duration_ms = (time.perf_counter() - start_time) * 1000

            logger.debug(
                "Error retrieving suggestions",
                extra={
                    "extra_fields": {
                        "query": query,
                        "error_type": type(error).__name__,
                        "duration_ms": duration_ms,
                    }
                },
            )
            return []

    async def health_check(self) -> bool:
        """
        Check if search service is healthy and responding.

        Performs a health check by calling the service's health endpoint.
        Used for dependency monitoring and startup validation.

        Returns:
            True if service is healthy, False otherwise
        """
        try:
            client = await self._get_client()
            response = await client.get(
                f"{self.base_url}/api/v1/health",
                headers=self._get_request_headers(),
                timeout=1.0,
            )
            is_healthy = response.status_code == 200

            if is_healthy:
                logger.debug(
                    "Search service health check passed",
                    extra={
                        "extra_fields": {
                            "backend_url": self.base_url,
                            "status_code": response.status_code,
                        }
                    },
                )
            else:
                logger.warning(
                    "Search service health check failed",
                    extra={
                        "extra_fields": {
                            "backend_url": self.base_url,
                            "status_code": response.status_code,
                            "response_body": response.text[:200],
                        }
                    },
                )

            return is_healthy

        except Exception as error:
            logger.warning(
                "Search service health check failed with exception",
                extra={
                    "extra_fields": {
                        "backend_url": self.base_url,
                        "error_type": type(error).__name__,
                        "error_message": str(error),
                    }
                },
            )
            return False


# Singleton instance for application-wide use
search_client = SearchServiceClient()
