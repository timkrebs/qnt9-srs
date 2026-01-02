"""Authentication and authorization."""

from typing import Optional

import jwt
import structlog
from app.config import settings
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

logger = structlog.get_logger(__name__)
security = HTTPBearer()


class User:
    """User model from JWT token."""

    def __init__(self, id: str, email: str, tier: str):
        self.id = id
        self.email = email
        self.tier = tier

    def __repr__(self):
        return f"User(id={self.id}, email={self.email}, tier={self.tier})"


def decode_jwt_token(token: str) -> Optional[dict]:
    """
    Decode and validate JWT token.

    Args:
        token: JWT token string

    Returns:
        Decoded token payload or None if invalid
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("JWT token expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning("Invalid JWT token", error=str(e))
        return None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> User:
    """
    Get current authenticated user from JWT token.

    Args:
        credentials: HTTP Bearer token from Authorization header

    Returns:
        User object

    Raises:
        HTTPException: 401 if token is invalid or missing
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
        )

    token = credentials.credentials
    payload = decode_jwt_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    # Support both "sub" and "user_id" for compatibility
    user_id = payload.get("sub") or payload.get("user_id")
    email = payload.get("email")
    tier = payload.get("tier", "free")

    logger.debug(
        "JWT token decoded",
        has_sub=bool(payload.get("sub")),
        has_user_id=bool(payload.get("user_id")),
        user_id_extracted=user_id,
        email=email,
        tier=tier,
    )

    if not user_id or not email:
        logger.error(
            "Invalid token payload - missing required fields",
            has_user_id=bool(user_id),
            has_email=bool(email),
            payload_keys=list(payload.keys()),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload - missing user ID or email",
        )

    user = User(id=user_id, email=email, tier=tier)
    logger.info(
        "User authenticated successfully",
        user_id=user.id,
        user_email=user.email,
        tier=user.tier,
    )

    return user
