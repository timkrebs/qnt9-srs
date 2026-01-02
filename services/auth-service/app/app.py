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
from .dependencies import get_current_user_from_token
from .logging_config import get_logger, setup_logging
from .metrics import metrics_endpoint, track_request_metrics
from .metrics_middleware import PrometheusMiddleware
from .middleware import check_auth_rate_limit, check_password_reset_rate_limit
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
from .routers.v1 import auth_router, users_router
from .shutdown_handler import setup_graceful_shutdown
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

    # Setup graceful shutdown handlers
    shutdown_handler = setup_graceful_shutdown(
        service_name="auth-service", cleanup_callbacks=[db_manager.disconnect]
    )
    app.state.shutdown_handler = shutdown_handler
    app.state.is_shutting_down = False

    logger.info("Graceful shutdown handlers configured")

    yield

    # Shutdown
    logger.info("Shutting down Auth Service...")
    app.state.is_shutting_down = True
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

# Add CORS middleware with restricted permissions
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=[
        "Content-Type",
        "Authorization",
        "Accept",
        "Origin",
        "X-Requested-With",
    ],
    expose_headers=["Content-Length", "X-Request-ID"],
    max_age=600,
)

# Add Prometheus metrics middleware
app.add_middleware(PrometheusMiddleware, track_func=track_request_metrics)

# Instrument FastAPI with OpenTelemetry
instrument_fastapi(app, excluded_urls="/health,/metrics")


# Include API v1 routers
app.include_router(auth_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")


# Middleware to handle shutdown state
@app.middleware("http")
async def shutdown_middleware(request: Request, call_next):
    """
    Reject new requests during graceful shutdown.

    Returns 503 Service Unavailable if service is shutting down.
    """
    if hasattr(request.app.state, "is_shutting_down") and request.app.state.is_shutting_down:
        # Allow health checks during shutdown for monitoring
        if request.url.path in ["/health", "/metrics"]:
            return await call_next(request)

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service is shutting down",
        )

    return await call_next(request)


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


# get_current_user_from_token is imported from dependencies module
# The duplicate definition has been removed to fix F811 ruff error


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
    _ip_address = request.client.host if request.client else None
    _user_agent = request.headers.get("user-agent")

    try:
        result = await auth_service.sign_up(
            email=user_data.email,
            password=user_data.password,
            full_name=user_data.full_name,
        )

        # Log successful signup
        # TODO: Re-enable audit logging in later stage
        ## TODO: Re-enable audit logging in later stage
        # await audit_service.log_auth_event(
        # #     action=AuditAction.USER_SIGNUP,
        # #     user_id=result["user"]["id"],
        # #     email=user_data.email,
        # #     ip_address=ip_address,
        # #     user_agent=user_agent,
        # #     success=True,
        # #     details={"tier": result["user"]["tier"]},
        # # )

        return AuthResponse(
            user=UserResponse(**result["user"]),
            session=SessionResponse(**result["session"]),
        )

    except AuthError as e:
        logger.error(f"Sign up failed: {e.message}")

        # Log failed signup# TODO: Re-enable audit logging in later stage

        # await audit_service.log_auth_event(

        # action=AuditAction.USER_SIGNUP,

        # user_id=None,

        # email=user_data.email,

        # ip_address=ip_address,

        # user_agent=user_agent,

        # success=False,

        # details={"error": e.message},

        # )

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

        # Log successful signin
        # TODO: Re-enable audit logging in later stage
        ## TODO: Re-enable audit logging in later stage
        # await audit_service.log_auth_event(
        # #     action=AuditAction.USER_SIGNIN,
        # #     user_id=result["user"]["id"],
        # #     email=result["user"]["email"],
        # #     ip_address=client_ip,
        # #     user_agent=user_agent,
        # #     success=True,
        # #     details={"session_id": result["session"]["id"]},
        # # )

        return AuthResponse(
            user=UserResponse(**result["user"]),
            session=SessionResponse(**result["session"]),
        )

    except AuthError as e:
        logger.error(f"Sign in failed: {e.message}")

        # Log failed signin
        # TODO: Re-enable audit logging in later stage
        ## TODO: Re-enable audit logging in later stage
        # await audit_service.log_auth_event(
        # #     action=AuditAction.USER_SIGNIN_FAILED,
        # #     email=credentials.email,
        # #     ip_address=client_ip,
        # #     user_agent=user_agent,
        # #     success=False,
        # #     details={"error": e.message, "code": e.code},
        # # )

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
async def sign_out(token_data: RefreshToken, request: Request):
    """
    Sign out the current user.

    Invalidates the user's refresh token.

    Args:
        token_data: Refresh token to invalidate
        request: FastAPI request object for IP/user-agent capture

    Returns:
        Success message

    Raises:
        HTTPException: If sign out fails
    """
    try:
        # Capture client info for audit
        _ip_address = request.client.host if request.client else None
        _user_agent = request.headers.get("user-agent")

        await auth_service.sign_out(token_data.refresh_token)

        # Log successful signout (no user_id available from token)
        # TODO: Re-enable audit logging in later stage
        ## TODO: Re-enable audit logging in later stage
        # await audit_service.log_auth_event(
        # #     action=AuditAction.USER_SIGNOUT,
        # #     ip_address=ip_address,
        # #     user_agent=user_agent,
        # #     success=True,
        # #     details={"token_provided": True},
        # # )

        return MessageResponse(
            message="Signed out successfully",
            success=True,
        )

    except AuthError as e:
        logger.error(f"Sign out failed: {e.message}")

        # Log failed signout
        # TODO: Re-enable audit logging in later stage
        # # _ip_address = request.client.host if request.client else None
        # # _user_agent = request.headers.get("user-agent")
        ## TODO: Re-enable audit logging in later stage
        # await audit_service.log_auth_event(
        # #     action=AuditAction.USER_SIGNOUT,
        # #     ip_address=ip_address,
        # #     user_agent=user_agent,
        # #     success=False,
        # #     details={"error": e.message},
        # # )

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
        _ip_address = request.client.host if request.client else None
        _user_agent = request.headers.get("user-agent")

        result = await auth_service.refresh_session(token_data.refresh_token)

        # Log successful token refresh
        # TODO: Re-enable audit logging in later stage
        ## TODO: Re-enable audit logging in later stage
        # await audit_service.log_auth_event(
        # #     action=AuditAction.TOKEN_REFRESH,
        # #     ip_address=ip_address,
        # #     user_agent=user_agent,
        # #     success=True,
        # #     details={"new_session_id": result["id"]},
        # # )

        return SessionResponse(**result)

    except AuthError as e:
        logger.error(f"Session refresh failed: {e.message}")

        # Log failed token refresh
        # TODO: Re-enable audit logging in later stage
        # # _ip_address = request.client.host if request.client else None
        # # _user_agent = request.headers.get("user-agent")
        ## TODO: Re-enable audit logging in later stage
        # await audit_service.log_auth_event(
        # #     action=AuditAction.TOKEN_REFRESH,
        # #     ip_address=ip_address,
        # #     user_agent=user_agent,
        # #     success=False,
        # #     details={"error": e.message, "code": e.code},
        # # )

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
        _ip_address = request.client.host if request.client else None
        _user_agent = request.headers.get("user-agent")

        # Track changes for audit
        changes = {}
        if user_update.email and user_update.email != current_user.get("email"):
            changes["email"] = {"old": current_user.get("email"), "new": user_update.email}
        if user_update.full_name and user_update.full_name != current_user.get("full_name"):
            changes["full_name"] = {
                "old": current_user.get("full_name"),
                "new": user_update.full_name,
            }

        result = await auth_service.update_user(
            user_id=current_user["user_id"],
            email=user_update.email,
            full_name=user_update.full_name,
        )

        # Log user profile update
        # TODO: Re-enable audit logging in later stage
        # if changes:
        ## TODO: Re-enable audit logging in later stage
        # await audit_service.log_auth_event(
        # #         action=AuditAction.USER_UPDATE,
        # #         user_id=current_user["user_id"],
        # #         email=current_user.get("email"),
        #         ip_address=ip_address,
        #         user_agent=user_agent,
        #         success=True,
        #         details={"changes": changes},
        #     )

        return UserResponse(**result)

    except AuthError as e:
        logger.error(f"User update failed: {e.message}")

        # Log failed user update
        # TODO: Re-enable audit logging in later stage
        # # _ip_address = request.client.host if request.client else None
        # # _user_agent = request.headers.get("user-agent")
        ## TODO: Re-enable audit logging in later stage
        # await audit_service.log_auth_event(
        # #     action=AuditAction.USER_UPDATE,
        # #     user_id=current_user["user_id"],
        # #     email=current_user.get("email"),
        #     ip_address=ip_address,
        #     user_agent=user_agent,
        #     success=False,
        #     details={"error": e.message},
        # )

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
        _ip_address = request.client.host if request.client else None
        _user_agent = request.headers.get("user-agent")

        await auth_service.update_user(
            user_id=current_user["user_id"],
            password=password_update.password,
        )

        # Log successful password change
        # TODO: Re-enable audit logging in later stage
        ## TODO: Re-enable audit logging in later stage
        # await audit_service.log_auth_event(
        # #     action=AuditAction.PASSWORD_CHANGE,
        # #     user_id=current_user["user_id"],
        # #     email=current_user.get("email"),
        #     ip_address=ip_address,
        #     user_agent=user_agent,
        #     success=True,
        #     details={"initiated_by": "user"},
        # )

        return MessageResponse(
            message="Password updated successfully",
            success=True,
        )

    except AuthError as e:
        logger.error(f"Password update failed: {e.message}")

        # Log failed password change
        # TODO: Re-enable audit logging in later stage
        # # _ip_address = request.client.host if request.client else None
        # # _user_agent = request.headers.get("user-agent")
        ## TODO: Re-enable audit logging in later stage
        # await audit_service.log_auth_event(
        # #     action=AuditAction.PASSWORD_CHANGE,
        # #     user_id=current_user["user_id"],
        # #     email=current_user.get("email"),
        #     ip_address=ip_address,
        #     user_agent=user_agent,
        #     success=False,
        #     details={"error": e.message},
        # )

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
        _ip_address = request.client.host if request.client else None
        _user_agent = request.headers.get("user-agent")

        await auth_service.reset_password_request(reset_request.email)

        # Log password reset request
        # TODO: Re-enable audit logging in later stage
        ## TODO: Re-enable audit logging in later stage
        # await audit_service.log_auth_event(
        # #     action=AuditAction.PASSWORD_RESET_REQUEST,
        # #     email=reset_request.email,
        # #     ip_address=ip_address,
        # #     user_agent=user_agent,
        # #     success=True,
        # #     details={"email_sent": True},
        # # )

        return MessageResponse(
            message="If the email exists, a password reset link has been sent.",
            success=True,
        )

    except Exception as e:
        logger.exception(f"Unexpected error requesting password reset: {e}")

        # Log failed password reset request
        # TODO: Re-enable audit logging in later stage
        # # _ip_address = request.client.host if request.client else None
        # # _user_agent = request.headers.get("user-agent")
        ## TODO: Re-enable audit logging in later stage
        # await audit_service.log_auth_event(
        # #     action=AuditAction.PASSWORD_RESET_REQUEST,
        # #     email=reset_request.email,
        # #     ip_address=ip_address,
        # #     user_agent=user_agent,
        # #     success=False,
        # #     details={"error": str(e)},
        # )

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
        _ip_address = request.client.host if request.client else None
        _user_agent = request.headers.get("user-agent")

        # Get old tier for audit
        _old_tier = current_user.get("tier", "unknown")

        updated_tier = await auth_service.update_user_tier(
            current_user["user_id"],
            tier_update.tier,
        )

        # Log tier update
        # TODO: Re-enable audit logging in later stage
        # await audit_service.log_data_change(
        #     action=AuditAction.TIER_UPDATE,
        #     user_id=current_user["user_id"],
        #     email=current_user.get("email"),
        #     ip_address=ip_address,
        #     user_agent=user_agent,
        #     old_value=old_tier,
        #     new_value=tier_update.tier,
        #     details={
        #         "subscription_start": str(updated_tier.get("subscription_start")),
        #         "subscription_end": str(updated_tier.get("subscription_end")),
        #     },
        # )

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
        # TODO: Re-enable audit logging in later stage
        # # _ip_address = request.client.host if request.client else None
        # # _user_agent = request.headers.get("user-agent")
        ## TODO: Re-enable audit logging in later stage
        # await audit_service.log_auth_event(
        # #     action=AuditAction.TIER_UPDATE,
        # #     user_id=current_user["user_id"],
        # #     email=current_user.get("email"),
        #     ip_address=ip_address,
        #     user_agent=user_agent,
        #     success=False,
        #     details={"error": e.message, "attempted_tier": tier_update.tier},
        # )

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
