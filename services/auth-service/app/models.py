"""
Pydantic models for request/response schemas.

Defines data models for authentication API endpoints using Supabase.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr

# Request Models


class UserSignUp(BaseModel):
    """Model for user registration."""

    email: EmailStr
    password: str
    full_name: Optional[str] = None


class UserSignIn(BaseModel):
    """Model for user sign in."""

    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    """Model for updating user profile."""

    email: Optional[EmailStr] = None
    full_name: Optional[str] = None


class PasswordUpdate(BaseModel):
    """Model for updating password."""

    password: str


class PasswordResetRequest(BaseModel):
    """Model for requesting password reset."""

    email: EmailStr


class RefreshToken(BaseModel):
    """Model for refreshing session token."""

    refresh_token: str


# Response Models


class UserResponse(BaseModel):
    """Model for user data in responses."""

    id: str
    email: str
    full_name: Optional[str] = None
    email_confirmed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class SessionResponse(BaseModel):
    """Model for session data."""

    access_token: str
    refresh_token: str
    expires_at: Optional[int] = None


class AuthResponse(BaseModel):
    """Model for authentication response with user and session."""

    user: UserResponse
    session: SessionResponse


class MessageResponse(BaseModel):
    """Generic message response."""

    message: str
    success: bool = True


class ErrorResponse(BaseModel):
    """Error response model."""

    detail: str
    success: bool = False

    new_password: str


class PasswordReset(BaseModel):
    """Model for admin password reset"""

    new_password: str


class UserStatusUpdate(BaseModel):
    """Model for updating user active status"""

    is_active: bool
