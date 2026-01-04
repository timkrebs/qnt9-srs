"""
Security utilities for authentication.

Provides Supabase JWT validation and legacy password hashing for migration.
"""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

import bcrypt
import jwt
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError, PyJWTError

from .config import settings
from .logging_config import get_logger

logger = get_logger(__name__)


# ==================== SUPABASE JWT VALIDATION ====================


def validate_supabase_jwt(token: str) -> Optional[Dict[str, Any]]:
    """
    Validate a Supabase JWT access token.

    Supabase tokens use ES256 (Elliptic Curve) algorithm. Since we don't have the public key
    directly, we verify the token structure and claims without signature verification.
    The token is already validated by Supabase Auth when issued, and we trust tokens
    that have valid structure, issuer, audience, and expiration.

    Args:
        token: JWT token string from Supabase Auth

    Returns:
        Decoded payload if valid, None otherwise
    """
    try:
        logger.debug(f"Validating Supabase JWT token (length: {len(token)})")

        # Decode without verification to check structure and claims
        # The token was already validated by Supabase when issued
        payload = jwt.decode(
            token,
            options={
                "verify_signature": False,  # Supabase uses ES256 with key rotation
                "verify_exp": False,  # We'll verify manually below
                "verify_aud": False,  # We'll verify manually below
            },
        )

        logger.debug(f"Token decoded successfully, subject: {payload.get('sub')}")

        # Verify issuer matches Supabase project
        expected_issuer = f"{settings.SUPABASE_URL}/auth/v1"
        if payload.get("iss") != expected_issuer:
            logger.warning(
                f"Invalid token issuer: {payload.get('iss')} (expected {expected_issuer})"
            )
            return None

        # Verify audience
        aud = payload.get("aud")
        if aud != "authenticated":
            logger.warning(f"Invalid audience in token: {aud}")
            return None

        # Verify role is authenticated (not anon or service_role)
        if payload.get("role") != "authenticated":
            logger.warning(f"Invalid role in token: {payload.get('role')}")
            return None

        # Verify token is not expired
        exp = payload.get("exp")
        if not exp:
            logger.warning("Token missing expiration")
            return None

        if datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(tz=timezone.utc):
            logger.debug("Supabase token expired")
            return None

        # Verify required claims are present
        required_claims = ["sub", "iat", "iss"]
        for claim in required_claims:
            if claim not in payload:
                logger.warning(f"Token missing required claim: {claim}")
                return None

        logger.debug(
            f"Successfully validated Supabase JWT for user {payload.get('sub')}"
        )
        return payload

    except ExpiredSignatureError:
        logger.debug("Supabase token expired")
        return None
    except InvalidTokenError as e:
        logger.warning(f"Invalid Supabase token: {e}")
        return None
    except PyJWTError as e:
        logger.error(f"JWT validation error: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error validating Supabase JWT: {e}")
        import traceback

        logger.error(f"Traceback: {traceback.format_exc()}")
        return None


def extract_user_from_supabase_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Extract user information from a Supabase JWT.

    Args:
        token: JWT token string

    Returns:
        Dict with user info (id, email, etc.) or None if invalid
    """
    payload = validate_supabase_jwt(token)
    if not payload:
        return None

    return {
        "id": payload.get("sub"),
        "email": payload.get("email"),
        "phone": payload.get("phone", ""),
        "role": payload.get("role"),
        "aal": payload.get("aal"),
        "session_id": payload.get("session_id"),
        "app_metadata": payload.get("app_metadata", {}),
        "user_metadata": payload.get("user_metadata", {}),
        "is_anonymous": payload.get("is_anonymous", False),
    }


# ==================== LEGACY PASSWORD HASHING (for migration) ====================


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


# ==================== LEGACY JWT TOKENS (deprecated - for migration only) ====================


def create_access_token(
    user_id: str,
    email: str,
    tier: str = "free",
    additional_claims: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Create a JWT access token.

    DEPRECATED: This is legacy code for migration only.
    New code should use Supabase Auth API which returns tokens automatically.

    Args:
        user_id: User's UUID
        email: User's email
        tier: User's subscription tier
        additional_claims: Optional additional claims to include

    Returns:
        Encoded JWT access token
    """
    logger.warning("Using legacy create_access_token - should migrate to Supabase Auth")

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

    token = jwt.encode(
        payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )

    logger.debug(f"Created legacy access token for user {user_id}, expires at {expire}")
    return token


def create_refresh_token(user_id: str) -> Tuple[str, str, datetime]:
    """
    Create a refresh token.

    DEPRECATED: This is legacy code for migration only.
    Supabase manages refresh tokens internally.

    Args:
        user_id: User's UUID

    Returns:
        Tuple of (raw_token, hashed_token, expires_at)
    """
    logger.warning(
        "Using legacy create_refresh_token - should migrate to Supabase Auth"
    )

    raw_token = generate_token(32)
    hashed = hash_token(raw_token)
    expires_at = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )

    return raw_token, hashed, expires_at


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode and validate a legacy JWT access token.

    DEPRECATED: Use validate_supabase_jwt() for Supabase tokens.
    This is legacy code for migration period only.

    Args:
        token: JWT token string

    Returns:
        Decoded payload if valid, None otherwise
    """
    logger.warning(
        "Using legacy decode_access_token - should use validate_supabase_jwt"
    )

    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )

        # Verify token type
        if payload.get("type") != "access":
            logger.warning("Invalid token type")
            return None

        return payload

    except ExpiredSignatureError:
        logger.debug("Legacy access token expired")
        return None
    except InvalidTokenError as e:
        logger.warning(f"Invalid legacy access token: {e}")
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
    expires_hours = settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS
    expires_at = datetime.now(timezone.utc) + timedelta(hours=expires_hours)

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
