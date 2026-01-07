import resend
import structlog
from typing import Dict, Any, Optional
import asyncio
from jinja2 import Template

from app.channels.base import NotificationChannel
from app.models import NotificationType, DeliveryStatus, AlertDirection
from app.config import settings
from app.email_templates import (
    PRICE_ALERT_TEMPLATE,
    MARKETING_WELCOME_TEMPLATE,
    PRODUCT_UPDATE_TEMPLATE,
)

logger = structlog.get_logger()


class ResendEmailChannel(NotificationChannel):
    """Email notification channel using Resend API."""

    def __init__(self):
        resend.api_key = settings.RESEND_API_KEY
        self.from_email = settings.RESEND_FROM_EMAIL
        self.from_name = settings.RESEND_FROM_NAME

        self.templates = {
            NotificationType.PRICE_ALERT: PRICE_ALERT_TEMPLATE,
            NotificationType.WELCOME: MARKETING_WELCOME_TEMPLATE,
            NotificationType.PRODUCT_UPDATE: PRODUCT_UPDATE_TEMPLATE,
            NotificationType.MARKETING: MARKETING_WELCOME_TEMPLATE,
        }

    def get_channel_name(self) -> str:
        """Get the name of this notification channel."""
        return "email"

    async def send(
        self,
        recipient: str,
        notification_type: NotificationType,
        data: Dict[str, Any],
    ) -> tuple[DeliveryStatus, Optional[str]]:
        """
        Send an email notification.

        Args:
            recipient: Email address
            notification_type: Type of notification
            data: Email data (subject, template_data, etc.)

        Returns:
            Tuple of (delivery_status, resend_id)
        """
        try:
            html_content = self._render_template(notification_type, data)
            subject = data.get("subject", self._get_default_subject(notification_type))

            params = {
                "from": f"{self.from_name} <{self.from_email}>",
                "to": [recipient],
                "subject": subject,
                "html": html_content,
            }

            response = await asyncio.to_thread(resend.Emails.send, params)

            logger.info(
                "Email sent successfully",
                recipient=recipient,
                notification_type=notification_type,
                resend_id=response.get("id"),
            )

            return DeliveryStatus.SENT, response.get("id")

        except Exception as e:
            logger.error(
                "Failed to send email",
                recipient=recipient,
                notification_type=notification_type,
                error=str(e),
            )
            return DeliveryStatus.FAILED, None

    async def send_batch(
        self,
        recipients: list[str],
        notification_type: NotificationType,
        data: Dict[str, Any],
    ) -> list[tuple[str, DeliveryStatus, Optional[str]]]:
        """
        Send emails to multiple recipients.

        Args:
            recipients: List of email addresses
            notification_type: Type of notification
            data: Email data

        Returns:
            List of tuples: (recipient, delivery_status, resend_id)
        """
        results = []

        for recipient in recipients:
            status, resend_id = await self.send(recipient, notification_type, data)
            results.append((recipient, status, resend_id))

            await asyncio.sleep(0.1)

        return results

    def _render_template(
        self, notification_type: NotificationType, data: Dict[str, Any]
    ) -> str:
        """
        Render email template with data.

        Args:
            notification_type: Type of notification
            data: Template data

        Returns:
            Rendered HTML content
        """
        template_str = self.templates.get(notification_type)
        if not template_str:
            logger.warning(
                "No template found for notification type",
                notification_type=notification_type,
            )
            return self._get_fallback_template(data)

        template = Template(template_str)
        return template.render(**data)

    def _get_default_subject(self, notification_type: NotificationType) -> str:
        """Get default email subject based on notification type."""
        subjects = {
            NotificationType.PRICE_ALERT: "Price Alert Triggered",
            NotificationType.WELCOME: "Welcome to QNT9 Stock Research",
            NotificationType.PRODUCT_UPDATE: "Product Update from QNT9",
            NotificationType.MARKETING: "QNT9 Stock Research Update",
            NotificationType.SECURITY_ALERT: "Security Alert from QNT9",
        }
        return subjects.get(notification_type, "Notification from QNT9")

    def _get_fallback_template(self, data: Dict[str, Any]) -> str:
        """Get fallback template when specific template is not found."""
        message = data.get("message", "You have a new notification from QNT9.")
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <p>{message}</p>
                <hr style="margin: 20px 0; border: none; border-top: 1px solid #ddd;">
                <p style="font-size: 12px; color: #666;">
                    QNT9 Stock Research Platform
                </p>
            </div>
        </body>
        </html>
        """
