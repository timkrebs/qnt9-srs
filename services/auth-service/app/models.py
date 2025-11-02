"""
Pydantic models for request/response schemas
"""

from typing import Optional

from pydantic import BaseModel, EmailStr


class UserBase(BaseModel):
    """Base user model"""

    username: str
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None


class UserCreate(UserBase):
    """Model for creating a new user"""

    password: str


class User(UserBase):
    """Model for user response (without password)"""

    id: int
    is_active: bool

    class Config:
        from_attributes = True


class UserInDB(User):
    """Model for user stored in database (with hashed password)"""

    hashed_password: str


class UserUpdate(BaseModel):
    """Model for updating user profile"""

    email: Optional[EmailStr] = None
    full_name: Optional[str] = None


class PasswordChange(BaseModel):
    """Model for changing user password"""

    current_password: str
    new_password: str


class PasswordReset(BaseModel):
    """Model for admin password reset"""

    new_password: str


class UserStatusUpdate(BaseModel):
    """Model for updating user active status"""

    is_active: bool
