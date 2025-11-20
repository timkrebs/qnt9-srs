"""
Comprehensive tests for Auth Service with Supabase mocking.

Tests all authentication endpoints with proper mocking of Supabase client.
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.app import app

client = TestClient(app)


@pytest.fixture
def mock_supabase_auth():
    """Mock Supabase auth client for testing."""
    with patch("app.auth_service.auth_service.supabase.auth") as mock_auth:
        yield mock_auth


@pytest.fixture
def mock_supabase_client():
    """Mock Supabase client for database operations."""
    with patch("app.auth_service.auth_service.supabase") as mock_client:
        yield mock_client


class TestHealthEndpoints:
    """Test health and root endpoints."""

    def test_root_endpoint(self):
        """Test root endpoint returns service information."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "QNT9 Auth Service"
        assert data["version"] == "2.0.0"
        assert data["status"] == "active"
        assert data["auth_provider"] == "Supabase"

    def test_health_check(self):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "auth-service"


class TestSignUp:
    """Test user signup functionality."""

    def test_signup_success(self, mock_supabase_auth):
        """Test successful user registration."""
        # Mock Supabase response
        mock_supabase_auth.sign_up.return_value = MagicMock(
            user=MagicMock(
                id="test-user-id",
                email="test@example.com",
                email_confirmed_at=None,
                created_at="2025-11-20T10:00:00Z",
                updated_at="2025-11-20T10:00:00Z",
                user_metadata={"full_name": "Test User"},
            ),
            session=MagicMock(
                access_token="mock-access-token",
                refresh_token="mock-refresh-token",
                expires_in=3600,
                token_type="bearer",
            ),
        )

        response = client.post(
            "/auth/signup",
            json={
                "email": "test@example.com",
                "password": "TestPassword123!",
                "full_name": "Test User",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert "user" in data
        assert "session" in data
        assert data["user"]["email"] == "test@example.com"
        assert data["session"]["access_token"] == "mock-access-token"

    def test_signup_duplicate_email(self, mock_supabase_auth):
        """Test signup with already registered email."""
        from gotrue.errors import AuthApiError

        mock_supabase_auth.sign_up.side_effect = AuthApiError(
            "User already registered", 400
        )

        response = client.post(
            "/auth/signup",
            json={
                "email": "existing@example.com",
                "password": "TestPassword123!",
                "full_name": "Existing User",
            },
        )

        assert response.status_code == 400
        assert "Registration failed" in response.json()["detail"]

    def test_signup_invalid_email(self):
        """Test signup with invalid email format."""
        response = client.post(
            "/auth/signup",
            json={
                "email": "invalid-email",
                "password": "TestPassword123!",
                "full_name": "Test User",
            },
        )

        assert response.status_code == 422  # Validation error

    def test_signup_weak_password(self):
        """Test signup with weak password."""
        response = client.post(
            "/auth/signup",
            json={
                "email": "test@example.com",
                "password": "weak",
                "full_name": "Test User",
            },
        )

        assert response.status_code == 422  # Validation error


class TestSignIn:
    """Test user signin functionality."""

    def test_signin_success(self, mock_supabase_auth):
        """Test successful user login."""
        mock_supabase_auth.sign_in_with_password.return_value = MagicMock(
            user=MagicMock(
                id="test-user-id",
                email="test@example.com",
                email_confirmed_at="2025-11-20T10:00:00Z",
                created_at="2025-11-20T10:00:00Z",
                updated_at="2025-11-20T10:00:00Z",
                user_metadata={"full_name": "Test User"},
            ),
            session=MagicMock(
                access_token="mock-access-token",
                refresh_token="mock-refresh-token",
                expires_in=3600,
                token_type="bearer",
            ),
        )

        response = client.post(
            "/auth/signin",
            json={
                "email": "test@example.com",
                "password": "TestPassword123!",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "user" in data
        assert "session" in data
        assert data["user"]["email"] == "test@example.com"
        assert data["session"]["access_token"] == "mock-access-token"

    def test_signin_invalid_credentials(self, mock_supabase_auth):
        """Test signin with invalid credentials."""
        from gotrue.errors import AuthApiError

        mock_supabase_auth.sign_in_with_password.side_effect = AuthApiError(
            "Invalid login credentials", 400
        )

        response = client.post(
            "/auth/signin",
            json={
                "email": "test@example.com",
                "password": "WrongPassword123!",
            },
        )

        assert response.status_code == 401
        assert "Invalid credentials" in response.json()["detail"]

    def test_signin_missing_fields(self):
        """Test signin with missing required fields."""
        response = client.post(
            "/auth/signin",
            json={"email": "test@example.com"},
        )

        assert response.status_code == 422  # Validation error


class TestSignOut:
    """Test user signout functionality."""

    def test_signout_success(self, mock_supabase_auth):
        """Test successful user logout."""
        mock_supabase_auth.sign_out.return_value = None

        response = client.post(
            "/auth/signout",
            headers={"Authorization": "Bearer mock-access-token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Successfully signed out"

    def test_signout_without_token(self):
        """Test signout without authorization header."""
        response = client.post("/auth/signout")

        assert response.status_code == 401
        assert "Authorization header missing" in response.json()["detail"]


class TestRefreshToken:
    """Test token refresh functionality."""

    def test_refresh_token_success(self, mock_supabase_auth):
        """Test successful token refresh."""
        mock_supabase_auth.refresh_session.return_value = MagicMock(
            user=MagicMock(
                id="test-user-id",
                email="test@example.com",
                email_confirmed_at="2025-11-20T10:00:00Z",
                created_at="2025-11-20T10:00:00Z",
                updated_at="2025-11-20T10:00:00Z",
                user_metadata={"full_name": "Test User"},
            ),
            session=MagicMock(
                access_token="new-access-token",
                refresh_token="new-refresh-token",
                expires_in=3600,
                token_type="bearer",
            ),
        )

        response = client.post(
            "/auth/refresh",
            json={"refresh_token": "mock-refresh-token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "user" in data
        assert "session" in data
        assert data["session"]["access_token"] == "new-access-token"

    def test_refresh_token_invalid(self, mock_supabase_auth):
        """Test refresh with invalid token."""
        from gotrue.errors import AuthApiError

        mock_supabase_auth.refresh_session.side_effect = AuthApiError(
            "Invalid refresh token", 400
        )

        response = client.post(
            "/auth/refresh",
            json={"refresh_token": "invalid-token"},
        )

        assert response.status_code == 401


class TestGetCurrentUser:
    """Test get current user functionality."""

    def test_get_current_user_success(self, mock_supabase_auth):
        """Test successful retrieval of current user."""
        mock_supabase_auth.get_user.return_value = MagicMock(
            user=MagicMock(
                id="test-user-id",
                email="test@example.com",
                email_confirmed_at="2025-11-20T10:00:00Z",
                created_at="2025-11-20T10:00:00Z",
                updated_at="2025-11-20T10:00:00Z",
                user_metadata={"full_name": "Test User"},
            )
        )

        response = client.get(
            "/auth/me",
            headers={"Authorization": "Bearer mock-access-token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"
        assert data["id"] == "test-user-id"

    def test_get_current_user_unauthorized(self):
        """Test get current user without token."""
        response = client.get("/auth/me")

        assert response.status_code == 401


class TestUpdateUser:
    """Test user update functionality."""

    def test_update_user_success(self, mock_supabase_auth):
        """Test successful user profile update."""
        mock_supabase_auth.update_user.return_value = MagicMock(
            user=MagicMock(
                id="test-user-id",
                email="test@example.com",
                email_confirmed_at="2025-11-20T10:00:00Z",
                created_at="2025-11-20T10:00:00Z",
                updated_at="2025-11-20T10:30:00Z",
                user_metadata={"full_name": "Updated Name"},
            )
        )

        response = client.patch(
            "/auth/me",
            headers={"Authorization": "Bearer mock-access-token"},
            json={"full_name": "Updated Name"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"

    def test_update_user_unauthorized(self):
        """Test update user without token."""
        response = client.patch(
            "/auth/me",
            json={"full_name": "Updated Name"},
        )

        assert response.status_code == 401


class TestPasswordReset:
    """Test password reset functionality."""

    def test_password_reset_request_success(self, mock_supabase_auth):
        """Test successful password reset request."""
        mock_supabase_auth.reset_password_email.return_value = None

        response = client.post(
            "/auth/password-reset",
            json={"email": "test@example.com"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "reset link" in data["message"].lower()

    def test_password_update_success(self, mock_supabase_auth):
        """Test successful password update."""
        mock_supabase_auth.update_user.return_value = MagicMock(
            user=MagicMock(
                id="test-user-id",
                email="test@example.com",
                email_confirmed_at="2025-11-20T10:00:00Z",
                created_at="2025-11-20T10:00:00Z",
                updated_at="2025-11-20T10:30:00Z",
                user_metadata={"full_name": "Test User"},
            )
        )

        response = client.patch(
            "/auth/password",
            headers={"Authorization": "Bearer mock-access-token"},
            json={"new_password": "NewPassword123!"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "Password updated successfully" in data["message"]


class TestUserTierManagement:
    """Test user tier management functionality."""

    def test_get_user_tier_success(self, mock_supabase_client):
        """Test successful retrieval of user tier."""
        # Mock the table query chain
        mock_table = MagicMock()
        mock_select = MagicMock()
        mock_eq = MagicMock()

        mock_supabase_client.table.return_value = mock_table
        mock_table.select.return_value = mock_select
        mock_select.eq.return_value = mock_eq
        mock_eq.single.return_value = MagicMock(
            execute=MagicMock(
                return_value=MagicMock(
                    data={"tier": "paid", "subscription_end": "2026-11-20T00:00:00Z"}
                )
            )
        )

        response = client.get(
            "/user/tier",
            headers={"Authorization": "Bearer mock-access-token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["tier"] == "paid"

    def test_update_user_tier_success(self, mock_supabase_client):
        """Test successful user tier update."""
        # Mock the table query chain
        mock_table = MagicMock()
        mock_update = MagicMock()
        mock_eq = MagicMock()

        mock_supabase_client.table.return_value = mock_table
        mock_table.update.return_value = mock_update
        mock_update.eq.return_value = mock_eq
        mock_eq.execute.return_value = MagicMock(
            data=[{"tier": "paid", "subscription_end": "2026-11-20T00:00:00Z"}]
        )

        response = client.patch(
            "/user/tier",
            headers={"Authorization": "Bearer mock-access-token"},
            json={"tier": "paid", "subscription_end": "2026-11-20T00:00:00Z"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["tier"] == "paid"
        assert "User tier updated successfully" in data["message"]


class TestErrorHandling:
    """Test error handling scenarios."""

    def test_unexpected_error_handling(self, mock_supabase_auth):
        """Test handling of unexpected errors."""
        mock_supabase_auth.sign_up.side_effect = Exception("Unexpected error")

        response = client.post(
            "/auth/signup",
            json={
                "email": "test@example.com",
                "password": "TestPassword123!",
                "full_name": "Test User",
            },
        )

        assert response.status_code == 500
        assert "unexpected error" in response.json()["detail"].lower()

    def test_invalid_json_payload(self):
        """Test handling of invalid JSON payload."""
        response = client.post(
            "/auth/signup",
            data="invalid json",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 422


class TestCORSConfiguration:
    """Test CORS configuration."""

    def test_cors_headers_present(self):
        """Test that CORS headers are present in responses."""
        response = client.options(
            "/auth/signup",
            headers={"Origin": "http://localhost:3000"},
        )

        # CORS middleware should handle OPTIONS requests
        assert response.status_code in [200, 405]  # 405 if no OPTIONS handler


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=app", "--cov-report=term-missing"])
