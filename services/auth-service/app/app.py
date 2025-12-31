"""
Auth Service - Main FastAPI Application.

Provides authentication endpoints using PostgreSQL with JWT for secure user management.
Integrates with the QNT9 Stock Recommendation System.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware

from .auth_service import AuthError, auth_service
from .config import settings
from .database import db_manager
from .logging_config import get_logger, setup_logging
from .metrics import metrics_endpoint, track_request_metrics
from .metrics_middleware import PrometheusMiddleware
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
    UserTierResponse,
    UserTierUpdate,
    UserUpdate,
)
from .rate_limiter import check_auth_rate_limit, check_password_reset_rate_limit
from .security import decode_access_token
from .tracing import configure_opentelemetry, instrument_fastapi

# Setup logging
setup_logging(log_level=settings.LOG_LEVEL, service_name="auth-service")
logger = get_logger(__name__)

# Configure OpenTelemetry tracing
configure_opentelemetry(
    service_name="auth-service",
    service_version="3.0.0",
    enable_tracing=not settings.DEBUG,
)


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

    # Initialize database connection pool
    await db_manager.connect()
    logger.info("PostgreSQL connection pool initialized")

    yield

    # Shutdown
    logger.info("Shutting down Auth Service...")
    await db_manager.disconnect()
    logger.info("Database connection pool closed")


# Initialize FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="Authentication service using PostgreSQL with JWT for QNT9 SRS",
    version="3.0.0",
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

# Add Prometheus metrics middleware
app.add_middleware(PrometheusMiddleware, track_func=track_request_metrics)

# Instrument FastAPI with OpenTelemetry
instrument_fastapi(app, excluded_urls="/health,/metrics")


# Metrics endpoint
@app.get("/metrics", include_in_schema=False)
async def metrics():
    """Prometheus metrics endpoint."""
    return await metrics_endpoint()


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


async def get_current_user_from_token(authorization: str = Header(None)) -> dict:
    """
    Dependency that extracts and validates the current user from JWT token.

    Args:
        authorization: Bearer token in Authorization header

    Returns:
        Dictionary with user_id and email from token

    Raises:
        HTTPException: If token is invalid or expired
    """
    token = get_token_from_header(authorization)

    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    return {
        "user_id": payload["sub"],
        "email": payload["email"],
        "tier": payload.get("tier", "free"),
    }


# Health & Info Endpoints


@app.get("/")
async def root() -> dict:
    """Root endpoint with service information."""
    return {
        "service": "QNT9 Auth Service",
        "version": "3.0.0",
        "status": "active",
        "auth_provider": "PostgreSQL + JWT",
    }


@app.get("/health")
async def health_check() -> dict:
    """Health check endpoint."""
    # Check database connectivity
    db_healthy = False
    try:
        result = await db_manager.fetchval("SELECT 1")
        db_healthy = result == 1
    except Exception as e:
        logger.error(f"Database health check failed: {e}")

    return {
        "status": "healthy" if db_healthy else "degraded",
        "service": "auth-service",
        "database": "connected" if db_healthy else "disconnected",
    }


# Authentication Endpoints


@app.post(
    "/auth/signup",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Authentication"],
    summary="Register new user",
    dependencies=[Depends(check_auth_rate_limit)],
)
async def sign_up(user_data: UserSignUp):
    """
    Register a new user with email and password.

    Creates a new user account and returns session tokens for immediate authentication.

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

    except AuthError as e:
        logger.error(f"Sign up failed: {e.message}")
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


@app.post(
    "/auth/signin",
    response_model=AuthResponse,
    tags=["Authentication"],
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

        return AuthResponse(
            user=UserResponse(**result["user"]),
            session=SessionResponse(**result["session"]),
        )

    except AuthError as e:
        logger.error(f"Sign in failed: {e.message}")
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


@app.post(
    "/auth/signout",
    response_model=MessageResponse,
    tags=["Authentication"],
    summary="Sign out user",
)
async def sign_out(token_data: RefreshToken):
    """
    Sign out the current user.

    Invalidates the user's refresh token.

    Args:
        token_data: Refresh token to invalidate

    Returns:
        Success message

    Raises:
        HTTPException: If sign out fails
    """
    try:
        await auth_service.sign_out(token_data.refresh_token)

        return MessageResponse(
            message="Signed out successfully",
            success=True,
        )

    except AuthError as e:
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

    except AuthError as e:
        logger.error(f"Session refresh failed: {e.message}")
        if e.code in ("invalid_token", "token_revoked", "token_expired"):
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


# User Management Endpoints


@app.get(
    "/auth/me",
    response_model=UserResponse,
    tags=["User Management"],
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


@app.patch(
    "/auth/me",
    response_model=UserResponse,
    tags=["User Management"],
    summary="Update current user",
)
async def update_current_user(
    user_update: UserUpdate,
    current_user: dict = Depends(get_current_user_from_token),
):
    """
    Update current user's profile information.

    Requires a valid access token in the Authorization header.

    Args:
        user_update: Updated user data (email, full_name)
        current_user: Injected user data from token

    Returns:
        Updated user information

    Raises:
        HTTPException: If update fails
    """
    try:
        result = await auth_service.update_user(
            user_id=current_user["user_id"],
            email=user_update.email,
            full_name=user_update.full_name,
        )

        return UserResponse(**result)

    except AuthError as e:
        logger.error(f"User update failed: {e.message}")
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


@app.patch(
    "/auth/me/password",
    response_model=MessageResponse,
    tags=["User Management"],
    summary="Update password",
)
async def update_password(
    password_update: PasswordUpdate,
    current_user: dict = Depends(get_current_user_from_token),
):
    """
    Update current user's password.

    Requires a valid access token in the Authorization header.

    Args:
        password_update: New password
        current_user: Injected user data from token

    Returns:
        Success message

    Raises:
        HTTPException: If password update fails
    """
    try:
        await auth_service.update_user(
            user_id=current_user["user_id"],
            password=password_update.password,
        )

        return MessageResponse(
            message="Password updated successfully",
            success=True,
        )

    except AuthError as e:
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
    dependencies=[Depends(check_password_reset_rate_limit)],
)
async def request_password_reset(reset_request: PasswordResetRequest):
    """
    Request a password reset email.

    Sends a password reset link to the user's email address.

    Args:
        reset_request: Email address for password reset

    Returns:
        Success message (always returns success for security)

    Raises:
        HTTPException: If request fails
    """
    try:
        await auth_service.reset_password_request(reset_request.email)

        return MessageResponse(
            message="If the email exists, a password reset link has been sent.",
            success=True,
        )

    except Exception as e:
        logger.exception(f"Unexpected error requesting password reset: {e}")
        # Don't reveal errors for security
        return MessageResponse(
            message="If the email exists, a password reset link has been sent.",
            success=True,
        )


@app.get(
    "/auth/me/tier",
    response_model=UserTierResponse,
    tags=["User Management"],
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


@app.patch(
    "/auth/me/tier",
    response_model=UserTierResponse,
    tags=["User Management"],
    summary="Update user tier (upgrade/downgrade)",
)
async def update_user_tier(
    tier_update: UserTierUpdate,
    current_user: dict = Depends(get_current_user_from_token),
):
    """
    Update user's subscription tier.

    Requires a valid access token in the Authorization header.

    Args:
        tier_update: New tier information
        current_user: Injected user data from token

    Returns:
        Updated user tier information

    Raises:
        HTTPException: If token is invalid or tier update fails
    """
    try:
        updated_tier = await auth_service.update_user_tier(
            current_user["user_id"],
            tier_update.tier,
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
