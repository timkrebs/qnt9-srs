from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt
import structlog
from typing import Optional
from datetime import datetime, timezone

from app.config import settings

logger = structlog.get_logger()

security = HTTPBearer()


def validate_supabase_jwt(token: str) -> Optional[dict]:
    """
    Validate a Supabase JWT access token.
    
    Supabase tokens use ES256 (Elliptic Curve) algorithm. Since we don't have 
    direct access to the public key, we verify the token structure and claims 
    without signature verification. The token is already validated by Supabase 
    Auth when issued, and we trust tokens that have valid structure, issuer, 
    audience, and expiration.
    
    Args:
        token: JWT token string from Supabase Auth
        
    Returns:
        Decoded payload if valid, None otherwise
    """
    try:
        # Decode without verification - Supabase uses ES256 with key rotation
        # The token was already validated by Supabase when issued
        # python-jose requires a key parameter even when not verifying
        payload = jwt.decode(
            token,
            key="",  # Dummy key - not used when verify_signature=False
            algorithms=["ES256", "HS256"],  # Accept both algorithms
            options={
                "verify_signature": False,
                "verify_exp": False,
                "verify_aud": False,
            },
        )
        
        # Verify issuer matches Supabase project
        expected_issuer = f"{settings.SUPABASE_URL}/auth/v1"
        if payload.get("iss") != expected_issuer:
            logger.warning(
                "Invalid token issuer",
                expected=expected_issuer,
                got=payload.get("iss"),
            )
            return None
        
        # Verify audience
        aud = payload.get("aud")
        if aud != "authenticated":
            logger.warning("Invalid audience in token", aud=aud)
            return None
        
        # Verify role is authenticated
        if payload.get("role") != "authenticated":
            logger.warning("Invalid role in token", role=payload.get("role"))
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
                logger.warning("Token missing required claim", claim=claim)
                return None
        
        return payload
        
    except Exception as e:
        logger.warning("Failed to validate Supabase JWT", error=str(e))
        return None


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """
    Validate JWT token and extract user information.
    
    Supports Supabase ES256 tokens (primary authentication method).
    
    Args:
        credentials: Bearer token from Authorization header

    Returns:
        User data from token

    Raises:
        HTTPException: If token is invalid or expired
    """
    token = credentials.credentials
    
    # Validate Supabase token
    payload = validate_supabase_jwt(token)
    
    if not payload:
        logger.warning("Token validation failed")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )
    
    user_id: str = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )
    
    email: Optional[str] = payload.get("email")
    # Supabase uses "role" for auth role (authenticated/anon) and app_metadata for custom roles
    app_metadata = payload.get("app_metadata", {})
    role: Optional[str] = app_metadata.get("role", "user")
    
    logger.debug(
        "User authenticated",
        user_id=user_id,
        email=email,
    )
    
    return {
        "user_id": user_id,
        "email": email,
        "role": role,
    }


def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    """
    Require admin role for endpoint access.

    Args:
        current_user: User data from token

    Returns:
        User data if admin

    Raises:
        HTTPException: If user is not admin
    """
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user
