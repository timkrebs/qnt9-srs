"""
Security utilities for authentication.

Provides password hashing, JWT token generation and validation.
"""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

import bcrypt
import jwt
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError

from .config import settings
from .logging_config import get_logger

logger = get_logger(__name__)


# ==================== PASSWORD HASHING ====================


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.

    Args:
        password: Plain text password

    Returns:
        Hashed password string
    """
    salt = bcrypt.gensalt(rounds=settings.PASSWORD_HASH_ROUNDS)
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.

    Args:
        password: Plain text password to verify
        hashed_password: Stored hash to verify against

    Returns:
        True if password matches, False otherwise
    """
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception as e:
        logger.error(f"Password verification failed: {e}")
        return False


# ==================== TOKEN GENERATION ====================


def generate_token(length: int = 32) -> str:
    """
    Generate a cryptographically secure random token.

    Args:
        length: Length of the token in bytes (actual string will be longer)

    Returns:
        URL-safe random token string
    """
    return secrets.token_urlsafe(length)


def hash_token(token: str) -> str:
    """
    Hash a token for secure storage.

    Uses SHA-256 for fast lookups while still being secure.

    Args:
        token: Token to hash

    Returns:
        Hashed token string
    """
    import hashlib

    return hashlib.sha256(token.encode()).hexdigest()


# ==================== JWT TOKENS ====================


def create_access_token(
    user_id: str,
    email: str,
    tier: str = "free",
    additional_claims: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Create a JWT access token.

    Args:
        user_id: User's UUID
        email: User's email
        tier: User's subscription tier
        additional_claims: Optional additional claims to include

    Returns:
        Encoded JWT access token
    """
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    payload = {
        "sub": user_id,
        "email": email,
        "tier": tier,
        "type": "access",
        "iat": now,
        "exp": expire,
    }

    if additional_claims:
        payload.update(additional_claims)

    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    logger.debug(f"Created access token for user {user_id}, expires at {expire}")
    return token


def create_refresh_token(user_id: str) -> Tuple[str, str, datetime]:
    """
    Create a refresh token.

    Args:
        user_id: User's UUID

    Returns:
        Tuple of (raw_token, hashed_token, expires_at)
    """
    raw_token = generate_token(48)
    hashed = hash_token(raw_token)
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    logger.debug(f"Created refresh token for user {user_id}, expires at {expires_at}")
    return raw_token, hashed, expires_at


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode and validate a JWT access token.

    Args:
        token: JWT token string

    Returns:
        Decoded payload if valid, None otherwise
    """
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])

        # Verify token type
        if payload.get("type") != "access":
            logger.warning("Invalid token type")
            return None

        return payload

    except ExpiredSignatureError:
        logger.debug("Access token expired")
        return None
    except InvalidTokenError as e:
        logger.warning(f"Invalid access token: {e}")
        return None


def create_password_reset_token() -> Tuple[str, str, datetime]:
    """
    Create a password reset token.

    Returns:
        Tuple of (raw_token, hashed_token, expires_at)
    """
    raw_token = generate_token(32)
    hashed = hash_token(raw_token)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)  # 1 hour validity

    return raw_token, hashed, expires_at


def create_email_verification_token() -> Tuple[str, str, datetime]:
    """
    Create an email verification token.

    Returns:
        Tuple of (raw_token, hashed_token, expires_at)
    """
    raw_token = generate_token(32)
    hashed = hash_token(raw_token)
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)  # 7 days validity

    return raw_token, hashed, expires_at


def get_token_from_header(authorization: Optional[str]) -> Optional[str]:
    """
    Extract Bearer token from Authorization header.

    Args:
        authorization: Authorization header value

    Returns:
        Token string if valid Bearer format, None otherwise
    """
    if not authorization:
        return None

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None

    return parts[1]
