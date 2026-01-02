"""
User management endpoints for API v1.

This module contains all user-related endpoints including profile management,
password updates, and subscription tier management using Supabase Auth.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status

from ...audit import AuditAction, audit_service
from ...supabase_auth_service import AuthError, auth_service
from ...dependencies import get_current_user_from_token
from ...middleware import check_password_reset_rate_limit
from ...models import (
    MessageResponse,
    PasswordResetRequest,
    PasswordUpdate,
    UserResponse,
    UserTierResponse,
    UserTierUpdate,
    UserUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["User Management"])


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user",
)
async def get_current_user(current_user: dict = Depends(get_current_user_from_token)):
    """
    Get current authenticated user information.

    Requires a valid access token in the Authorization header.

    Args:
        current_user: Injected user data from token

    Returns:
        User information

    Raises:
        HTTPException: If token is invalid or user not found
    """
    try:
        user = await auth_service.get_user(current_user["user_id"])

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        return UserResponse(**user)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error getting user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        )


@router.patch(
    "/me",
    response_model=UserResponse,
    summary="Update current user",
)
async def update_current_user(
    user_update: UserUpdate,
    request: Request,
    current_user: dict = Depends(get_current_user_from_token),
):
    """
    Update current user's profile information.

    Requires a valid access token in the Authorization header.

    Args:
        user_update: Updated user data (email, full_name)
        request: FastAPI request object for IP/user-agent capture
        current_user: Injected user data from token

    Returns:
        Updated user information

    Raises:
        HTTPException: If update fails
    """
    try:
        # Capture client info for audit
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")
        
        # Track changes for audit
        changes = {}
        if user_update.email and user_update.email != current_user.get("email"):
            changes["email"] = {
                "old": current_user.get("email"),
                "new": user_update.email
            }
        if user_update.full_name and user_update.full_name != current_user.get("full_name"):
            changes["full_name"] = {
                "old": current_user.get("full_name"),
                "new": user_update.full_name
            }
        
        result = await auth_service.update_user(
            user_id=current_user["user_id"],
            email=user_update.email,
            full_name=user_update.full_name,
        )

        # Log user profile update
        if changes:
            await audit_service.log_auth_event(
                action=AuditAction.USER_UPDATE,
                user_id=current_user["user_id"],
                email=current_user.get("email"),
                ip_address=ip_address,
                user_agent=user_agent,
                success=True,
                details={"changes": changes}
            )

        return UserResponse(**result)

    except AuthError as e:
        logger.error(f"User update failed: {e.message}")
        
        # Log failed user update
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")
        await audit_service.log_auth_event(
            action=AuditAction.USER_UPDATE,
            user_id=current_user["user_id"],
            email=current_user.get("email"),
            ip_address=ip_address,
            user_agent=user_agent,
            success=False,
            details={"error": e.message}
        )
        
        if e.code == "email_exists":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already in use",
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Update failed: {e.message}",
        )
    except Exception as e:
        logger.exception(f"Unexpected error updating user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during update",
        )


@router.patch(
    "/me/password",
    response_model=MessageResponse,
    summary="Update password",
)
async def update_password(
    password_update: PasswordUpdate,
    request: Request,
    current_user: dict = Depends(get_current_user_from_token),
):
    """
    Update current user's password.

    Requires a valid access token in the Authorization header.

    Args:
        password_update: New password
        request: FastAPI request object for IP/user-agent capture
        current_user: Injected user data from token

    Returns:
        Success message

    Raises:
        HTTPException: If password update fails
    """
    try:
        # Capture client info for audit
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")
        
        await auth_service.update_user(
            user_id=current_user["user_id"],
            password=password_update.password,
        )

        # Log successful password change
        await audit_service.log_auth_event(
            action=AuditAction.PASSWORD_CHANGE,
            user_id=current_user["user_id"],
            email=current_user.get("email"),
            ip_address=ip_address,
            user_agent=user_agent,
            success=True,
            details={"initiated_by": "user"}
        )

        return MessageResponse(
            message="Password updated successfully",
            success=True,
        )

    except AuthError as e:
        logger.error(f"Password update failed: {e.message}")
        
        # Log failed password change
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")
        await audit_service.log_auth_event(
            action=AuditAction.PASSWORD_CHANGE,
            user_id=current_user["user_id"],
            email=current_user.get("email"),
            ip_address=ip_address,
            user_agent=user_agent,
            success=False,
            details={"error": e.message}
        )
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Password update failed: {e.message}",
        )
    except Exception as e:
        logger.exception(f"Unexpected error updating password: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during password update",
        )


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    summary="Request password reset",
    dependencies=[Depends(check_password_reset_rate_limit)],
)
async def request_password_reset(reset_request: PasswordResetRequest, request: Request):
    """
    Request a password reset email.

    Sends a password reset link to the user's email address.

    Args:
        reset_request: Email address for password reset
        request: FastAPI request object for IP/user-agent capture

    Returns:
        Success message (always returns success for security)

    Raises:
        HTTPException: If request fails
    """
    try:
        # Capture client info for audit
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")
        
        await auth_service.reset_password_request(reset_request.email)

        # Log password reset request
        await audit_service.log_auth_event(
            action=AuditAction.PASSWORD_RESET_REQUEST,
            email=reset_request.email,
            ip_address=ip_address,
            user_agent=user_agent,
            success=True,
            details={"email_sent": True}
        )

        return MessageResponse(
            message="If the email exists, a password reset link has been sent.",
            success=True,
        )

    except Exception as e:
        logger.exception(f"Unexpected error requesting password reset: {e}")
        
        # Log failed password reset request
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")
        await audit_service.log_auth_event(
            action=AuditAction.PASSWORD_RESET_REQUEST,
            email=reset_request.email,
            ip_address=ip_address,
            user_agent=user_agent,
            success=False,
            details={"error": str(e)}
        )
        
        # Don't reveal errors for security
        return MessageResponse(
            message="If the email exists, a password reset link has been sent.",
            success=True,
        )


@router.get(
    "/me/tier",
    response_model=UserTierResponse,
    summary="Get user tier information",
)
async def get_user_tier(current_user: dict = Depends(get_current_user_from_token)):
    """
    Get current user's subscription tier.

    Requires a valid access token in the Authorization header.

    Args:
        current_user: Injected user data from token

    Returns:
        User tier information

    Raises:
        HTTPException: If token is invalid or tier fetch fails
    """
    try:
        tier_data = await auth_service.get_user_tier(current_user["user_id"])

        return UserTierResponse(
            id=tier_data["id"],
            email=current_user["email"],
            tier=tier_data["tier"],
            subscription_start=tier_data.get("subscription_start"),
            subscription_end=tier_data.get("subscription_end"),
        )
    except AuthError as e:
        logger.error(f"Error getting user tier: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve tier information",
        )
    except Exception as e:
        logger.exception(f"Error getting user tier: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve tier information",
        )


@router.patch(
    "/me/tier",
    response_model=UserTierResponse,
    summary="Update user tier (upgrade/downgrade)",
)
async def update_user_tier(
    tier_update: UserTierUpdate,
    request: Request,
    current_user: dict = Depends(get_current_user_from_token),
):
    """
    Update user's subscription tier.

    Requires a valid access token in the Authorization header.

    Args:
        tier_update: New tier information
        request: FastAPI request object for IP/user-agent capture
        current_user: Injected user data from token

    Returns:
        Updated user tier information

    Raises:
        HTTPException: If token is invalid or tier update fails
    """
    try:
        # Capture client info for audit
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")
        
        # Get old tier for audit
        old_tier = current_user.get("tier", "unknown")
        
        updated_tier = await auth_service.update_user_tier(
            current_user["user_id"],
            tier_update.tier,
        )

        # Log tier update
        await audit_service.log_data_change(
            action=AuditAction.TIER_UPDATE,
            user_id=current_user["user_id"],
            email=current_user.get("email"),
            ip_address=ip_address,
            user_agent=user_agent,
            old_value=old_tier,
            new_value=tier_update.tier,
            details={
                "subscription_start": str(updated_tier.get("subscription_start")),
                "subscription_end": str(updated_tier.get("subscription_end"))
            }
        )

        return UserTierResponse(
            id=updated_tier["id"],
            email=updated_tier["email"],
            tier=updated_tier["tier"],
            subscription_start=updated_tier.get("subscription_start"),
            subscription_end=updated_tier.get("subscription_end"),
        )
    except AuthError as e:
        logger.error(f"Error updating user tier: {e.message}")
        
        # Log failed tier update
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")
        await audit_service.log_auth_event(
            action=AuditAction.TIER_UPDATE,
            user_id=current_user["user_id"],
            email=current_user.get("email"),
            ip_address=ip_address,
            user_agent=user_agent,
            success=False,
            details={"error": e.message, "attempted_tier": tier_update.tier}
        )
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update tier: {e.message}",
        )
    except Exception as e:
        logger.exception(f"Error updating user tier: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update tier",
        )
