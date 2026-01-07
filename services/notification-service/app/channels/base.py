from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

from app.models import NotificationType, DeliveryStatus


class NotificationChannel(ABC):
    """Abstract base class for notification channels."""

    @abstractmethod
    async def send(
        self,
        recipient: str,
        notification_type: NotificationType,
        data: Dict[str, Any],
    ) -> tuple[DeliveryStatus, Optional[str]]:
        """
        Send a notification through this channel.

        Args:
            recipient: Recipient identifier (email, phone, user_id, etc.)
            notification_type: Type of notification
            data: Notification data

        Returns:
            Tuple of (delivery_status, external_id)
        """
        pass

    @abstractmethod
    async def send_batch(
        self,
        recipients: list[str],
        notification_type: NotificationType,
        data: Dict[str, Any],
    ) -> list[tuple[str, DeliveryStatus, Optional[str]]]:
        """
        Send notifications to multiple recipients.

        Args:
            recipients: List of recipient identifiers
            notification_type: Type of notification
            data: Notification data

        Returns:
            List of tuples: (recipient, delivery_status, external_id)
        """
        pass

    @abstractmethod
    def get_channel_name(self) -> str:
        """Get the name of this notification channel."""
        pass
