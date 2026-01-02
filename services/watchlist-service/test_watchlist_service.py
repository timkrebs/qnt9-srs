"""
Comprehensive Test Suite for Watchlist Service

Tests:
1. Supabase Database Connection
2. Health Check Endpoint
3. CRUD Operations (GET, POST, PATCH, DELETE)
4. Tier Limits (Free: 3, Paid: unlimited)
5. JWT Authentication
6. Duplicate Prevention
7. Error Handling
"""

import os
import sys

# Add app directory to path - must be before other imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "app"))

import asyncio  # noqa: E402
from datetime import datetime, timedelta  # noqa: E402

import asyncpg  # noqa: E402
import httpx  # noqa: E402
import jwt  # noqa: E402
import structlog  # noqa: E402

from app.config import settings  # noqa: E402

logger = structlog.get_logger(__name__)

# Test configuration
BASE_URL = f"http://{settings.SERVICE_HOST}:{settings.SERVICE_PORT}"
TEST_USER_ID = "123e4567-e89b-12d3-a456-426614174000"  # UUID format
TEST_USER_EMAIL = "test@example.com"


def create_test_jwt(user_id: str, email: str, tier: str = "free") -> str:
    """Create a test JWT token."""
    payload = {
        "sub": user_id,
        "user_id": user_id,  # Support both formats
        "email": email,
        "tier": tier,
        "exp": datetime.utcnow() + timedelta(hours=1),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


class Colors:
    """ANSI color codes."""

    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


def print_test(name: str):
    """Print test name."""
    print(f"\n{Colors.BLUE}{Colors.BOLD}[TEST] {name}{Colors.RESET}")


def print_success(msg: str):
    """Print success message."""
    print(f"  {Colors.GREEN}[PASS] {msg}{Colors.RESET}")


def print_error(msg: str):
    """Print error message."""
    print(f"  {Colors.RED}[FAIL] {msg}{Colors.RESET}")


def print_info(msg: str):
    """Print info message."""
    print(f"  {Colors.YELLOW}[INFO] {msg}{Colors.RESET}")


async def test_database_connection():
    """Test 1: Verify Supabase database connection."""
    print_test("Test 1: Supabase Database Connection")

    try:
        print_info(f"Connecting to: {settings.DATABASE_URL.split('@')[1].split('/')[0]}")

        conn = await asyncpg.connect(
            settings.DATABASE_URL,
            statement_cache_size=0,  # Required for Supabase pooler
        )

        # Test basic query
        version = await conn.fetchval("SELECT version()")
        print_success(f"Connected to PostgreSQL: {version.split(',')[0]}")

        # Check if watchlists table exists
        table_exists = await conn.fetchval(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'watchlists')"
        )

        if table_exists:
            print_success("Table 'watchlists' exists")
        else:
            print_error("Table 'watchlists' not found")

        # Check table structure
        columns = await conn.fetch(
            """
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'watchlists'
            ORDER BY ordinal_position
            """
        )

        print_info(f"Table structure ({len(columns)} columns):")
        for col in columns:
            print(
                f"    - {col['column_name']}: {col['data_type']} (nullable: {col['is_nullable']})"
            )

        await conn.close()
        return True

    except Exception as e:
        print_error(f"Database connection failed: {e}")
        return False


async def test_health_endpoint():
    """Test 2: Health check endpoint."""
    print_test("Test 2: Health Check Endpoint")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/health")

            if response.status_code == 200:
                data = response.json()
                print_success(f"Status: {response.status_code}")
                print_info(f"Response: {data}")

                # Verify response structure
                assert "status" in data, "Missing 'status' field"
                assert data["status"] == "healthy", "Service not healthy"
                assert "service" in data, "Missing 'service' field"
                assert "version" in data, "Missing 'version' field"

                print_success("Health check passed")
                return True
            else:
                print_error(f"Unexpected status code: {response.status_code}")
                return False

    except Exception as e:
        print_error(f"Health check failed: {e}")
        return False


async def test_authentication():
    """Test 3: JWT Authentication."""
    print_test("Test 3: JWT Authentication")

    try:
        async with httpx.AsyncClient() as client:
            # Test 3.1: Request without token
            response = await client.get(f"{BASE_URL}/api/watchlist")
            if response.status_code == 403:  # FastAPI HTTPBearer returns 403
                print_success("Request without token correctly rejected (403)")
            else:
                print_error(f"Expected 403, got {response.status_code}")

            # Test 3.2: Request with invalid token
            headers = {"Authorization": "Bearer invalid-token"}
            response = await client.get(f"{BASE_URL}/api/watchlist", headers=headers)
            if response.status_code == 401:
                print_success("Request with invalid token correctly rejected (401)")
            else:
                print_error(f"Expected 401, got {response.status_code}")

            # Test 3.3: Request with valid token
            token = create_test_jwt(TEST_USER_ID, TEST_USER_EMAIL, "free")
            headers = {"Authorization": f"Bearer {token}"}
            response = await client.get(f"{BASE_URL}/api/watchlist", headers=headers)
            if response.status_code == 200:
                print_success("Request with valid token accepted (200)")
                return True
            else:
                print_error(f"Expected 200, got {response.status_code}: {response.text}")
                return False

    except Exception as e:
        print_error(f"Authentication test failed: {e}")
        return False


async def ensure_test_user_exists():
    """Ensure test user exists in auth.users table."""
    try:
        conn = await asyncpg.connect(settings.DATABASE_URL, statement_cache_size=0)

        # Check if user exists
        user_exists = await conn.fetchval(
            "SELECT EXISTS(SELECT 1 FROM auth.users WHERE id = $1)", TEST_USER_ID
        )

        if not user_exists:
            # Create test user in auth.users
            await conn.execute(
                """
                INSERT INTO auth.users (id, email, encrypted_password, email_confirmed_at, created_at, updated_at)
                VALUES ($1, $2, '', NOW(), NOW(), NOW())
                ON CONFLICT (id) DO NOTHING
                """,
                TEST_USER_ID,
                TEST_USER_EMAIL,
            )
            print_info("Created test user in auth.users")

            # Check if user_profile exists, if not create it
            profile_exists = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM user_profiles WHERE id = $1)", TEST_USER_ID
            )

            if not profile_exists:
                await conn.execute(
                    """
                    INSERT INTO user_profiles (id, tier)
                    VALUES ($1, 'free')
                    ON CONFLICT (id) DO NOTHING
                    """,
                    TEST_USER_ID,
                )
                print_info("Created test user profile")

        await conn.close()
        return True
    except Exception as e:
        print_error(f"Failed to ensure test user: {e}")
        return False


async def cleanup_test_data():
    """Clean up test data from previous runs."""
    try:
        conn = await asyncpg.connect(settings.DATABASE_URL, statement_cache_size=0)
        await conn.execute("DELETE FROM watchlists WHERE user_id = $1", TEST_USER_ID)
        await conn.close()
        print_info("Cleaned up previous test data")
    except Exception as e:
        print_error(f"Cleanup failed: {e}")


async def test_crud_operations():
    """Test 4: CRUD Operations (GET, POST, PATCH, DELETE)."""
    print_test("Test 4: CRUD Operations")

    # Ensure test user exists
    if not await ensure_test_user_exists():
        print_error("Cannot run CRUD tests without test user")
        return False

    # Clean up first
    await cleanup_test_data()

    token = create_test_jwt(TEST_USER_ID, TEST_USER_EMAIL, "free")
    headers = {"Authorization": f"Bearer {token}"}

    try:
        async with httpx.AsyncClient() as client:
            # Test 4.1: GET empty watchlist
            response = await client.get(f"{BASE_URL}/api/watchlist", headers=headers)
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 0
            assert data["tier"] == "free"
            assert data["limit"] == 3
            print_success("GET empty watchlist: OK")

            # Test 4.2: POST - Add stock
            payload = {"symbol": "AAPL", "notes": "Test stock", "alert_enabled": False}
            response = await client.post(f"{BASE_URL}/api/watchlist", json=payload, headers=headers)
            assert response.status_code == 201
            data = response.json()
            assert data["symbol"] == "AAPL"
            assert data["notes"] == "Test stock"
            print_success("POST add stock: OK")

            # Test 4.3: GET watchlist with 1 item
            response = await client.get(f"{BASE_URL}/api/watchlist", headers=headers)
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 1
            assert len(data["watchlist"]) == 1
            print_success("GET watchlist with 1 item: OK")

            # Test 4.4: POST - Try to add duplicate
            response = await client.post(f"{BASE_URL}/api/watchlist", json=payload, headers=headers)
            assert response.status_code == 409  # Conflict
            print_success("POST duplicate prevention: OK")

            # Test 4.5: PATCH - Update stock
            update_payload = {
                "notes": "Updated notes",
                "alert_enabled": True,
                "alert_price_above": 200.0,
            }
            response = await client.patch(
                f"{BASE_URL}/api/watchlist/AAPL", json=update_payload, headers=headers
            )
            assert response.status_code == 200
            data = response.json()
            assert data["notes"] == "Updated notes"
            assert data["alert_enabled"] is True
            assert data["alert_price_above"] == 200.0
            print_success("PATCH update stock: OK")

            # Test 4.6: DELETE - Remove stock
            response = await client.delete(f"{BASE_URL}/api/watchlist/AAPL", headers=headers)
            assert response.status_code == 200
            print_success("DELETE remove stock: OK")

            # Test 4.7: GET empty watchlist again
            response = await client.get(f"{BASE_URL}/api/watchlist", headers=headers)
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 0
            print_success("GET empty watchlist after delete: OK")

            return True

    except AssertionError as e:
        print_error(f"CRUD test assertion failed: {e}")
        return False
    except Exception as e:
        print_error(f"CRUD test failed: {e}")
        return False


async def test_tier_limits():
    """Test 5: Tier-based limits (Free: 3, Paid: unlimited)."""
    print_test("Test 5: Tier-based Limits")

    # Ensure test user exists
    if not await ensure_test_user_exists():
        print_error("Cannot run tier limit tests without test user")
        return False

    # Clean up first
    await cleanup_test_data()

    try:
        async with httpx.AsyncClient() as client:
            # Test 5.1: Free tier - can add 3 stocks
            token = create_test_jwt(TEST_USER_ID, TEST_USER_EMAIL, "free")
            headers = {"Authorization": f"Bearer {token}"}

            symbols = ["AAPL", "GOOGL", "MSFT", "TSLA"]

            for i, symbol in enumerate(symbols[:3]):
                payload = {"symbol": symbol, "notes": f"Test {symbol}"}
                response = await client.post(
                    f"{BASE_URL}/api/watchlist", json=payload, headers=headers
                )
                assert response.status_code == 201
                print_success(f"Added {symbol} ({i+1}/3)")

            # Test 5.2: Free tier - 4th stock should be rejected
            payload = {"symbol": symbols[3], "notes": "Test TSLA"}
            response = await client.post(f"{BASE_URL}/api/watchlist", json=payload, headers=headers)
            assert response.status_code == 403  # Forbidden
            data = response.json()
            assert "limit reached" in data["detail"].lower()
            print_success("Free tier limit (3) enforced: OK")

            # Test 5.3: Paid tier - can add more than 3 stocks
            # First clean up
            for symbol in symbols[:3]:
                await client.delete(f"{BASE_URL}/api/watchlist/{symbol}", headers=headers)

            # Create paid user token
            paid_token = create_test_jwt(TEST_USER_ID, TEST_USER_EMAIL, "paid")
            paid_headers = {"Authorization": f"Bearer {paid_token}"}

            # Add 4 stocks with paid tier
            for symbol in symbols:
                payload = {"symbol": symbol, "notes": f"Test {symbol}"}
                response = await client.post(
                    f"{BASE_URL}/api/watchlist", json=payload, headers=paid_headers
                )
                assert response.status_code == 201

            # Verify we have 4 stocks
            response = await client.get(f"{BASE_URL}/api/watchlist", headers=paid_headers)
            data = response.json()
            assert data["total"] == 4
            assert data["tier"] == "paid"
            assert data["limit"] == 999
            print_success("Paid tier can exceed 3 stocks: OK")

            return True

    except AssertionError as e:
        print_error(f"Tier limit test assertion failed: {e}")
        return False
    except Exception as e:
        print_error(f"Tier limit test failed: {e}")
        return False
    finally:
        # Cleanup
        await cleanup_test_data()


async def run_all_tests():
    """Run all tests."""
    print(f"\n{Colors.BOLD}{'='*60}")
    print("  Watchlist Service Test Suite")
    print(f"{'='*60}{Colors.RESET}\n")

    print_info(f"Service URL: {BASE_URL}")
    print_info("Database: Supabase PostgreSQL")
    print_info(f"Test User ID: {TEST_USER_ID}\n")

    results = {}

    # Run tests
    results["Database Connection"] = await test_database_connection()

    # Only continue if database is accessible
    if not results["Database Connection"]:
        print_error("\n[ERROR] Database connection failed. Cannot continue with other tests.")
        return

    results["Health Endpoint"] = await test_health_endpoint()
    results["Authentication"] = await test_authentication()
    results["CRUD Operations"] = await test_crud_operations()
    results["Tier Limits"] = await test_tier_limits()

    # Print summary
    print(f"\n{Colors.BOLD}{'='*60}")
    print("  Test Summary")
    print(f"{'='*60}{Colors.RESET}\n")

    total = len(results)
    passed = sum(1 for v in results.values() if v)
    failed = total - passed

    for test_name, result in results.items():
        status = (
            f"{Colors.GREEN}[PASS]{Colors.RESET}" if result else f"{Colors.RED}[FAIL]{Colors.RESET}"
        )
        print(f"  {test_name:.<50} {status}")

    print(f"\n{Colors.BOLD}{'='*60}")
    print(
        f"  Total: {total} | Passed: {Colors.GREEN}{passed}{Colors.RESET} | Failed: {Colors.RED}{failed}{Colors.RESET}"
    )
    print(f"{'='*60}{Colors.RESET}\n")

    if failed == 0:
        print(f"{Colors.GREEN}{Colors.BOLD}SUCCESS: All tests passed!{Colors.RESET}\n")
    else:
        print(
            f"{Colors.RED}{Colors.BOLD}FAILURE: Some tests failed. Check the logs above.{Colors.RESET}\n"
        )


if __name__ == "__main__":
    asyncio.run(run_all_tests())
