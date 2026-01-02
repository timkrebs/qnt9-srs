"""
Comprehensive tests for Auth Service with PostgreSQL and JWT.

Tests all authentication endpoints with proper mocking of database operations.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.app import app
from app.auth_service import AuthError, AuthService

client = TestClient(app)


# Test data
TEST_USER_ID = str(uuid4())
TEST_EMAIL = "test@example.com"
TEST_PASSWORD = "TestPassword123!"
TEST_FULL_NAME = "Test User"
TEST_ACCESS_TOKEN = "mock-access-token"
TEST_REFRESH_TOKEN = "mock-refresh-token"


@pytest.fixture
def mock_db_manager():
    """Mock database manager for testing."""
    with patch("app.auth_service.db_manager") as mock_db:
        mock_db.fetchrow = AsyncMock()
        mock_db.fetchval = AsyncMock()
        mock_db.execute = AsyncMock()
        yield mock_db


@pytest.fixture
def mock_db_for_app():
    """Mock database for app-level dependencies."""
    with patch("app.app.db_manager") as mock_db:
        mock_db.fetchval = AsyncMock(return_value=1)
        mock_db.connect = AsyncMock()
        mock_db.disconnect = AsyncMock()
        yield mock_db


@pytest.fixture
def mock_security():
    """Mock security functions for testing."""
    with patch("app.auth_service.hash_password") as mock_hash, patch(
        "app.auth_service.verify_password"
    ) as mock_verify, patch("app.auth_service.create_access_token") as mock_access, patch(
        "app.auth_service.create_refresh_token"
    ) as mock_refresh:
        mock_hash.return_value = "hashed_password"
        mock_verify.return_value = True
        mock_access.return_value = TEST_ACCESS_TOKEN
        mock_refresh.return_value = (
            TEST_REFRESH_TOKEN,
            "hashed_refresh",
            datetime.now(timezone.utc) + timedelta(days=7),
        )
        yield {
            "hash_password": mock_hash,
            "verify_password": mock_verify,
            "create_access_token": mock_access,
            "create_refresh_token": mock_refresh,
        }


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Reset rate limiter before each test."""
    from app.rate_limiter import auth_rate_limiter, password_reset_rate_limiter

    auth_rate_limiter._clients.clear()
    password_reset_rate_limiter._clients.clear()
    yield
    auth_rate_limiter._clients.clear()
    password_reset_rate_limiter._clients.clear()


@pytest.fixture
def auth_service():
    """Create AuthService instance for testing."""
    return AuthService()


@pytest.fixture
def mock_supabase():
    """Mock auth_service sign_up for testing."""
    with patch("app.auth_service.auth_service.sign_up") as mock_sign_up:
        # Mock successful sign_up
        async def return_user(email, password, full_name=None):
            return {
                "user": {
                    "id": TEST_USER_ID,
                    "email": email,
                    "email_confirmed_at": None,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "user_metadata": {},
                    "app_metadata": {},
                    "tier": "free",
                    "full_name": full_name,
                },
                "session": {
                    "access_token": TEST_ACCESS_TOKEN,
                    "refresh_token": TEST_REFRESH_TOKEN,
                    "expires_in": 3600,
                    "expires_at": int(
                        (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()
                    ),
                    "token_type": "bearer",
                },
            }

        mock_sign_up.side_effect = return_user
        yield mock_sign_up


class TestHealthEndpoints:
    """Test health and root endpoints."""

    def test_root_endpoint(self):
        """Test root endpoint returns service information."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "QNT9 Auth Service"
        assert data["version"] == "3.0.0"
        assert data["status"] == "active"
        assert data["auth_provider"] == "PostgreSQL + JWT"

    def test_health_check(self, mock_db_for_app):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["service"] == "auth-service"


class TestSignUp:
    """Test user signup functionality."""

    @pytest.mark.asyncio
    async def test_signup_success(self, mock_supabase):
        """Test successful user registration."""
        response = client.post(
            "/auth/signup",
            json={
                "email": TEST_EMAIL,
                "password": TEST_PASSWORD,
                "full_name": TEST_FULL_NAME,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert "user" in data
        assert "session" in data
        assert data["user"]["email"] == TEST_EMAIL
        assert "access_token" in data["session"]

    def test_signup_duplicate_email(self, mock_db_manager):
        """Test signup with already registered email."""
        # Mock existing user found
        mock_db_manager.fetchrow.return_value = {"id": UUID(TEST_USER_ID)}

        response = client.post(
            "/auth/signup",
            json={
                "email": "existing@example.com",
                "password": TEST_PASSWORD,
                "full_name": TEST_FULL_NAME,
            },
        )

        assert response.status_code == 409
        assert "already registered" in response.json()["detail"].lower()

    def test_signup_missing_email(self):
        """Test signup with missing email."""
        response = client.post(
            "/auth/signup",
            json={
                "password": TEST_PASSWORD,
                "full_name": TEST_FULL_NAME,
            },
        )

        assert response.status_code == 422

    def test_signup_missing_password(self):
        """Test signup with missing password."""
        response = client.post(
            "/auth/signup",
            json={
                "email": TEST_EMAIL,
                "full_name": TEST_FULL_NAME,
            },
        )

        assert response.status_code == 422

    def test_signup_invalid_email(self):
        """Test signup with invalid email format."""
        response = client.post(
            "/auth/signup",
            json={
                "email": "not-an-email",
                "password": TEST_PASSWORD,
                "full_name": TEST_FULL_NAME,
            },
        )

        assert response.status_code == 422


class TestSignIn:
    """Test user signin functionality."""

    @pytest.mark.asyncio
    async def test_signin_success(self, mock_db_manager, mock_security):
        """Test successful user authentication."""
        mock_db_manager.fetchrow.return_value = {
            "id": UUID(TEST_USER_ID),
            "email": TEST_EMAIL,
            "password_hash": "hashed_password",
            "full_name": TEST_FULL_NAME,
            "tier": "free",
            "email_verified": True,
            "created_at": datetime.now(timezone.utc),
            "subscription_end": None,
            "is_active": True,
        }

        response = client.post(
            "/auth/signin",
            json={
                "email": TEST_EMAIL,
                "password": TEST_PASSWORD,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "user" in data
        assert "session" in data
        assert data["user"]["email"] == TEST_EMAIL

    def test_signin_user_not_found(self, mock_db_manager):
        """Test signin with non-existent user."""
        mock_db_manager.fetchrow.return_value = None

        response = client.post(
            "/auth/signin",
            json={
                "email": "nonexistent@example.com",
                "password": TEST_PASSWORD,
            },
        )

        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()

    def test_signin_wrong_password(self, mock_db_manager, mock_security):
        """Test signin with incorrect password."""
        mock_db_manager.fetchrow.return_value = {
            "id": UUID(TEST_USER_ID),
            "email": TEST_EMAIL,
            "password_hash": "hashed_password",
            "full_name": TEST_FULL_NAME,
            "tier": "free",
            "email_verified": True,
            "created_at": datetime.now(timezone.utc),
            "subscription_end": None,
            "is_active": True,
        }
        mock_security["verify_password"].return_value = False

        response = client.post(
            "/auth/signin",
            json={
                "email": TEST_EMAIL,
                "password": "WrongPassword123!",
            },
        )

        assert response.status_code == 401

    def test_signin_disabled_account(self, mock_db_manager):
        """Test signin with disabled account."""
        mock_db_manager.fetchrow.return_value = {
            "id": UUID(TEST_USER_ID),
            "email": TEST_EMAIL,
            "password_hash": "hashed_password",
            "full_name": TEST_FULL_NAME,
            "tier": "free",
            "email_verified": True,
            "created_at": datetime.now(timezone.utc),
            "subscription_end": None,
            "is_active": False,
        }

        response = client.post(
            "/auth/signin",
            json={
                "email": TEST_EMAIL,
                "password": TEST_PASSWORD,
            },
        )

        assert response.status_code == 403
        assert "disabled" in response.json()["detail"].lower()

    def test_signin_missing_email(self):
        """Test signin with missing email."""
        response = client.post(
            "/auth/signin",
            json={
                "password": TEST_PASSWORD,
            },
        )

        assert response.status_code == 422

    def test_signin_missing_password(self):
        """Test signin with missing password."""
        response = client.post(
            "/auth/signin",
            json={
                "email": TEST_EMAIL,
            },
        )

        assert response.status_code == 422


class TestSignOut:
    """Test user signout functionality."""

    def test_signout_success(self, mock_db_manager):
        """Test successful user sign out."""
        mock_db_manager.execute.return_value = None

        response = client.post(
            "/auth/signout",
            json={"refresh_token": TEST_REFRESH_TOKEN},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "signed out" in data["message"].lower()


class TestRefreshSession:
    """Test session refresh functionality."""

    @pytest.mark.asyncio
    async def test_refresh_success(self, mock_db_manager, mock_security):
        """Test successful session refresh."""
        mock_db_manager.fetchrow.return_value = {
            "id": 1,
            "user_id": UUID(TEST_USER_ID),
            "expires_at": datetime.now(timezone.utc) + timedelta(days=1),
            "revoked": False,
            "email": TEST_EMAIL,
            "tier": "free",
            "full_name": TEST_FULL_NAME,
            "is_active": True,
        }

        response = client.post(
            "/auth/refresh",
            json={"refresh_token": TEST_REFRESH_TOKEN},
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    def test_refresh_invalid_token(self, mock_db_manager):
        """Test refresh with invalid token."""
        mock_db_manager.fetchrow.return_value = None

        response = client.post(
            "/auth/refresh",
            json={"refresh_token": "invalid-token"},
        )

        assert response.status_code == 401

    def test_refresh_revoked_token(self, mock_db_manager):
        """Test refresh with revoked token."""
        mock_db_manager.fetchrow.return_value = {
            "id": 1,
            "user_id": UUID(TEST_USER_ID),
            "expires_at": datetime.now(timezone.utc) + timedelta(days=1),
            "revoked": True,
            "email": TEST_EMAIL,
            "tier": "free",
            "full_name": TEST_FULL_NAME,
            "is_active": True,
        }

        response = client.post(
            "/auth/refresh",
            json={"refresh_token": TEST_REFRESH_TOKEN},
        )

        assert response.status_code == 401

    def test_refresh_expired_token(self, mock_db_manager):
        """Test refresh with expired token."""
        mock_db_manager.fetchrow.return_value = {
            "id": 1,
            "user_id": UUID(TEST_USER_ID),
            "expires_at": datetime.now(timezone.utc) - timedelta(days=1),  # Expired
            "revoked": False,
            "email": TEST_EMAIL,
            "tier": "free",
            "full_name": TEST_FULL_NAME,
            "is_active": True,
        }

        response = client.post(
            "/auth/refresh",
            json={"refresh_token": TEST_REFRESH_TOKEN},
        )

        assert response.status_code == 401


class TestPasswordReset:
    """Test password reset functionality."""

    def test_password_reset_request(self, mock_db_manager):
        """Test password reset request."""
        mock_db_manager.fetchrow.return_value = {"id": UUID(TEST_USER_ID)}

        response = client.post(
            "/auth/reset-password",
            json={"email": TEST_EMAIL},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        # For security, always returns success even if email doesn't exist

    def test_password_reset_nonexistent_email(self, mock_db_manager):
        """Test password reset with non-existent email."""
        mock_db_manager.fetchrow.return_value = None

        response = client.post(
            "/auth/reset-password",
            json={"email": "nonexistent@example.com"},
        )

        # Should still return success for security
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestGetCurrentUser:
    """Test getting current user information."""

    def test_get_user_without_token(self):
        """Test getting user without authorization header."""
        response = client.get("/auth/me")
        assert response.status_code == 401

    def test_get_user_with_invalid_token(self):
        """Test getting user with invalid token."""
        response = client.get(
            "/auth/me",
            headers={"Authorization": "Bearer invalid-token"},
        )
        assert response.status_code == 401


class TestUpdateUser:
    """Test user update functionality."""

    def test_update_user_without_token(self):
        """Test updating user without authorization header."""
        response = client.patch(
            "/auth/me",
            json={"full_name": "Updated Name"},
        )
        assert response.status_code == 401


class TestUserTier:
    """Test user tier functionality."""

    def test_get_tier_without_token(self):
        """Test getting tier without authorization header."""
        response = client.get("/auth/me/tier")
        assert response.status_code == 401

    def test_update_tier_without_token(self):
        """Test updating tier without authorization header."""
        response = client.patch(
            "/auth/me/tier",
            json={"tier": "paid"},
        )
        assert response.status_code == 401


class TestAuthError:
    """Test AuthError exception class."""

    def test_auth_error_default_code(self):
        """Test AuthError with default code."""
        error = AuthError("Test message")
        assert error.message == "Test message"
        assert error.code == "auth_error"
        assert str(error) == "Test message"

    def test_auth_error_custom_code(self):
        """Test AuthError with custom code."""
        error = AuthError("User not found", "user_not_found")
        assert error.message == "User not found"
        assert error.code == "user_not_found"

    def test_auth_error_inheritance(self):
        """Test that AuthError inherits from Exception."""
        error = AuthError("Test")
        assert isinstance(error, Exception)


class TestAuthServiceUnit:
    """Unit tests for AuthService class methods."""

    @pytest.mark.asyncio
    async def test_sign_up_exception_handling(self, auth_service, mock_db_manager):
        """Test sign up handles unexpected exceptions."""
        mock_db_manager.fetchrow.side_effect = Exception("Database error")

        with pytest.raises(AuthError) as exc_info:
            await auth_service.sign_up(
                email="test@example.com",
                password="TestPass123!",
            )

        assert "Registration failed" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_sign_in_exception_handling(self, auth_service, mock_db_manager):
        """Test sign in handles unexpected exceptions."""
        mock_db_manager.fetchrow.side_effect = Exception("Database error")

        with pytest.raises(AuthError) as exc_info:
            await auth_service.sign_in(
                email="test@example.com",
                password="TestPass123!",
            )

        assert "Sign in failed" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_get_user_returns_none_on_exception(self, auth_service, mock_db_manager):
        """Test get_user returns None on exception."""
        mock_db_manager.fetchrow.side_effect = Exception("Database error")

        result = await auth_service.get_user(TEST_USER_ID)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_user_returns_none_for_nonexistent(self, auth_service, mock_db_manager):
        """Test get_user returns None for non-existent user."""
        mock_db_manager.fetchrow.return_value = None

        result = await auth_service.get_user(TEST_USER_ID)
        assert result is None

    @pytest.mark.asyncio
    async def test_update_user_no_fields(self, auth_service, mock_db_manager):
        """Test update_user with no fields to update."""
        with pytest.raises(AuthError) as exc_info:
            await auth_service.update_user(user_id=TEST_USER_ID)

        assert exc_info.value.code == "no_updates"

    @pytest.mark.asyncio
    async def test_update_user_duplicate_email(self, auth_service, mock_db_manager):
        """Test update_user with duplicate email."""
        mock_db_manager.fetchrow.return_value = {"id": UUID(TEST_USER_ID)}

        with pytest.raises(AuthError) as exc_info:
            await auth_service.update_user(
                user_id=TEST_USER_ID,
                email="existing@example.com",
            )

        assert exc_info.value.code == "email_exists"

    @pytest.mark.asyncio
    async def test_update_user_not_found(self, auth_service, mock_db_manager):
        """Test update_user when user not found."""
        mock_db_manager.fetchrow.side_effect = [None, None]  # No existing email, no user

        with pytest.raises(AuthError) as exc_info:
            await auth_service.update_user(
                user_id=TEST_USER_ID,
                full_name="New Name",
            )

        assert exc_info.value.code == "user_not_found"

    @pytest.mark.asyncio
    async def test_refresh_session_disabled_account(self, auth_service, mock_db_manager):
        """Test refresh_session with disabled account."""
        mock_db_manager.fetchrow.return_value = {
            "id": 1,
            "user_id": UUID(TEST_USER_ID),
            "expires_at": datetime.now(timezone.utc) + timedelta(days=1),
            "revoked": False,
            "email": TEST_EMAIL,
            "tier": "free",
            "full_name": TEST_FULL_NAME,
            "is_active": False,
        }

        with pytest.raises(AuthError) as exc_info:
            await auth_service.refresh_session(TEST_REFRESH_TOKEN)

        assert exc_info.value.code == "account_disabled"

    @pytest.mark.asyncio
    async def test_get_user_tier_exception(self, auth_service, mock_db_manager):
        """Test get_user_tier handles exception."""
        mock_db_manager.fetchrow.side_effect = Exception("Database error")

        with pytest.raises(AuthError) as exc_info:
            await auth_service.get_user_tier(TEST_USER_ID)

        assert exc_info.value.code == "tier_fetch_error"

    @pytest.mark.asyncio
    async def test_get_user_tier_not_found(self, auth_service, mock_db_manager):
        """Test get_user_tier returns defaults when user not found."""
        mock_db_manager.fetchrow.return_value = None

        result = await auth_service.get_user_tier(TEST_USER_ID)

        assert result["tier"] == "free"
        assert result["subscription_start"] is None

    @pytest.mark.asyncio
    async def test_update_user_tier_not_found(self, auth_service, mock_db_manager):
        """Test update_user_tier when user not found."""
        mock_db_manager.fetchrow.return_value = None

        with pytest.raises(AuthError) as exc_info:
            await auth_service.update_user_tier(TEST_USER_ID, "paid")

        assert exc_info.value.code == "user_not_found"

    @pytest.mark.asyncio
    async def test_update_user_tier_exception(self, auth_service, mock_db_manager):
        """Test update_user_tier handles exception."""
        mock_db_manager.fetchrow.side_effect = Exception("Database error")

        with pytest.raises(AuthError) as exc_info:
            await auth_service.update_user_tier(TEST_USER_ID, "paid")

        assert exc_info.value.code == "tier_update_error"

    @pytest.mark.asyncio
    async def test_sign_out_exception(self, auth_service, mock_db_manager):
        """Test sign_out handles exception."""
        mock_db_manager.execute.side_effect = Exception("Database error")

        with pytest.raises(AuthError) as exc_info:
            await auth_service.sign_out(TEST_REFRESH_TOKEN)

        assert exc_info.value.code == "signout_error"
