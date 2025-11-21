"""
Pydantic models for User Service.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class UserProfile(BaseModel):
    """User profile response model."""

    id: str
    email: str
    tier: str
    subscription_start: Optional[datetime] = None
    subscription_end: Optional[datetime] = None
    stripe_customer_id: Optional[str] = None
    last_login: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class SubscriptionUpdate(BaseModel):
    """Subscription update request model."""

    plan: str = Field(..., description="Subscription plan: monthly, yearly")
    payment_method_id: Optional[str] = Field(None, description="Stripe payment method ID")


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    service: str
    version: str
    timestamp: str


class MessageResponse(BaseModel):
    """Generic message response."""

    message: str
    success: bool = True
