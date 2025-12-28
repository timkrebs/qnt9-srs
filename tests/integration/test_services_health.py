"""
Integration tests for existing QNT9 services.

Tests the actual deployed services:
- auth-service (port 8010)
- user-service (port 8011)
- search-service (port 8000)
- frontend-service (port 8080)
"""


import httpx
import pytest

# Service endpoints
SERVICE_URLS = {
    "auth": "http://localhost:8010",
    "user": "http://localhost:8011",
    "search": "http://localhost:8000",
    "frontend": "http://localhost:8080",
}


class TestServiceHealth:
    """Test that all deployed services are healthy and reachable."""

    @pytest.mark.asyncio
    async def test_all_services_healthy(self):
        """Verify all services respond to health checks."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            services = {
                "Auth Service": f"{SERVICE_URLS['auth']}/health",
                "User Service": f"{SERVICE_URLS['user']}/health",
                "Search Service": f"{SERVICE_URLS['search']}/api/v1/health",
                "Frontend Service": f"{SERVICE_URLS['frontend']}/health",
            }

            results = {}
            for service_name, health_url in services.items():
                try:
                    response = await client.get(health_url)
                    results[service_name] = {
                        "status_code": response.status_code,
                        "healthy": response.status_code == 200,
                        "data": response.json() if response.status_code == 200 else None,
                    }
                except Exception as e:
                    results[service_name] = {"status_code": None, "healthy": False, "error": str(e)}

            # Check all services are healthy
            for service_name, result in results.items():
                assert result["healthy"], f"{service_name} unhealthy: {result}"

    @pytest.mark.asyncio
    async def test_auth_service_endpoints(self):
        """Test auth service basic endpoints."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Health check
            response = await client.get(f"{SERVICE_URLS['auth']}/health")
            assert response.status_code == 200
            data = response.json()
            assert data.get("status") == "healthy"

    @pytest.mark.asyncio
    async def test_user_service_endpoints(self):
        """Test user service basic endpoints."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Health check
            response = await client.get(f"{SERVICE_URLS['user']}/health")
            assert response.status_code == 200
            data = response.json()
            assert data.get("status") == "healthy"

    @pytest.mark.asyncio
    async def test_search_service_endpoints(self):
        """Test search service basic endpoints."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Health check
            response = await client.get(f"{SERVICE_URLS['search']}/api/v1/health")
            assert response.status_code == 200
            data = response.json()
            assert data.get("status") in ["healthy", "ok"]

    @pytest.mark.asyncio
    async def test_frontend_service_endpoints(self):
        """Test frontend service basic endpoints."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Health check
            response = await client.get(f"{SERVICE_URLS['frontend']}/health")
            assert response.status_code == 200
            data = response.json()
            assert data.get("status") == "healthy"


class TestServiceIntegration:
    """Test integration between services."""

    @pytest.mark.asyncio
    async def test_search_service_can_query_stocks(self):
        """Test search service can search for stocks."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Search for a stock
            response = await client.get(
                f"{SERVICE_URLS['search']}/api/v1/search", params={"query": "AAPL"}
            )

            # Should return 200 or 404 if no results
            assert response.status_code in [
                200,
                404,
            ], f"Unexpected status code: {response.status_code}"

            if response.status_code == 200:
                data = response.json()
                # Verify response structure
                assert (
                    "results" in data or "data" in data or isinstance(data, list)
                ), f"Unexpected response structure: {data}"
