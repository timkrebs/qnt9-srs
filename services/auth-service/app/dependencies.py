"""
Dependency functions for the auth service.

Provides JWT validation and user extraction using Supabase tokens.
"""

from typing import Any, Dict

from fastapi import Header, HTTPException, status

from .security import extract_user_from_supabase_token


def get_token_from_header(authorization: str | None) -> str:
    """
    Extract JWT token from Authorization header.

    Args:
        authorization: Authorization header value

    Returns:
        JWT token string

    Raises:
        HTTPException: If authorization header is missing or malformed
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format. Use: Bearer <token>",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return parts[1]


async def get_current_user_from_token(authorization: str = Header(None)) -> Dict[str, Any]:
    """
    Dependency that extracts and validates the current user from Supabase JWT token.

    This validates the token signature, expiration, and issuer using the Supabase JWT secret.
    It ensures the token is from an authenticated user (not anon or service role).

    Args:
        authorization: Bearer token in Authorization header

    Returns:
        Dictionary with user information from Supabase token

    Raises:
        HTTPException: If token is invalid, expired, or not from Supabase Auth
    """
    token = get_token_from_header(authorization)

    user_info = extract_user_from_supabase_token(token)
    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {
        "user_id": user_info["id"],
        "email": user_info["email"],
        "phone": user_info.get("phone", ""),
        "role": user_info.get("role", "authenticated"),
        "session_id": user_info.get("session_id"),
        "is_anonymous": user_info.get("is_anonymous", False),
        "user_metadata": user_info.get("user_metadata", {}),
        "app_metadata": user_info.get("app_metadata", {}),
    }


async def get_current_user_id(current_user: Dict[str, Any] = Header(alias="authorization")) -> str:
    """
    Simplified dependency that returns only the user ID.

    Args:
        current_user: Current user from get_current_user_from_token

    Returns:
        User ID string
    """
    user = await get_current_user_from_token(current_user)
    return user["user_id"]


__all__ = ["get_current_user_from_token", "get_current_user_id", "get_token_from_header"]
