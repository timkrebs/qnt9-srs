"""
Authentication and authorization for search service.

Validates JWT tokens from auth-service and implements tier-based access control.
"""

import os
from typing import Optional

import jwt
import structlog
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

logger = structlog.get_logger(__name__)
security = HTTPBearer(auto_error=False)

# JWT Configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"


class User:
    """
    User model for authenticated requests.

    Attributes:
        id: User UUID from auth-service
        email: User email address
        tier: Subscription tier (anonymous, free, paid, enterprise)
        is_authenticated: Whether user is authenticated
    """

    def __init__(self, id: str, email: str, tier: str):
        self.id = id
        self.email = email
        self.tier = tier
        self.is_authenticated = True

    def __repr__(self) -> str:
        return f"User(id={self.id}, email={self.email}, tier={self.tier})"


def decode_jwt_token(token: str) -> Optional[dict]:
    """
    Decode and validate a JWT token.

    Args:
        token: JWT token string

    Returns:
        Decoded payload if valid, None otherwise
    """
    try:
        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
        )

        # Verify it's an access token
        if payload.get("type") != "access":
            logger.warning("Invalid token type", token_type=payload.get("type"))
            return None

        return payload

    except jwt.ExpiredSignatureError:
        logger.warning("Token has expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning("Invalid token", error=str(e))
        return None
    except Exception as e:
        logger.error("Token decode error", error=str(e), error_type=type(e).__name__)
        return None


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[User]:
    """
    Validate JWT token and return user.

    Returns None for unauthenticated requests (allows anonymous access).
    This enables optional authentication where endpoints can work with or without auth.

    Args:
        credentials: HTTP Bearer token from Authorization header

    Returns:
        User object if authenticated, None if not authenticated

    Example:
        @router.get("/search")
        async def search(user: User | None = Depends(get_current_user)):
            tier = user.tier if user else "anonymous"
            # ... handle request based on tier
    """
    if not credentials:
        logger.debug("No credentials provided - anonymous access")
        return None

    token = credentials.credentials

    # Decode and validate the JWT token
    payload = decode_jwt_token(token)

    if not payload:
        logger.warning("Token validation failed")
        return None

    user_id = payload.get("sub")
    email = payload.get("email")
    tier = payload.get("tier", "free")

    if not user_id or not email:
        logger.warning("Invalid token payload - missing user_id or email")
        return None

    user = User(id=user_id, email=email, tier=tier)
    logger.info("User authenticated", user_id=user_id, tier=tier)

    return user


async def require_authentication(
    user: Optional[User] = Depends(get_current_user),
) -> User:
    """
    Require authenticated user.

    Use this dependency when an endpoint requires authentication.
    Raises 401 if user is not authenticated.

    Args:
        user: User from get_current_user dependency

    Returns:
        Authenticated User object

    Raises:
        HTTPException: 401 if user is not authenticated

    Example:
        @router.get("/history")
        async def get_history(user: User = Depends(require_authentication)):
            # User is guaranteed to be authenticated here
            return await get_user_history(user.id)
    """
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please log in to access this feature.",
        )
    return user


async def require_paid_tier(user: User = Depends(require_authentication)) -> User:
    """
    Require paid subscription tier.

    Use this dependency when an endpoint requires paid subscription.
    Raises 403 if user is not on paid or enterprise tier.

    Args:
        user: Authenticated user from require_authentication

    Returns:
        User object with paid tier

    Raises:
        HTTPException: 403 if user is not on paid tier

    Example:
        @router.get("/premium-feature")
        async def premium_feature(user: User = Depends(require_paid_tier)):
            # User is guaranteed to be paid tier here
            return await get_premium_data()
    """
    if user.tier not in ("paid", "enterprise"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This feature requires a paid subscription. Upgrade at /upgrade",
        )
    return user
