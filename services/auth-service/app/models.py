"""
Pydantic models for request/response schemas.

Defines data models for authentication API endpoints using Supabase Auth.
"""

from datetime import datetime
from typing import Any, Dict, Optional, Union

from pydantic import BaseModel, EmailStr, Field, field_validator

from .validators import PasswordValidator, sanitize_full_name

# Request Models


class UserSignUp(BaseModel):
    """Model for user registration."""

    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: Optional[str] = Field(None, max_length=255)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Validate password meets complexity requirements."""
        is_valid, error_message = PasswordValidator.validate(v)
        if not is_valid:
            raise ValueError(error_message)
        return v

    @field_validator("full_name")
    @classmethod
    def sanitize_name(cls, v: Optional[str]) -> Optional[str]:
        """Sanitize full name to prevent XSS."""
        if v is None:
            return None
        return sanitize_full_name(v)


class UserSignIn(BaseModel):
    """Model for user sign in."""

    email: EmailStr
    password: str = Field(..., min_length=1, max_length=128)


class UserUpdate(BaseModel):
    """Model for updating user profile."""

    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, max_length=255)

    @field_validator("full_name")
    @classmethod
    def sanitize_name(cls, v: Optional[str]) -> Optional[str]:
        """Sanitize full name to prevent XSS."""
        if v is None:
            return None
        return sanitize_full_name(v)


class PasswordUpdate(BaseModel):
    """Model for updating password."""

    password: str = Field(..., min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Validate password meets complexity requirements."""
        is_valid, error_message = PasswordValidator.validate(v)
        if not is_valid:
            raise ValueError(error_message)
        return v


class PasswordChangeRequest(BaseModel):
    """Model for changing password with current password verification."""

    current_password: str = Field(..., min_length=1, max_length=128)
    new_password: str = Field(..., min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Validate new password meets complexity requirements."""
        is_valid, error_message = PasswordValidator.validate(v)
        if not is_valid:
            raise ValueError(error_message)
        return v


class PasswordResetRequest(BaseModel):
    """Model for requesting password reset."""

    email: EmailStr


class RefreshToken(BaseModel):
    """Model for refreshing session token."""

    refresh_token: str


# Response Models


class UserResponse(BaseModel):
    """Model for user data in responses (Supabase format)."""

    id: str
    email: str
    email_confirmed_at: Optional[str] = None
    phone: Optional[str] = None
    created_at: Optional[str] = None
    last_sign_in_at: Optional[str] = None
    user_metadata: Dict[str, Any] = Field(default_factory=dict)
    app_metadata: Dict[str, Any] = Field(default_factory=dict)
    tier: str = "free"
    role: str = "user"
    full_name: Optional[str] = None
    subscription_start: Optional[str] = None
    subscription_end: Optional[str] = None
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    last_login: Optional[str] = None

    @field_validator(
        "email_confirmed_at",
        "created_at",
        "last_sign_in_at",
        "subscription_start",
        "subscription_end",
        "last_login",
        mode="before",
    )
    @classmethod
    def convert_datetime_to_string(
        cls, v: Optional[Union[str, datetime]]
    ) -> Optional[str]:
        """Convert datetime objects to ISO format strings."""
        if v is None:
            return None
        if isinstance(v, datetime):
            return v.isoformat()
        return v


class SessionResponse(BaseModel):
    """Model for session data (Supabase format)."""

    access_token: str
    refresh_token: str
    expires_in: Optional[int] = None
    expires_at: Optional[int] = None
    token_type: str = "bearer"


class AuthResponse(BaseModel):
    """Model for authentication response with user and session."""

    user: UserResponse
    session: Optional[SessionResponse] = None


class MessageResponse(BaseModel):
    """Generic message response."""

    message: str
    success: bool = True


class ErrorResponse(BaseModel):
    """Error response model."""

    detail: str
    success: bool = False


class PasswordReset(BaseModel):
    """Model for admin password reset"""

    new_password: str = Field(..., min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Validate password meets complexity requirements."""
        is_valid, error_message = PasswordValidator.validate(v)
        if not is_valid:
            raise ValueError(error_message)
        return v


class UserStatusUpdate(BaseModel):
    """Model for updating user active status"""

    is_active: bool


class UserTierUpdate(BaseModel):
    """Model for updating user subscription tier."""

    tier: str


class UserTierResponse(BaseModel):
    """Model for user tier response."""

    id: str
    email: Optional[str] = None
    tier: str
    subscription_start: Optional[datetime] = None
    subscription_end: Optional[datetime] = None
