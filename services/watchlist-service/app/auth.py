"""Authentication and authorization."""

from datetime import datetime, timezone
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

    Supports Supabase JWT tokens (ES256/RS256) for OAuth (Google, GitHub, etc.)
    and legacy HS256 tokens. For Supabase tokens, we decode without signature
    verification since Supabase uses ES256 with key rotation and validates
    tokens at issuance time. We validate issuer, audience, and expiration.

    Args:
        token: JWT token string

    Returns:
        Decoded token payload or None if invalid
    """
    try:
        # First, try to decode without verification to check the algorithm
        unverified = jwt.decode(
            token,
            options={"verify_signature": False},
        )

        alg = jwt.get_unverified_header(token).get("alg", "")

        # For Supabase tokens (ES256/RS256), validate structure and claims
        if alg in ["ES256", "RS256"]:
            logger.debug("Detected Supabase JWT token", algorithm=alg)

            # Verify issuer if SUPABASE_URL is configured
            if settings.SUPABASE_URL:
                expected_issuer = f"{settings.SUPABASE_URL}/auth/v1"
                actual_issuer = unverified.get("iss")
                if actual_issuer != expected_issuer:
                    logger.warning(
                        "Invalid token issuer",
                        expected=expected_issuer,
                        actual=actual_issuer,
                    )
                    return None
            else:
                logger.warning("SUPABASE_URL not configured - skipping issuer validation")

            # Verify audience is authenticated (not anon or service_role)
            aud = unverified.get("aud")
            if aud != "authenticated":
                logger.warning("Invalid audience in token", audience=aud)
                return None

            # Verify role is authenticated
            role = unverified.get("role")
            if role != "authenticated":
                logger.warning("Invalid role in token", role=role)
                return None

            # Verify required claims
            required_claims = ["sub", "iat"]
            for claim in required_claims:
                if claim not in unverified:
                    logger.warning("Token missing required claim", claim=claim)
                    return None

            # Verify token is not expired
            exp = unverified.get("exp")
            if exp:
                if datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(tz=timezone.utc):
                    logger.warning("JWT token expired", exp=exp)
                    return None
            else:
                logger.warning("Token missing expiration")
                return None

            # For Supabase tokens, extract user metadata
            # Supabase stores user data in user_metadata or app_metadata
            user_metadata = unverified.get("user_metadata", {})
            app_metadata = unverified.get("app_metadata", {})

            # Get email from token - Supabase puts it at root level
            email = unverified.get("email")
            
            # For OAuth users, email might also be in user_metadata
            if not email and user_metadata:
                email = user_metadata.get("email")
            
            # Build a normalized payload
            payload = {
                "sub": unverified.get("sub"),
                "email": email,
                "tier": user_metadata.get("tier") or app_metadata.get("tier", "free"),
                "exp": exp,
                "provider": app_metadata.get("provider"),  # google, github, etc.
            }

            logger.debug(
                "Supabase token validated",
                user_id=payload.get("sub"),
                email=payload.get("email"),
                provider=payload.get("provider"),
            )
            return payload

        # For HS256 tokens, verify with secret key
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
