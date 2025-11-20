"""
Authentication and authorization for search service.

Integrates with Supabase JWT authentication and implements tier-based access control.
"""

import os
from typing import Optional

import httpx
import structlog
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

logger = structlog.get_logger(__name__)
security = HTTPBearer(auto_error=False)


class User:
    """
    User model for authenticated requests.

    Attributes:
        id: User UUID from Supabase
        email: User email address
        tier: Subscription tier (anonymous, free, paid)
        is_authenticated: Whether user is authenticated
    """

    def __init__(self, id: str, email: str, tier: str):
        self.id = id
        self.email = email
        self.tier = tier
        self.is_authenticated = True

    def __repr__(self) -> str:
        return f"User(id={self.id}, email={self.email}, tier={self.tier})"


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[User]:
    """
    Validate JWT token with Supabase and return user.

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
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_anon_key = os.getenv("SUPABASE_ANON_KEY")

    if not supabase_url:
        logger.error("SUPABASE_URL not configured")
        return None

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Validate token with Supabase auth
            auth_response = await client.get(
                f"{supabase_url}/auth/v1/user",
                headers={"Authorization": f"Bearer {token}"},
            )

            if auth_response.status_code != 200:
                logger.warning(
                    "Token validation failed", status_code=auth_response.status_code
                )
                return None

            user_data = auth_response.json()
            user_id = user_data.get("id")
            email = user_data.get("email")

            if not user_id or not email:
                logger.warning("Invalid user data from Supabase")
                return None

            # Fetch user tier from user_profiles table
            tier = "free"  # Default tier

            if supabase_anon_key:
                try:
                    tier_response = await client.get(
                        f"{supabase_url}/rest/v1/user_profiles",
                        params={"user_id": f"eq.{user_id}", "select": "tier"},
                        headers={
                            "Authorization": f"Bearer {token}",
                            "apikey": supabase_anon_key,
                        },
                    )

                    if tier_response.status_code == 200:
                        profiles = tier_response.json()
                        if profiles and len(profiles) > 0:
                            tier = profiles[0].get("tier", "free")
                            logger.debug(
                                "User tier fetched", user_id=user_id, tier=tier
                            )
                except Exception as e:
                    logger.warning(
                        "Failed to fetch user tier, using default", error=str(e)
                    )

            user = User(id=user_id, email=email, tier=tier)
            logger.info("User authenticated", user_id=user_id, tier=tier)

            return user

    except httpx.TimeoutException:
        logger.error("Supabase authentication timeout")
        return None
    except Exception as e:
        logger.error("Authentication error", error=str(e), error_type=type(e).__name__)
        return None


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
    Raises 403 if user is not on paid tier.

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
    if user.tier != "paid":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This feature requires a paid subscription. Upgrade at /upgrade",
        )
    return user
