from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator
from uuid import UUID


class NotificationType(str, Enum):
    """Types of notifications."""

    PRICE_ALERT = "price_alert"
    MARKETING = "marketing"
    PRODUCT_UPDATE = "product_update"
    SECURITY_ALERT = "security_alert"
    WELCOME = "welcome"


class DeliveryStatus(str, Enum):
    """Notification delivery status."""

    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    BOUNCED = "bounced"


class AlertDirection(str, Enum):
    """Price alert direction."""

    ABOVE = "above"
    BELOW = "below"


class NotificationPreferences(BaseModel):
    """User notification preferences."""

    email_notifications: bool = True
    product_updates: bool = True
    usage_alerts: bool = True
    security_alerts: bool = True
    marketing_emails: bool = False


class NotificationPreferencesUpdate(BaseModel):
    """Update notification preferences."""

    email_notifications: Optional[bool] = None
    product_updates: Optional[bool] = None
    usage_alerts: Optional[bool] = None
    security_alerts: Optional[bool] = None
    marketing_emails: Optional[bool] = None


class PriceAlertData(BaseModel):
    """Price alert notification data."""

    symbol: str = Field(..., min_length=1, max_length=10)
    current_price: float = Field(..., gt=0)
    threshold_price: float = Field(..., gt=0)
    direction: AlertDirection
    user_email: str
    user_name: Optional[str] = None


class MarketingEmailData(BaseModel):
    """Marketing email data."""

    subject: str = Field(..., min_length=1, max_length=200)
    template_name: str = Field(..., min_length=1)
    recipient_emails: list[str] = Field(..., min_items=1)
    template_data: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("recipient_emails")
    @classmethod
    def validate_emails(cls, v: list[str]) -> list[str]:
        """Validate email format."""
        import re

        email_regex = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        for email in v:
            if not re.match(email_regex, email):
                raise ValueError(f"Invalid email format: {email}")
        return v


class NotificationHistoryRecord(BaseModel):
    """Notification history record."""

    id: UUID
    user_id: UUID
    notification_type: NotificationType
    sent_at: datetime
    delivery_status: DeliveryStatus
    resend_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class NotificationHistoryQuery(BaseModel):
    """Query parameters for notification history."""

    user_id: Optional[UUID] = None
    notification_type: Optional[NotificationType] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)


class MessageResponse(BaseModel):
    """Generic message response."""

    message: str
    success: bool = True
