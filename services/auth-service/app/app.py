"""
Auth Service - Main FastAPI Application.

Provides authentication endpoints using Supabase Auth for secure user management.
Integrates with the QNT9 Stock Recommendation System.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from gotrue.errors import AuthApiError

from .auth_service import auth_service
from .config import settings
from .logging_config import get_logger, setup_logging
from .models import (
    AuthResponse,
    MessageResponse,
    PasswordResetRequest,
    PasswordUpdate,
    RefreshToken,
    SessionResponse,
    UserResponse,
    UserSignIn,
    UserSignUp,
    UserUpdate,
)

# Setup logging
setup_logging(log_level=settings.LOG_LEVEL, service_name="auth-service")
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan context manager.

    Handles startup and shutdown events for the application.
    """
    # Startup
    logger.info("Starting Auth Service...")
    logger.info(f"Service: {settings.APP_NAME}")
    logger.info(f"Debug mode: {settings.DEBUG}")
    logger.info(f"Log level: {settings.LOG_LEVEL}")
    logger.info("Supabase Auth integration active")

    yield

    # Shutdown
    logger.info("Shutting down Auth Service...")


# Initialize FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="Authentication service using Supabase for QNT9 SRS",
    version="2.0.0",
    docs_url="/api/docs" if settings.DEBUG else None,
    redoc_url="/api/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Helper Functions


def get_token_from_header(authorization: str = Header(None)) -> str:
    """
    Extract Bearer token from Authorization header.

    Args:
        authorization: Authorization header value

    Returns:
        JWT access token

    Raises:
        HTTPException: If authorization header is missing or invalid
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing",
        )

    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise ValueError("Invalid authentication scheme")
        return token
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format. Use: Bearer <token>",
        )


# Health & Info Endpoints


@app.get("/")
async def root() -> dict:
    """Root endpoint with service information."""
    return {
        "service": "QNT9 Auth Service",
        "version": "2.0.0",
        "status": "active",
        "auth_provider": "Supabase",
    }


@app.get("/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "auth-service",
    }


# Authentication Endpoints


@app.post(
    "/auth/signup",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Authentication"],
    summary="Register new user",
)
async def sign_up(user_data: UserSignUp):
    """
    Register a new user with email and password.

    Creates a new user account in Supabase Auth and returns
    session tokens for immediate authentication.

    Args:
        user_data: User registration data (email, password, full_name)

    Returns:
        User data and session tokens

    Raises:
        HTTPException: If registration fails
    """
    try:
        result = await auth_service.sign_up(
            email=user_data.email,
            password=user_data.password,
            full_name=user_data.full_name,
        )

        return AuthResponse(
            user=UserResponse(**result["user"]),
            session=SessionResponse(**result["session"]),
        )

    except AuthApiError as e:
        logger.error(f"Sign up failed: {e.message}")
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


@app.post(
    "/auth/signin",
    response_model=AuthResponse,
    tags=["Authentication"],
    summary="Sign in user",
)
async def sign_in(credentials: UserSignIn):
    """
    Sign in a user with email and password.

    Authenticates the user and returns session tokens.

    Args:
        credentials: User credentials (email, password)

    Returns:
        User data and session tokens

    Raises:
        HTTPException: If authentication fails
    """
    try:
        result = await auth_service.sign_in(
            email=credentials.email,
            password=credentials.password,
        )

        return AuthResponse(
            user=UserResponse(**result["user"]),
            session=SessionResponse(**result["session"]),
        )

    except AuthApiError as e:
        logger.error(f"Sign in failed: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    except Exception as e:
        logger.exception(f"Unexpected error during sign in: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during sign in",
        )


@app.post(
    "/auth/signout",
    response_model=MessageResponse,
    tags=["Authentication"],
    summary="Sign out user",
)
async def sign_out(authorization: str = Header(None)):
    """
    Sign out the current user.

    Invalidates the user's session tokens.

    Args:
        authorization: Bearer token in Authorization header

    Returns:
        Success message

    Raises:
        HTTPException: If sign out fails
    """
    try:
        token = get_token_from_header(authorization)
        await auth_service.sign_out(token)

        return MessageResponse(
            message="Signed out successfully",
            success=True,
        )

    except AuthApiError as e:
        logger.error(f"Sign out failed: {e.message}")
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


@app.post(
    "/auth/refresh",
    response_model=SessionResponse,
    tags=["Authentication"],
    summary="Refresh session",
)
async def refresh_session(token_data: RefreshToken):
    """
    Refresh an expired session.

    Uses a refresh token to obtain new access and refresh tokens.

    Args:
        token_data: Refresh token

    Returns:
        New session tokens

    Raises:
        HTTPException: If refresh fails
    """
    try:
        result = await auth_service.refresh_session(token_data.refresh_token)

        return SessionResponse(**result)

    except AuthApiError as e:
        logger.error(f"Session refresh failed: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )
    except Exception as e:
        logger.exception(f"Unexpected error refreshing session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during session refresh",
        )


# User Management Endpoints


@app.get(
    "/auth/me",
    response_model=UserResponse,
    tags=["User Management"],
    summary="Get current user",
)
async def get_current_user(authorization: str = Header(None)):
    """
    Get current authenticated user information.

    Requires a valid access token in the Authorization header.

    Args:
        authorization: Bearer token in Authorization header

    Returns:
        User information

    Raises:
        HTTPException: If token is invalid or user not found
    """
    try:
        token = get_token_from_header(authorization)
        user = await auth_service.get_user(token)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
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


@app.patch(
    "/auth/me",
    response_model=UserResponse,
    tags=["User Management"],
    summary="Update current user",
)
async def update_current_user(
    user_update: UserUpdate,
    authorization: str = Header(None),
):
    """
    Update current user's profile information.

    Requires a valid access token in the Authorization header.

    Args:
        user_update: Updated user data (email, full_name)
        authorization: Bearer token in Authorization header

    Returns:
        Updated user information

    Raises:
        HTTPException: If update fails
    """
    try:
        token = get_token_from_header(authorization)

        result = await auth_service.update_user(
            access_token=token,
            email=user_update.email,
            full_name=user_update.full_name,
        )

        return UserResponse(**result)

    except AuthApiError as e:
        logger.error(f"User update failed: {e.message}")
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


@app.patch(
    "/auth/me/password",
    response_model=MessageResponse,
    tags=["User Management"],
    summary="Update password",
)
async def update_password(
    password_update: PasswordUpdate,
    authorization: str = Header(None),
):
    """
    Update current user's password.

    Requires a valid access token in the Authorization header.

    Args:
        password_update: New password
        authorization: Bearer token in Authorization header

    Returns:
        Success message

    Raises:
        HTTPException: If password update fails
    """
    try:
        token = get_token_from_header(authorization)

        await auth_service.update_user(
            access_token=token,
            password=password_update.password,
        )

        return MessageResponse(
            message="Password updated successfully",
            success=True,
        )

    except AuthApiError as e:
        logger.error(f"Password update failed: {e.message}")
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


@app.post(
    "/auth/reset-password",
    response_model=MessageResponse,
    tags=["User Management"],
    summary="Request password reset",
)
async def request_password_reset(reset_request: PasswordResetRequest):
    """
    Request a password reset email.

    Sends a password reset link to the user's email address.

    Args:
        reset_request: Email address for password reset

    Returns:
        Success message

    Raises:
        HTTPException: If request fails
    """
    try:
        await auth_service.reset_password_request(reset_request.email)

        return MessageResponse(
            message="Password reset email sent. Please check your inbox.",
            success=True,
        )

    except AuthApiError as e:
        logger.error(f"Password reset request failed: {e.message}")
        # Don't reveal if email exists for security
        return MessageResponse(
            message="If the email exists, a password reset link has been sent.",
            success=True,
        )
    except Exception as e:
        logger.exception(f"Unexpected error requesting password reset: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        )
