"""
Tests for Supabase authentication integration.

Tests sign up, sign in, token validation, and session refresh.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from app.supabase_auth_service import AuthError, SupabaseAuthService


@pytest.fixture
def mock_supabase_client():
    """Create a mock Supabase client."""
    with patch("app.supabase_auth_service.get_supabase_client") as mock_get_client:
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        yield mock_client


@pytest.fixture
def auth_service(mock_supabase_client):
    """Create auth service with mocked Supabase client."""
    service = SupabaseAuthService()
    service.supabase = mock_supabase_client
    return service


@pytest.fixture
def mock_db_manager():
    """Mock database manager."""
    with patch("app.supabase_auth_service.db_manager") as mock_db:
        yield mock_db


@pytest.mark.asyncio
class TestSupabaseAuth:
    """Test cases for Supabase authentication."""

    async def test_sign_up_success(
        self, auth_service, mock_supabase_client, mock_db_manager
    ):
        """Test successful user registration."""
        mock_user = Mock()
        mock_user.id = "test-user-id"
        mock_user.email = "test@example.com"
        mock_user.email_confirmed_at = None
        mock_user.created_at = datetime.now().isoformat()
        mock_user.user_metadata = {"full_name": "Test User"}
        mock_user.app_metadata = {}

        mock_session = Mock()
        mock_session.access_token = "test-access-token"
        mock_session.refresh_token = "test-refresh-token"
        mock_session.expires_in = 3600
        mock_session.expires_at = 3600
        mock_session.token_type = "bearer"

        mock_response = Mock()
        mock_response.user = mock_user
        mock_response.session = mock_session

        mock_supabase_client.auth.sign_up.return_value = mock_response
        mock_db_manager.execute = Mock()

        result = await auth_service.sign_up(
            email="test@example.com",
            password="TestPass123!",
            full_name="Test User",
        )

        assert result["user"]["id"] == "test-user-id"
        assert result["user"]["email"] == "test@example.com"
        assert result["session"]["access_token"] == "test-access-token"
        mock_supabase_client.auth.sign_up.assert_called_once()

    async def test_sign_up_duplicate_email(self, auth_service, mock_supabase_client):
        """Test registration with existing email."""
        from gotrue.errors import AuthApiError

        mock_supabase_client.auth.sign_up.side_effect = AuthApiError(
            "User already registered", 400, "email_exists"
        )

        with pytest.raises(AuthError) as exc_info:
            await auth_service.sign_up(
                email="existing@example.com",
                password="TestPass123!",
            )

        assert exc_info.value.code == "email_exists"

    async def test_sign_in_success(
        self, auth_service, mock_supabase_client, mock_db_manager
    ):
        """Test successful sign in."""
        mock_user = Mock()
        mock_user.id = "test-user-id"
        mock_user.email = "test@example.com"
        mock_user.email_confirmed_at = datetime.now().isoformat()
        mock_user.created_at = datetime.now().isoformat()
        mock_user.last_sign_in_at = datetime.now().isoformat()
        mock_user.user_metadata = {}
        mock_user.app_metadata = {}

        mock_session = Mock()
        mock_session.access_token = "test-access-token"
        mock_session.refresh_token = "test-refresh-token"
        mock_session.expires_in = 3600
        mock_session.expires_at = 3600
        mock_session.token_type = "bearer"

        mock_response = Mock()
        mock_response.user = mock_user
        mock_response.session = mock_session

        mock_supabase_client.auth.sign_in_with_password.return_value = mock_response
        mock_db_manager.execute = Mock()

        result = await auth_service.sign_in(
            email="test@example.com",
            password="TestPass123!",
        )

        assert result["user"]["id"] == "test-user-id"
        assert result["session"]["access_token"] == "test-access-token"
        mock_supabase_client.auth.sign_in_with_password.assert_called_once()

    async def test_sign_in_invalid_credentials(
        self, auth_service, mock_supabase_client
    ):
        """Test sign in with invalid credentials."""
        from gotrue.errors import AuthApiError

        mock_supabase_client.auth.sign_in_with_password.side_effect = AuthApiError(
            "Invalid credentials", 400, "invalid_credentials"
        )

        with pytest.raises(AuthError) as exc_info:
            await auth_service.sign_in(
                email="test@example.com",
                password="WrongPassword",
            )

        assert exc_info.value.code == "invalid_credentials"

    async def test_refresh_session_success(self, auth_service, mock_supabase_client):
        """Test successful session refresh."""
        mock_user = Mock()
        mock_user.id = "test-user-id"
        mock_user.email = "test@example.com"
        mock_user.user_metadata = {}

        mock_session = Mock()
        mock_session.access_token = "new-access-token"
        mock_session.refresh_token = "new-refresh-token"
        mock_session.expires_in = 3600
        mock_session.expires_at = 3600
        mock_session.token_type = "bearer"

        mock_response = Mock()
        mock_response.user = mock_user
        mock_response.session = mock_session

        mock_supabase_client.auth.refresh_session.return_value = mock_response

        result = await auth_service.refresh_session("old-refresh-token")

        assert result["session"]["access_token"] == "new-access-token"
        mock_supabase_client.auth.refresh_session.assert_called_once_with(
            "old-refresh-token"
        )

    async def test_sign_out_success(self, auth_service, mock_supabase_client):
        """Test successful sign out."""
        mock_supabase_client.auth.set_session = Mock()
        mock_supabase_client.auth.sign_out = Mock()

        result = await auth_service.sign_out("test-access-token")

        assert result["message"] == "Successfully signed out"
        mock_supabase_client.auth.sign_out.assert_called_once()

    async def test_get_user_success(
        self, auth_service, mock_supabase_client, mock_db_manager
    ):
        """Test getting user data."""
        mock_user = Mock()
        mock_user.id = "test-user-id"
        mock_user.email = "test@example.com"
        mock_user.email_confirmed_at = datetime.now().isoformat()
        mock_user.phone = None
        mock_user.created_at = datetime.now().isoformat()
        mock_user.last_sign_in_at = datetime.now().isoformat()
        mock_user.user_metadata = {}
        mock_user.app_metadata = {}

        mock_user_response = Mock()
        mock_user_response.user = mock_user

        mock_supabase_client.auth.admin.get_user_by_id.return_value = mock_user_response

        mock_profile = {
            "tier": "free",
            "full_name": "Test User",
            "subscription_start": None,
            "subscription_end": None,
            "stripe_customer_id": None,
            "stripe_subscription_id": None,
            "metadata": {},
            "last_login": datetime.now(),
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
        mock_db_manager.fetchrow = AsyncMock(return_value=mock_profile)

        result = await auth_service.get_user("test-user-id")

        assert result["id"] == "test-user-id"
        assert result["email"] == "test@example.com"
        assert result["tier"] == "free"

    async def test_update_user_tier(self, auth_service, mock_db_manager):
        """Test updating user subscription tier."""
        mock_db_manager.execute = AsyncMock()
        mock_db_manager.fetchrow = AsyncMock(
            return_value={
                "tier": "paid",
                "subscription_start": datetime.now(),
                "subscription_end": datetime.now(),
            }
        )

        result = await auth_service.update_user_tier(
            user_id="test-user-id",
            tier="paid",
            subscription_start=datetime.now(),
            subscription_end=datetime.now(),
        )

        assert result["tier"] == "paid"
        mock_db_manager.execute.assert_called_once()


def test_auth_error():
    """Test AuthError exception."""
    error = AuthError("Test error message", "test_code")
    assert error.message == "Test error message"
    assert error.code == "test_code"
    assert str(error) == "Test error message"
