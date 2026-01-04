"""
Authentication endpoints for API v1.

This module contains all authentication-related endpoints including signup,
signin, signout, session refresh, and password reset using Supabase Auth.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status

from ...audit import AuditAction, audit_service
from ...dependencies import get_current_user_from_token
from ...middleware import check_auth_rate_limit
from ...models import (AuthResponse, MessageResponse, PasswordUpdate,
                       RefreshToken, SessionResponse, UserResponse, UserSignIn,
                       UserSignUp)
from ...supabase_auth_service import AuthError, auth_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/signup",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register new user",
    dependencies=[Depends(check_auth_rate_limit)],
)
async def sign_up(user_data: UserSignUp, request: Request):
    """
    Register a new user with email and password.

    Creates a new user account and returns session tokens for immediate authentication.

    Args:
        user_data: User registration data (email, password, full_name)
        request: FastAPI request object

    Returns:
        User data and session tokens

    Raises:
        HTTPException: If registration fails
    """
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    try:
        result = await auth_service.sign_up(
            email=user_data.email,
            password=user_data.password,
            full_name=user_data.full_name,
        )

        # Log successful signup
        await audit_service.log_auth_event(
            action=AuditAction.USER_SIGNUP,
            user_id=result["user"]["id"],
            email=user_data.email,
            ip_address=ip_address,
            user_agent=user_agent,
            success=True,
            details={"tier": result["user"]["tier"]},
        )

        return AuthResponse(
            user=UserResponse(**result["user"]),
            session=SessionResponse(**result["session"]),
        )

    except AuthError as e:
        logger.error(f"Sign up failed: {e.message}")

        # Log failed signup
        await audit_service.log_auth_event(
            action=AuditAction.USER_SIGNUP,
            user_id=None,
            email=user_data.email,
            ip_address=ip_address,
            user_agent=user_agent,
            success=False,
            details={"error": e.message},
        )

        if e.code == "email_exists":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Registration failed: {e.message}",
        )
    except Exception as e:
        logger.exception(f"Unexpected error during sign up: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during registration",
        )


@router.post(
    "/signin",
    response_model=AuthResponse,
    summary="Sign in user",
    dependencies=[Depends(check_auth_rate_limit)],
)
async def sign_in(credentials: UserSignIn, request: Request):
    """
    Sign in a user with email and password.

    Authenticates the user and returns session tokens.

    Args:
        credentials: User credentials (email, password)
        request: FastAPI request object for IP/user-agent capture

    Returns:
        User data and session tokens

    Raises:
        HTTPException: If authentication fails
    """
    try:
        # Capture client info for audit
        client_ip = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")

        result = await auth_service.sign_in(
            email=credentials.email,
            password=credentials.password,
            ip_address=client_ip,
            user_agent=user_agent,
        )

        # Log successful signin
        await audit_service.log_auth_event(
            action=AuditAction.USER_SIGNIN,
            user_id=result["user"]["id"],
            email=result["user"]["email"],
            ip_address=client_ip,
            user_agent=user_agent,
            success=True,
            details={"user_id": result["user"]["id"]},
        )

        return AuthResponse(
            user=UserResponse(**result["user"]),
            session=SessionResponse(**result["session"]),
        )

    except AuthError as e:
        logger.error(f"Sign in failed: {e.message}")

        # Log failed signin
        await audit_service.log_auth_event(
            action=AuditAction.USER_SIGNIN_FAILED,
            user_id=None,
            email=credentials.email,
            ip_address=client_ip,
            user_agent=user_agent,
            success=False,
            details={"error": e.message, "code": e.code},
        )

        if e.code == "invalid_credentials":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )
        if e.code == "account_disabled":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is disabled",
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
        )
    except Exception as e:
        logger.exception(f"Unexpected error during sign in: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during sign in",
        )


@router.post(
    "/signout",
    response_model=MessageResponse,
    summary="Sign out user",
)
async def sign_out(
    request: Request,
    current_user: dict = Depends(get_current_user_from_token),
):
    """
    Sign out the current user.

    Invalidates the user's session in Supabase Auth.

    Args:
        request: FastAPI request object for IP/user-agent capture
        current_user: User info extracted from access token

    Returns:
        Success message

    Raises:
        HTTPException: If sign out fails
    """
    try:
        # Capture client info for audit
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")

        # Extract access token from Authorization header
        auth_header = request.headers.get("authorization", "")
        if not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header",
            )
        access_token = auth_header.split(" ")[1]

        result = await auth_service.sign_out(access_token)

        # Extract user info for audit (returned by service)
        user_id = result.get("user_id")
        email = result.get("email")

        # Log successful signout
        await audit_service.log_auth_event(
            action=AuditAction.USER_SIGNOUT,
            user_id=user_id,
            email=email,
            ip_address=ip_address,
            user_agent=user_agent,
            success=True,
            details={"token_provided": True},
        )

        return MessageResponse(
            message="Signed out successfully",
            success=True,
        )

    except AuthError as e:
        logger.error(f"Sign out failed: {e.message}")

        # Log failed signout
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")
        await audit_service.log_auth_event(
            action=AuditAction.USER_SIGNOUT,
            user_id=None,
            email=None,
            ip_address=ip_address,
            user_agent=user_agent,
            success=False,
            details={"error": e.message},
        )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Sign out failed: {e.message}",
        )
    except Exception as e:
        logger.exception(f"Unexpected error during sign out: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during sign out",
        )


@router.post(
    "/refresh",
    response_model=SessionResponse,
    summary="Refresh session",
)
async def refresh_session(token_data: RefreshToken, request: Request):
    """
    Refresh an expired session.

    Uses a refresh token to obtain new access and refresh tokens.

    Args:
        token_data: Refresh token
        request: FastAPI request object for IP/user-agent capture

    Returns:
        New session tokens

    Raises:
        HTTPException: If refresh fails
    """
    try:
        # Capture client info for audit
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")

        result = await auth_service.refresh_session(token_data.refresh_token)

        # Extract user info for audit (included in result)
        user_id = result.pop("user_id", None)
        email = result.pop("email", None)

        # Log successful token refresh
        await audit_service.log_auth_event(
            action=AuditAction.TOKEN_REFRESH,
            user_id=user_id,
            email=email,
            ip_address=ip_address,
            user_agent=user_agent,
            success=True,
            details={"refreshed": True},
        )

        return SessionResponse(**result)

    except AuthError as e:
        logger.error(f"Session refresh failed: {e.message}")

        # Log failed token refresh
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")
        await audit_service.log_auth_event(
            action=AuditAction.TOKEN_REFRESH,
            user_id=None,
            email=None,
            ip_address=ip_address,
            user_agent=user_agent,
            success=False,
            details={"error": e.message, "code": e.code},
        )

        if e.code in (
            "invalid_token",
            "token_revoked",
            "token_expired",
            "invalid_refresh_token",
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token",
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session refresh failed",
        )
    except Exception as e:
        logger.exception(f"Unexpected error refreshing session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during session refresh",
        )


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    summary="Update password with reset token",
)
async def update_password(
    password_data: PasswordUpdate,
    request: Request,
    current_user: dict = Depends(get_current_user_from_token),
):
    """
    Update user password using reset token from email.

    This endpoint is called after the user clicks the reset link in their email.
    The access token from the reset link is passed in the Authorization header.

    Args:
        password_data: New password
        request: FastAPI request object for IP/user-agent capture
        current_user: User info extracted from reset token

    Returns:
        Success message

    Raises:
        HTTPException: If password update fails
    """
    try:
        # Capture client info for audit
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")

        # Extract access token from Authorization header
        auth_header = request.headers.get("authorization", "")
        if not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header",
            )
        access_token = auth_header.split(" ")[1]

        # Update password
        await auth_service.update_password(access_token, password_data.password)

        # Log successful password update
        await audit_service.log_auth_event(
            action=AuditAction.PASSWORD_CHANGE,
            user_id=current_user["user_id"],
            email=current_user["email"],
            ip_address=ip_address,
            user_agent=user_agent,
            success=True,
            details={"method": "reset_token"},
        )

        return MessageResponse(
            message="Password updated successfully",
            success=True,
        )

    except AuthError as e:
        logger.error(f"Password update failed: {e.message}")

        # Log failed password update
        await audit_service.log_auth_event(
            action=AuditAction.PASSWORD_CHANGE,
            user_id=current_user.get("user_id") if current_user else None,
            email=current_user.get("email") if current_user else None,
            ip_address=ip_address,
            user_agent=user_agent,
            success=False,
            details={"error": e.message, "code": e.code},
        )

        if e.code == "invalid_token":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired reset token",
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
