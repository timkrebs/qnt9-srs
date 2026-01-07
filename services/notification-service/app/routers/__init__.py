from fastapi import APIRouter, Depends, HTTPException, status
import structlog
from uuid import UUID

from app.auth import get_current_user
from app.database import db
from app.models import (
    NotificationPreferences,
    NotificationPreferencesUpdate,
    MessageResponse,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1", tags=["preferences"])


@router.get("/preferences", response_model=NotificationPreferences)
async def get_preferences(current_user: dict = Depends(get_current_user)):
    """
    Get user's notification preferences.

    Retrieves notification preferences from user_profiles.notification_preferences.
    Returns default preferences if not set.
    """
    try:
        user_id = UUID(current_user["user_id"])

        query = """
            SELECT notification_preferences
            FROM public.user_profiles
            WHERE id = $1
        """

        result = await db.fetchval(query, user_id)

        if result is None:
            logger.info("No preferences found, returning defaults", user_id=str(user_id))
            return NotificationPreferences()

        if isinstance(result, str):
            import json

            result = json.loads(result)

        return NotificationPreferences(**result)

    except Exception as e:
        logger.error("Failed to get preferences", user_id=current_user["user_id"], error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve notification preferences",
        )


@router.patch("/preferences", response_model=MessageResponse)
async def update_preferences(
    preferences: NotificationPreferencesUpdate,
    current_user: dict = Depends(get_current_user),
):
    """
    Update user's notification preferences.

    Updates only the provided fields in notification_preferences JSONB column.
    """
    try:
        user_id = UUID(current_user["user_id"])

        current_prefs_query = """
            SELECT notification_preferences
            FROM public.user_profiles
            WHERE id = $1
        """

        current_prefs = await db.fetchval(current_prefs_query, user_id)

        if current_prefs is None:
            current_prefs_dict = NotificationPreferences().model_dump()
        else:
            if isinstance(current_prefs, str):
                import json

                current_prefs_dict = json.loads(current_prefs)
            else:
                current_prefs_dict = current_prefs

        update_data = preferences.model_dump(exclude_unset=True)
        current_prefs_dict.update(update_data)

        import json

        update_query = """
            UPDATE public.user_profiles
            SET notification_preferences = $1::jsonb,
                updated_at = NOW()
            WHERE id = $2
        """

        await db.execute(update_query, json.dumps(current_prefs_dict), user_id)

        logger.info(
            "Notification preferences updated",
            user_id=str(user_id),
            updated_fields=list(update_data.keys()),
        )

        return MessageResponse(
            message="Notification preferences updated successfully", success=True
        )

    except Exception as e:
        logger.error("Failed to update preferences", user_id=current_user["user_id"], error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update notification preferences",
        )
