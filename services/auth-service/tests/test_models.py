"""
Comprehensive tests for models.py (Pydantic schemas).

Tests validation rules, required fields, and optional fields.
"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from app.models import (
    AuthResponse,
    ErrorResponse,
    MessageResponse,
    PasswordResetRequest,
    PasswordUpdate,
    RefreshToken,
    SessionResponse,
    UserResponse,
    UserSignIn,
    UserSignUp,
    UserStatusUpdate,
    UserTierResponse,
    UserTierUpdate,
    UserUpdate,
)


class TestUserSignUp:
    """Test UserSignUp model validation."""

    def test_valid_signup(self):
        """Test valid signup data."""
        data = UserSignUp(
            email="test@example.com",
            password="SecurePass123!",
            full_name="Test User",
        )
        assert data.email == "test@example.com"
        assert data.password == "SecurePass123!"
        assert data.full_name == "Test User"

    def test_signup_without_full_name(self):
        """Test signup without optional full_name."""
        data = UserSignUp(
            email="test@example.com",
            password="SecurePass123!",
        )
        assert data.email == "test@example.com"
        assert data.full_name is None

    def test_signup_missing_email(self):
        """Test signup with missing email."""
        with pytest.raises(ValidationError) as exc_info:
            UserSignUp(password="SecurePass123!")
        assert "email" in str(exc_info.value)

    def test_signup_missing_password(self):
        """Test signup with missing password."""
        with pytest.raises(ValidationError) as exc_info:
            UserSignUp(email="test@example.com")
        assert "password" in str(exc_info.value)

    def test_signup_invalid_email_format(self):
        """Test signup with invalid email format."""
        with pytest.raises(ValidationError) as exc_info:
            UserSignUp(
                email="not-an-email",
                password="SecurePass123!",
            )
        assert "email" in str(exc_info.value).lower()

    def test_signup_email_without_domain(self):
        """Test signup with email missing domain."""
        with pytest.raises(ValidationError):
            UserSignUp(
                email="test@",
                password="SecurePass123!",
            )

    def test_signup_email_without_at(self):
        """Test signup with email missing @ symbol."""
        with pytest.raises(ValidationError):
            UserSignUp(
                email="testexample.com",
                password="SecurePass123!",
            )


class TestUserSignIn:
    """Test UserSignIn model validation."""

    def test_valid_signin(self):
        """Test valid signin data."""
        data = UserSignIn(
            email="test@example.com",
            password="SecurePass123!",
        )
        assert data.email == "test@example.com"
        assert data.password == "SecurePass123!"

    def test_signin_missing_email(self):
        """Test signin with missing email."""
        with pytest.raises(ValidationError):
            UserSignIn(password="SecurePass123!")

    def test_signin_missing_password(self):
        """Test signin with missing password."""
        with pytest.raises(ValidationError):
            UserSignIn(email="test@example.com")

    def test_signin_invalid_email(self):
        """Test signin with invalid email."""
        with pytest.raises(ValidationError):
            UserSignIn(
                email="invalid-email",
                password="SecurePass123!",
            )


class TestUserUpdate:
    """Test UserUpdate model validation."""

    def test_valid_update_all_fields(self):
        """Test update with all fields."""
        data = UserUpdate(
            email="new@example.com",
            full_name="New Name",
        )
        assert data.email == "new@example.com"
        assert data.full_name == "New Name"

    def test_update_email_only(self):
        """Test update with only email."""
        data = UserUpdate(email="new@example.com")
        assert data.email == "new@example.com"
        assert data.full_name is None

    def test_update_full_name_only(self):
        """Test update with only full_name."""
        data = UserUpdate(full_name="New Name")
        assert data.full_name == "New Name"
        assert data.email is None

    def test_update_empty(self):
        """Test update with no fields."""
        data = UserUpdate()
        assert data.email is None
        assert data.full_name is None

    def test_update_invalid_email(self):
        """Test update with invalid email."""
        with pytest.raises(ValidationError):
            UserUpdate(email="invalid-email")


class TestPasswordUpdate:
    """Test PasswordUpdate model validation."""

    def test_valid_password_update(self):
        """Test valid password update."""
        data = PasswordUpdate(password="NewSecurePass123!")
        assert data.password == "NewSecurePass123!"

    def test_password_update_missing(self):
        """Test password update without password."""
        with pytest.raises(ValidationError):
            PasswordUpdate()


class TestPasswordResetRequest:
    """Test PasswordResetRequest model validation."""

    def test_valid_reset_request(self):
        """Test valid password reset request."""
        data = PasswordResetRequest(email="test@example.com")
        assert data.email == "test@example.com"

    def test_reset_request_missing_email(self):
        """Test reset request without email."""
        with pytest.raises(ValidationError):
            PasswordResetRequest()

    def test_reset_request_invalid_email(self):
        """Test reset request with invalid email."""
        with pytest.raises(ValidationError):
            PasswordResetRequest(email="not-valid")


class TestRefreshToken:
    """Test RefreshToken model validation."""

    def test_valid_refresh_token(self):
        """Test valid refresh token."""
        data = RefreshToken(refresh_token="my-refresh-token-123")
        assert data.refresh_token == "my-refresh-token-123"

    def test_refresh_token_missing(self):
        """Test refresh token without token."""
        with pytest.raises(ValidationError):
            RefreshToken()


class TestUserResponse:
    """Test UserResponse model."""

    def test_valid_user_response(self):
        """Test valid user response."""
        data = UserResponse(
            id="user-uuid-123",
            email="test@example.com",
            full_name="Test User",
            tier="paid",
        )
        assert data.id == "user-uuid-123"
        assert data.email == "test@example.com"
        assert data.full_name == "Test User"
        assert data.tier == "paid"

    def test_user_response_minimal(self):
        """Test user response with minimal fields."""
        data = UserResponse(
            id="user-uuid-123",
            email="test@example.com",
        )
        assert data.id == "user-uuid-123"
        assert data.email == "test@example.com"
        assert data.tier == "free"
        assert data.full_name is None

    def test_user_response_with_dates(self):
        """Test user response with datetime fields."""
        now = datetime.now()
        data = UserResponse(
            id="user-uuid-123",
            email="test@example.com",
            email_confirmed_at=now,
            created_at=now,
            subscription_end=now,
        )
        assert data.email_confirmed_at == now
        assert data.created_at == now
        assert data.subscription_end == now


class TestSessionResponse:
    """Test SessionResponse model."""

    def test_valid_session_response(self):
        """Test valid session response."""
        data = SessionResponse(
            access_token="access-token-123",
            refresh_token="refresh-token-456",
            expires_at=1234567890,
        )
        assert data.access_token == "access-token-123"
        assert data.refresh_token == "refresh-token-456"
        assert data.expires_at == 1234567890

    def test_session_response_without_expires(self):
        """Test session response without expires_at."""
        data = SessionResponse(
            access_token="access-token-123",
            refresh_token="refresh-token-456",
        )
        assert data.expires_at is None


class TestAuthResponse:
    """Test AuthResponse model."""

    def test_valid_auth_response(self):
        """Test valid auth response."""
        data = AuthResponse(
            user=UserResponse(
                id="user-uuid-123",
                email="test@example.com",
            ),
            session=SessionResponse(
                access_token="access-token-123",
                refresh_token="refresh-token-456",
            ),
        )
        assert data.user.id == "user-uuid-123"
        assert data.session.access_token == "access-token-123"

    def test_auth_response_missing_user(self):
        """Test auth response without user."""
        with pytest.raises(ValidationError):
            AuthResponse(
                session=SessionResponse(
                    access_token="access-token-123",
                    refresh_token="refresh-token-456",
                ),
            )


class TestMessageResponse:
    """Test MessageResponse model."""

    def test_valid_message_response(self):
        """Test valid message response."""
        data = MessageResponse(message="Operation successful")
        assert data.message == "Operation successful"
        assert data.success is True

    def test_message_response_failure(self):
        """Test message response with failure."""
        data = MessageResponse(message="Operation failed", success=False)
        assert data.message == "Operation failed"
        assert data.success is False


class TestErrorResponse:
    """Test ErrorResponse model."""

    def test_valid_error_response(self):
        """Test valid error response."""
        data = ErrorResponse(detail="Something went wrong")
        assert data.detail == "Something went wrong"
        assert data.success is False

    def test_error_response_custom_success(self):
        """Test error response with custom success (shouldn't be True for errors)."""
        data = ErrorResponse(detail="Error", success=True)
        assert data.success is True  # Though semantically wrong


class TestUserStatusUpdate:
    """Test UserStatusUpdate model."""

    def test_valid_status_update_active(self):
        """Test status update to active."""
        data = UserStatusUpdate(is_active=True)
        assert data.is_active is True

    def test_valid_status_update_inactive(self):
        """Test status update to inactive."""
        data = UserStatusUpdate(is_active=False)
        assert data.is_active is False

    def test_status_update_missing(self):
        """Test status update without is_active."""
        with pytest.raises(ValidationError):
            UserStatusUpdate()


class TestUserTierUpdate:
    """Test UserTierUpdate model."""

    def test_valid_tier_update_free(self):
        """Test tier update to free."""
        data = UserTierUpdate(tier="free")
        assert data.tier == "free"

    def test_valid_tier_update_paid(self):
        """Test tier update to paid."""
        data = UserTierUpdate(tier="paid")
        assert data.tier == "paid"

    def test_valid_tier_update_enterprise(self):
        """Test tier update to enterprise."""
        data = UserTierUpdate(tier="enterprise")
        assert data.tier == "enterprise"

    def test_tier_update_missing(self):
        """Test tier update without tier."""
        with pytest.raises(ValidationError):
            UserTierUpdate()


class TestUserTierResponse:
    """Test UserTierResponse model."""

    def test_valid_tier_response(self):
        """Test valid tier response."""
        now = datetime.now()
        data = UserTierResponse(
            id="user-uuid-123",
            email="test@example.com",
            tier="paid",
            subscription_start=now,
            subscription_end=now,
        )
        assert data.id == "user-uuid-123"
        assert data.email == "test@example.com"
        assert data.tier == "paid"
        assert data.subscription_start == now
        assert data.subscription_end == now

    def test_tier_response_minimal(self):
        """Test tier response with minimal fields."""
        data = UserTierResponse(
            id="user-uuid-123",
            tier="free",
        )
        assert data.id == "user-uuid-123"
        assert data.tier == "free"
        assert data.email is None
        assert data.subscription_start is None
        assert data.subscription_end is None
