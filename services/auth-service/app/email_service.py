"""
Email service for sending verification and notification emails.

Supports SMTP with TLS for secure email delivery.
"""

import asyncio
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

import aiosmtplib

from .config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """
    Email service for sending verification and notification emails.

    Uses aiosmtplib for async SMTP support with TLS encryption.
    """

    def __init__(self):
        """Initialize email service with configuration."""
        self.enabled = settings.EMAIL_VERIFICATION_ENABLED
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USER
        self.smtp_password = settings.SMTP_PASSWORD
        self.from_email = settings.SMTP_FROM_EMAIL
        self.from_name = settings.SMTP_FROM_NAME
        self.frontend_url = settings.FRONTEND_URL

        if not self.enabled:
            logger.info("Email verification is disabled")

    async def send_verification_email(
        self, email: str, token: str, full_name: Optional[str] = None
    ) -> bool:
        """
        Send email verification email.

        Args:
            email: Recipient email address
            token: Verification token
            full_name: User's full name (optional)

        Returns:
            True if email sent successfully, False otherwise
        """
        if not self.enabled:
            logger.debug(f"Email verification disabled, skipping email to {email}")
            return True

        try:
            verification_link = f"{self.frontend_url}/verify-email?token={token}"

            subject = "Verify your QNT9 account"

            # Create HTML email body
            html_body = self._create_verification_email_html(
                email=email, full_name=full_name, verification_link=verification_link
            )

            # Create plain text fallback
            text_body = self._create_verification_email_text(
                email=email, full_name=full_name, verification_link=verification_link
            )

            success = await self._send_email(
                to_email=email,
                subject=subject,
                html_body=html_body,
                text_body=text_body,
            )

            if success:
                logger.info(f"Verification email sent to {email}")
            else:
                logger.error(f"Failed to send verification email to {email}")

            return success

        except Exception as e:
            logger.error(
                f"Error sending verification email to {email}: {e}", exc_info=True
            )
            return False

    async def send_password_reset_email(
        self, email: str, token: str, full_name: Optional[str] = None
    ) -> bool:
        """
        Send password reset email.

        Args:
            email: Recipient email address
            token: Password reset token
            full_name: User's full name (optional)

        Returns:
            True if email sent successfully, False otherwise
        """
        if not self.enabled:
            logger.debug(f"Email disabled, skipping password reset email to {email}")
            return True

        try:
            reset_link = f"{self.frontend_url}/reset-password?token={token}"

            subject = "Reset your QNT9 password"

            # Create HTML email body
            html_body = self._create_password_reset_email_html(
                email=email, full_name=full_name, reset_link=reset_link
            )

            # Create plain text fallback
            text_body = self._create_password_reset_email_text(
                email=email, full_name=full_name, reset_link=reset_link
            )

            success = await self._send_email(
                to_email=email,
                subject=subject,
                html_body=html_body,
                text_body=text_body,
            )

            if success:
                logger.info(f"Password reset email sent to {email}")
            else:
                logger.error(f"Failed to send password reset email to {email}")

            return success

        except Exception as e:
            logger.error(
                f"Error sending password reset email to {email}: {e}", exc_info=True
            )
            return False

    async def _send_email(
        self, to_email: str, subject: str, html_body: str, text_body: str
    ) -> bool:
        """
        Send email via SMTP.

        Args:
            to_email: Recipient email address
            subject: Email subject
            html_body: HTML version of email body
            text_body: Plain text version of email body

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            # Create multipart message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = f"{self.from_name} <{self.from_email}>"
            message["To"] = to_email

            # Attach text and HTML parts
            text_part = MIMEText(text_body, "plain")
            html_part = MIMEText(html_body, "html")

            message.attach(text_part)
            message.attach(html_part)

            # Send email via SMTP
            await aiosmtplib.send(
                message,
                hostname=self.smtp_host,
                port=self.smtp_port,
                username=self.smtp_user,
                password=self.smtp_password,
                start_tls=True,
                timeout=10.0,
            )

            return True

        except aiosmtplib.SMTPException as e:
            logger.error(f"SMTP error sending email to {to_email}: {e}")
            return False
        except asyncio.TimeoutError:
            logger.error(f"Timeout sending email to {to_email}")
            return False
        except Exception as e:
            logger.error(
                f"Unexpected error sending email to {to_email}: {e}", exc_info=True
            )
            return False

    def _create_verification_email_html(
        self, email: str, full_name: Optional[str], verification_link: str
    ) -> str:
        """Create HTML body for verification email."""
        greeting = f"Hi {full_name}," if full_name else "Hello,"

        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background-color: #f8f9fa; padding: 20px; border-radius: 5px;">
        <h1 style="color: #007bff; margin-top: 0;">Welcome to QNT9 Stock Research</h1>
        
        <p>{greeting}</p>
        
        <p>Thank you for signing up for QNT9 Stock Research System. To complete your registration and start analyzing stocks, please verify your email address.</p>
        
        <div style="text-align: center; margin: 30px 0;">
            <a href="{verification_link}" 
               style="background-color: #007bff; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block; font-weight: bold;">
                Verify Email Address
            </a>
        </div>
        
        <p>Or copy and paste this link into your browser:</p>
        <p style="word-break: break-all; color: #007bff;">{verification_link}</p>
        
        <p>This verification link will expire in 24 hours.</p>
        
        <hr style="border: none; border-top: 1px solid #dee2e6; margin: 20px 0;">
        
        <p style="font-size: 12px; color: #6c757d;">
            If you didn't create an account with QNT9, you can safely ignore this email.
        </p>
        
        <p style="font-size: 12px; color: #6c757d;">
            Best regards,<br>
            The QNT9 Team
        </p>
    </div>
</body>
</html>
"""

    def _create_verification_email_text(
        self, email: str, full_name: Optional[str], verification_link: str
    ) -> str:
        """Create plain text body for verification email."""
        greeting = f"Hi {full_name}," if full_name else "Hello,"

        return f"""{greeting}

Thank you for signing up for QNT9 Stock Research System. To complete your registration and start analyzing stocks, please verify your email address.

Verify your email by clicking this link:
{verification_link}

This verification link will expire in 24 hours.

If you didn't create an account with QNT9, you can safely ignore this email.

Best regards,
The QNT9 Team
"""

    def _create_password_reset_email_html(
        self, email: str, full_name: Optional[str], reset_link: str
    ) -> str:
        """Create HTML body for password reset email."""
        greeting = f"Hi {full_name}," if full_name else "Hello,"

        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background-color: #f8f9fa; padding: 20px; border-radius: 5px;">
        <h1 style="color: #007bff; margin-top: 0;">Password Reset Request</h1>
        
        <p>{greeting}</p>
        
        <p>We received a request to reset the password for your QNT9 account ({email}).</p>
        
        <div style="text-align: center; margin: 30px 0;">
            <a href="{reset_link}" 
               style="background-color: #dc3545; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block; font-weight: bold;">
                Reset Password
            </a>
        </div>
        
        <p>Or copy and paste this link into your browser:</p>
        <p style="word-break: break-all; color: #007bff;">{reset_link}</p>
        
        <p>This password reset link will expire in 1 hour.</p>
        
        <hr style="border: none; border-top: 1px solid #dee2e6; margin: 20px 0;">
        
        <p style="font-size: 12px; color: #6c757d;">
            If you didn't request a password reset, you can safely ignore this email. Your password will remain unchanged.
        </p>
        
        <p style="font-size: 12px; color: #6c757d;">
            Best regards,<br>
            The QNT9 Team
        </p>
    </div>
</body>
</html>
"""

    def _create_password_reset_email_text(
        self, email: str, full_name: Optional[str], reset_link: str
    ) -> str:
        """Create plain text body for password reset email."""
        greeting = f"Hi {full_name}," if full_name else "Hello,"

        return f"""{greeting}

We received a request to reset the password for your QNT9 account ({email}).

Reset your password by clicking this link:
{reset_link}

This password reset link will expire in 1 hour.

If you didn't request a password reset, you can safely ignore this email. Your password will remain unchanged.

Best regards,
The QNT9 Team
"""


# Global email service instance
email_service = EmailService()
