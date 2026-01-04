"""
Supabase JWT Authentication Helper.

Provides utilities to validate Supabase JWT tokens in backend services.
Supabase uses JWT tokens signed with their project's JWT secret.
"""

import os
from typing import Optional

import jwt
from fastapi import Header, HTTPException, status
from pydantic import BaseModel


class SupabaseUser(BaseModel):
    """Supabase user information from JWT token."""

    id: str
    email: str
    role: str = "authenticated"
    aud: str = "authenticated"


def get_supabase_jwt_secret() -> str:
    """
    Get Supabase JWT secret from environment.

    This should be the JWT_SECRET from your Supabase project settings.
    Not the anon key or service role key, but the actual JWT secret.
    """
    secret = os.getenv("SUPABASE_JWT_SECRET")
    if not secret:
        raise ValueError("SUPABASE_JWT_SECRET environment variable is required")
    return secret


def decode_supabase_token(token: str) -> SupabaseUser:
    """
    Decode and validate a Supabase JWT token.

    Args:
        token: The JWT token string from Authorization header

    Returns:
        SupabaseUser object with user information

    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        secret = get_supabase_jwt_secret()

        payload = jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            audience="authenticated",  # Supabase default audience
        )

        return SupabaseUser(
            id=payload.get("sub"),
            email=payload.get("email"),
            role=payload.get("role", "authenticated"),
            aud=payload.get("aud", "authenticated"),
        )

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(authorization: Optional[str] = Header(None)) -> SupabaseUser:
    """
    FastAPI dependency to get current authenticated user from Supabase JWT.

    Usage:
        @app.get("/protected")
        async def protected_route(user: SupabaseUser = Depends(get_current_user)):
            return {"user_id": user.id, "email": user.email}

    Args:
        authorization: Authorization header containing "Bearer <token>"

    Returns:
        SupabaseUser object with user information

    Raises:
        HTTPException: If authorization header is missing or token is invalid
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format. Expected 'Bearer <token>'",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization.split(" ")[1]
    return decode_supabase_token(token)
