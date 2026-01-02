"""
Audit logging service for tracking security and business events.

Records user actions, authentication events, and data changes for compliance
and security monitoring.
"""

import json
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional

import asyncpg
from prometheus_client import Counter

from .database import db_manager
from .logging_config import get_logger

logger = get_logger(__name__)


class AuditAction(str, Enum):
    """Standard audit actions for consistent logging."""

    # Authentication events
    USER_SIGNUP = "user.signup"
    USER_SIGNIN = "user.signin"
    USER_SIGNOUT = "user.signout"
    USER_SIGNIN_FAILED = "user.signin.failed"
    TOKEN_REFRESH = "token.refresh"

    # Password management
    PASSWORD_CHANGE = "password.change"
    PASSWORD_RESET_REQUEST = "password.reset.request"
    PASSWORD_RESET_CONFIRM = "password.reset.confirm"

    # Email verification
    EMAIL_VERIFICATION_SENT = "email.verification.sent"
    EMAIL_VERIFIED = "email.verified"

    # User profile
    USER_UPDATE = "user.update"
    USER_TIER_UPDATE = "user.tier.update"

    # Session management
    SESSION_REVOKE = "session.revoke"
    SESSION_REVOKE_ALL = "session.revoke.all"


# Prometheus metrics for audit events
audit_events_total = Counter(
    "audit_events_total", "Total number of audit events logged", ["action", "success"]
)


class AuditService:
    """
    Service for logging audit events to database.

    Provides async methods to record user actions, authentication events,
    and data changes for security and compliance purposes.
    """

    @staticmethod
    async def log(
        action: str,
        user_id: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        success: bool = True,
    ) -> bool:
        """
        Log an audit event to the database.

        Args:
            action: Action identifier (use AuditAction enum values)
            user_id: UUID of the user performing the action
            entity_type: Type of entity being acted upon
            entity_id: UUID of the entity being acted upon
            old_values: Previous values (for updates)
            new_values: New values (for updates/creates)
            ip_address: IP address of the requester
            user_agent: User agent string from request
            success: Whether the action was successful

        Returns:
            True if logged successfully, False otherwise
        """
        try:
            # Sanitize sensitive data from values
            if old_values:
                old_values = AuditService._sanitize_values(old_values)
            if new_values:
                new_values = AuditService._sanitize_values(new_values)

            await db_manager.execute(
                """
                INSERT INTO audit_log 
                (user_id, action, entity_type, entity_id, old_values, new_values, 
                 ip_address, user_agent, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                """,
                user_id,
                action,
                entity_type,
                entity_id,
                json.dumps(old_values) if old_values else None,
                json.dumps(new_values) if new_values else None,
                ip_address,
                user_agent,
                datetime.now(timezone.utc),
            )

            # Update metrics
            audit_events_total.labels(action=action, success=str(success)).inc()

            logger.debug(
                f"Audit event logged: {action}",
                extra={
                    "extra_fields": {
                        "action": action,
                        "user_id": user_id,
                        "entity_type": entity_type,
                        "success": success,
                    }
                },
            )

            return True

        except asyncpg.PostgresError as e:
            logger.error(
                f"Database error logging audit event: {e}",
                extra={"extra_fields": {"action": action, "user_id": user_id, "error": str(e)}},
            )
            return False
        except Exception as e:
            logger.error(
                f"Unexpected error logging audit event: {e}",
                exc_info=True,
                extra={"extra_fields": {"action": action, "user_id": user_id}},
            )
            return False

    @staticmethod
    def _sanitize_values(values: Dict[str, Any]) -> Dict[str, Any]:
        """
        Remove sensitive fields from audit log values.

        Args:
            values: Dictionary of values to sanitize

        Returns:
            Sanitized dictionary with sensitive fields removed or masked
        """
        sensitive_fields = {
            "password",
            "password_hash",
            "token",
            "access_token",
            "refresh_token",
            "secret",
            "api_key",
            "private_key",
        }

        sanitized = {}
        for key, value in values.items():
            if key.lower() in sensitive_fields or any(s in key.lower() for s in sensitive_fields):
                sanitized[key] = "REDACTED"
            elif isinstance(value, dict):
                sanitized[key] = AuditService._sanitize_values(value)
            else:
                sanitized[key] = value

        return sanitized

    @staticmethod
    async def log_auth_event(
        action: AuditAction,
        user_id: Optional[str],
        email: Optional[str],
        ip_address: Optional[str],
        user_agent: Optional[str],
        success: bool = True,
        details: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Log an authentication-related event.

        Convenience method for logging auth events with consistent structure.

        Args:
            action: Authentication action (from AuditAction enum)
            user_id: UUID of the user
            email: Email address of the user
            ip_address: IP address of the requester
            user_agent: User agent string
            success: Whether the action was successful
            details: Additional details to log

        Returns:
            True if logged successfully, False otherwise
        """
        new_values = {"email": email}
        if details:
            new_values.update(details)

        return await AuditService.log(
            action=action.value,
            user_id=user_id,
            entity_type="user",
            entity_id=user_id,
            new_values=new_values,
            ip_address=ip_address,
            user_agent=user_agent,
            success=success,
        )

    @staticmethod
    async def log_data_change(
        action: AuditAction,
        user_id: str,
        entity_type: str,
        entity_id: str,
        old_values: Optional[Dict[str, Any]],
        new_values: Dict[str, Any],
        ip_address: Optional[str],
        user_agent: Optional[str],
    ) -> bool:
        """
        Log a data change event (create, update, delete).

        Convenience method for logging data modifications.

        Args:
            action: Action performed (from AuditAction enum)
            user_id: UUID of the user making the change
            entity_type: Type of entity being modified
            entity_id: UUID of the entity
            old_values: Previous values (None for create)
            new_values: New values
            ip_address: IP address of the requester
            user_agent: User agent string

        Returns:
            True if logged successfully, False otherwise
        """
        return await AuditService.log(
            action=action.value,
            user_id=user_id,
            entity_type=entity_type,
            entity_id=entity_id,
            old_values=old_values,
            new_values=new_values,
            ip_address=ip_address,
            user_agent=user_agent,
            success=True,
        )


# Global audit service instance
audit_service = AuditService()
