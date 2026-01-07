from fastapi import APIRouter, Depends, HTTPException, status
from datetime import datetime
import structlog
from uuid import UUID

from app.auth import require_admin
from app.database import db
from app.models import (
    MarketingEmailData,
    MessageResponse,
    NotificationHistoryQuery,
    NotificationHistoryRecord,
    NotificationType,
)
from app.channels.email import ResendEmailChannel
from app.metrics import record_email_sent, MetricsTracker

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

email_channel = ResendEmailChannel()


@router.post("/marketing-email", response_model=MessageResponse)
async def send_marketing_email(
    email_data: MarketingEmailData,
    current_user: dict = Depends(require_admin),
):
    """
    Send marketing email campaign to multiple recipients.

    Requires admin role.
    """
    try:
        logger.info(
            "Sending marketing email",
            admin_user=current_user["user_id"],
            recipient_count=len(email_data.recipient_emails),
            template=email_data.template_name,
        )

        results = []

        with MetricsTracker(NotificationType.MARKETING):
            for recipient in email_data.recipient_emails:
                data = {
                    "subject": email_data.subject,
                    **email_data.template_data,
                }

                status, resend_id = await email_channel.send(
                    recipient=recipient,
                    notification_type=NotificationType.MARKETING,
                    data=data,
                )

                success = status.value in ["sent", "delivered"]
                record_email_sent(NotificationType.MARKETING, success)

                insert_query = """
                    INSERT INTO public.notification_history 
                    (user_id, notification_type, sent_at, delivery_status, resend_id, metadata)
                    SELECT 
                        up.id,
                        $1,
                        NOW(),
                        $2,
                        $3,
                        $4::jsonb
                    FROM public.user_profiles up
                    WHERE up.id IN (
                        SELECT id FROM auth.users WHERE email = $5
                    )
                """

                import json

                metadata = {"subject": email_data.subject, "template": email_data.template_name}

                try:
                    await db.execute(
                        insert_query,
                        NotificationType.MARKETING.value,
                        status.value,
                        resend_id,
                        json.dumps(metadata),
                        recipient,
                    )
                except Exception as db_error:
                    logger.warning(
                        "Failed to log notification history",
                        recipient=recipient,
                        error=str(db_error),
                    )

                results.append({"recipient": recipient, "status": status.value})

        successful = sum(1 for r in results if r["status"] in ["sent", "delivered"])
        logger.info(
            "Marketing email campaign completed",
            total=len(results),
            successful=successful,
            failed=len(results) - successful,
        )

        return MessageResponse(
            message=f"Marketing email sent to {successful}/{len(results)} recipients",
            success=True,
        )

    except Exception as e:
        logger.error("Failed to send marketing email", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send marketing email: {str(e)}",
        )


@router.get("/notification-history", response_model=list[NotificationHistoryRecord])
async def get_notification_history(
    user_id: str = None,
    notification_type: str = None,
    start_date: str = None,
    end_date: str = None,
    limit: int = 100,
    offset: int = 0,
    current_user: dict = Depends(require_admin),
):
    """
    Query notification history.

    Requires admin role.
    """
    try:
        conditions = []
        params = []
        param_idx = 1

        if user_id:
            conditions.append(f"user_id = ${param_idx}")
            params.append(UUID(user_id))
            param_idx += 1

        if notification_type:
            conditions.append(f"notification_type = ${param_idx}")
            params.append(notification_type)
            param_idx += 1

        if start_date:
            conditions.append(f"sent_at >= ${param_idx}")
            params.append(datetime.fromisoformat(start_date))
            param_idx += 1

        if end_date:
            conditions.append(f"sent_at <= ${param_idx}")
            params.append(datetime.fromisoformat(end_date))
            param_idx += 1

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        query = f"""
            SELECT 
                id,
                user_id,
                notification_type,
                sent_at,
                delivery_status,
                resend_id,
                metadata
            FROM public.notification_history
            {where_clause}
            ORDER BY sent_at DESC
            LIMIT ${param_idx}
            OFFSET ${param_idx + 1}
        """

        params.extend([limit, offset])

        rows = await db.fetch(query, *params)

        results = []
        for row in rows:
            results.append(
                NotificationHistoryRecord(
                    id=row["id"],
                    user_id=row["user_id"],
                    notification_type=NotificationType(row["notification_type"]),
                    sent_at=row["sent_at"],
                    delivery_status=row["delivery_status"],
                    resend_id=row["resend_id"],
                    metadata=row["metadata"] or {},
                )
            )

        return results

    except Exception as e:
        logger.error("Failed to query notification history", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to query notification history",
        )
