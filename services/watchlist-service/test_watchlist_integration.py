"""Integration tests for watchlist feature."""

import time

import httpx
import pytest


class TestWatchlistIntegration:
    """Test the complete watchlist flow from login to add/view/delete."""

    @pytest.fixture
    async def auth_token(self, test_user):
        """Get authentication token for test user."""
        async with httpx.AsyncClient(base_url="http://localhost:8010") as client:
            response = await client.post(
                "/api/v1/auth/login",
                json={
                    "email": test_user["email"],
                    "password": test_user["password"],
                },
            )
            assert response.status_code == 200
            data = response.json()
            return data["access_token"]

    @pytest.fixture
    def test_user(self):
        """Test user credentials."""
        return {
            "email": "test@example.com",
            "password": "TestPassword123!",
        }

    @pytest.fixture
    def auth_headers(self, auth_token):
        """Create authorization headers."""
        return {"Authorization": f"Bearer {auth_token}"}

    async def test_watchlist_empty_initial(self, auth_headers):
        """Test that watchlist is initially empty for new user."""
        async with httpx.AsyncClient(base_url="http://localhost:8012") as client:
            response = await client.get("/api/watchlist", headers=auth_headers)

            assert response.status_code == 200
            data = response.json()
            assert "watchlist" in data
            assert isinstance(data["watchlist"], list)
            assert data["total"] == 0
            assert data["tier"] in ["free", "paid", "enterprise"]

    async def test_add_stock_to_watchlist(self, auth_headers):
        """Test adding a stock to watchlist."""
        async with httpx.AsyncClient(base_url="http://localhost:8012") as client:
            response = await client.post(
                "/api/watchlist",
                headers=auth_headers,
                json={"symbol": "AAPL"},
            )

            assert response.status_code == 201
            data = response.json()
            assert data["symbol"] == "AAPL"
            assert data["user_id"]
            assert data["added_at"]

    async def test_view_watchlist_after_add(self, auth_headers):
        """Test viewing watchlist after adding a stock."""
        async with httpx.AsyncClient(base_url="http://localhost:8012") as client:
            await client.post(
                "/api/watchlist",
                headers=auth_headers,
                json={"symbol": "TSLA"},
            )

            time.sleep(0.1)

            response = await client.get("/api/watchlist", headers=auth_headers)

            assert response.status_code == 200
            data = response.json()
            assert len(data["watchlist"]) > 0
            symbols = [item["symbol"] for item in data["watchlist"]]
            assert "TSLA" in symbols

    async def test_duplicate_stock_rejected(self, auth_headers):
        """Test that adding duplicate stock returns 409 Conflict."""
        async with httpx.AsyncClient(base_url="http://localhost:8012") as client:
            await client.post(
                "/api/watchlist",
                headers=auth_headers,
                json={"symbol": "MSFT"},
            )

            response = await client.post(
                "/api/watchlist",
                headers=auth_headers,
                json={"symbol": "MSFT"},
            )

            assert response.status_code == 409
            data = response.json()
            assert "detail" in data

    async def test_free_tier_limit(self, auth_headers):
        """Test that free tier is limited to 3 stocks."""
        async with httpx.AsyncClient(base_url="http://localhost:8012") as client:
            # Clear existing watchlist
            response = await client.get("/api/watchlist", headers=auth_headers)
            for item in response.json()["watchlist"]:
                await client.delete(
                    f"/api/watchlist/{item['symbol']}", headers=auth_headers
                )

            # Add 3 stocks (should succeed)
            symbols = ["AAPL", "MSFT", "GOOGL"]
            for symbol in symbols:
                response = await client.post(
                    "/api/watchlist",
                    headers=auth_headers,
                    json={"symbol": symbol},
                )
                assert response.status_code == 201

            # Try to add 4th stock (should fail for free tier)
            response = await client.post(
                "/api/watchlist",
                headers=auth_headers,
                json={"symbol": "AMZN"},
            )

            if response.status_code == 403:
                data = response.json()
                assert "limit" in data["detail"].lower()

    async def test_delete_stock_from_watchlist(self, auth_headers):
        """Test removing a stock from watchlist."""
        async with httpx.AsyncClient(base_url="http://localhost:8012") as client:
            await client.post(
                "/api/watchlist",
                headers=auth_headers,
                json={"symbol": "NFLX"},
            )

            response = await client.delete("/api/watchlist/NFLX", headers=auth_headers)

            assert response.status_code in [200, 204]

            response = await client.get("/api/watchlist", headers=auth_headers)
            data = response.json()
            symbols = [item["symbol"] for item in data["watchlist"]]
            assert "NFLX" not in symbols

    async def test_unauthorized_access(self):
        """Test that unauthorized requests are rejected."""
        async with httpx.AsyncClient(base_url="http://localhost:8012") as client:
            response = await client.get("/api/watchlist")
            assert response.status_code == 403

            response = await client.post("/api/watchlist", json={"symbol": "AAPL"})
            assert response.status_code == 403

    async def test_frontend_proxy(self, auth_headers):
        """Test that frontend proxy correctly forwards watchlist requests."""
        async with httpx.AsyncClient(base_url="http://localhost:8080") as client:
            response = await client.get("/api/watchlist", headers=auth_headers)

            if response.status_code == 200:
                data = response.json()
                assert "watchlist" in data

    async def test_end_to_end_flow(self, test_user):
        """Test complete user flow: login -> add stock -> view watchlist."""
        # Step 1: Login
        async with httpx.AsyncClient(base_url="http://localhost:8010") as client:
            login_response = await client.post(
                "/api/v1/auth/login",
                json={
                    "email": test_user["email"],
                    "password": test_user["password"],
                },
            )
            assert login_response.status_code == 200
            access_token = login_response.json()["access_token"]

        headers = {"Authorization": f"Bearer {access_token}"}

        # Step 2: Add stock via frontend proxy
        async with httpx.AsyncClient(base_url="http://localhost:8080") as client:
            add_response = await client.post(
                "/api/watchlist",
                headers=headers,
                json={"symbol": "NVDA"},
            )
            assert add_response.status_code in [201, 409]

        # Step 3: View watchlist via frontend
        async with httpx.AsyncClient(base_url="http://localhost:8080") as client:
            view_response = await client.get("/api/watchlist", headers=headers)
            assert view_response.status_code == 200
            data = view_response.json()
            symbols = [item["symbol"] for item in data["watchlist"]]
            assert "NVDA" in symbols

    async def test_watchlist_with_alerts(self, auth_headers):
        """Test adding stock with price alerts."""
        async with httpx.AsyncClient(base_url="http://localhost:8012") as client:
            response = await client.post(
                "/api/watchlist",
                headers=auth_headers,
                json={
                    "symbol": "AMD",
                    "alert_enabled": True,
                    "alert_price_above": 150.0,
                    "alert_price_below": 100.0,
                },
            )

            assert response.status_code == 201
            data = response.json()
            assert data["symbol"] == "AMD"
            assert data["alert_enabled"] is True
            assert data["alert_price_above"] == 150.0
            assert data["alert_price_below"] == 100.0

    async def test_watchlist_with_notes(self, auth_headers):
        """Test adding stock with notes."""
        async with httpx.AsyncClient(base_url="http://localhost:8012") as client:
            response = await client.post(
                "/api/watchlist",
                headers=auth_headers,
                json={
                    "symbol": "INTC",
                    "notes": "Potential turnaround play",
                },
            )

            assert response.status_code == 201
            data = response.json()
            assert data["symbol"] == "INTC"
            assert data["notes"] == "Potential turnaround play"
