"""
Authentication service using Supabase Auth.

Provides business logic for user authentication, registration,
and profile management using Supabase Auth API.
"""

from datetime import datetime
from typing import Any, Dict, Optional

from gotrue.errors import AuthApiError
from supabase import Client as SupabaseClient

from .config import settings
from .database import db_manager, get_supabase_client
from .logging_config import get_logger

logger = get_logger(__name__)


class AuthError(Exception):
    """Base exception for authentication errors."""

    def __init__(self, message: str, code: str = "auth_error"):
        self.message = message
        self.code = code
        super().__init__(self.message)


class SupabaseAuthService:
    """
    Service class for Supabase authentication operations.

    Handles user registration, login, logout, and profile management
    using Supabase Auth API with JWT tokens.
    """

    def __init__(self):
        """Initialize Supabase auth service."""
        self.supabase: SupabaseClient = get_supabase_client()

    async def sign_up(
        self,
        email: str,
        password: str,
        full_name: Optional[str] = None,
        tier: str = "free",
    ) -> Dict[str, Any]:
        """
        Register a new user using Supabase Auth.

        Args:
            email: User email address
            password: User password
            full_name: Optional full name
            tier: Subscription tier (default: free)

        Returns:
            Dictionary containing user data and session tokens

        Raises:
            AuthError: If registration fails
        """
        try:
            logger.info(f"Attempting to register user with Supabase: {email}")

            # Sign up with Supabase Auth
            response = self.supabase.auth.sign_up(
                {
                    "email": email.lower(),
                    "password": password,
                    "options": {
                        "data": {
                            "full_name": full_name,
                            "tier": tier,
                        }
                    },
                }
            )

            if not response.user:
                raise AuthError("User registration failed", "registration_failed")

            user = response.user
            session = response.session

            logger.info(f"User registered successfully with Supabase: {email} (id: {user.id})")

            # Create user profile in user_profiles table
            try:
                await db_manager.execute(
                    """
                    INSERT INTO user_profiles (id, tier, full_name, created_at, updated_at)
                    VALUES ($1, $2, $3, NOW(), NOW())
                    ON CONFLICT (id) DO NOTHING
                    """,
                    user.id,
                    tier,
                    full_name,
                )
                logger.debug(f"User profile created for {user.id}")
            except Exception as e:
                logger.error(f"Failed to create user profile: {e}")
                # Don't fail registration if profile creation fails

            # Return session data in Supabase format
            return {
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "email_confirmed_at": user.email_confirmed_at,
                    "created_at": user.created_at,
                    "user_metadata": user.user_metadata or {},
                    "app_metadata": user.app_metadata or {},
                    "tier": tier,  # Include tier from input
                    "full_name": full_name,  # Include full_name from input
                },
                "session": {
                    "access_token": session.access_token if session else None,
                    "refresh_token": session.refresh_token if session else None,
                    "expires_in": session.expires_in if session else None,
                    "expires_at": session.expires_at if session else None,
                    "token_type": session.token_type if session else "bearer",
                }
                if session
                else None,
            }

        except AuthApiError as e:
            logger.error(f"Supabase auth error during sign up: {e.message}")
            if "already registered" in e.message.lower() or "duplicate" in e.message.lower():
                raise AuthError("Email already registered", "email_exists")
            raise AuthError(f"Registration failed: {e.message}", "supabase_error")
        except Exception as e:
            logger.error(f"Unexpected error during sign up: {e}")
            raise AuthError(f"Registration failed: {str(e)}", "internal_error")

    async def sign_in(
        self,
        email: str,
        password: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Authenticate user with Supabase Auth.

        Args:
            email: User email address
            password: User password
            ip_address: Client IP address (for audit logging)
            user_agent: Client user agent (for audit logging)

        Returns:
            Dictionary containing user data and session tokens

        Raises:
            AuthError: If authentication fails
        """
        try:
            logger.info(f"Attempting sign in with Supabase: {email}")

            # Sign in with Supabase Auth
            response = self.supabase.auth.sign_in_with_password(
                {"email": email.lower(), "password": password}
            )

            if not response.user or not response.session:
                raise AuthError("Invalid credentials", "invalid_credentials")

            user = response.user
            session = response.session

            logger.info(f"User signed in successfully: {email} (id: {user.id})")

            # Update last_login in user_profiles
            try:
                await db_manager.execute(
                    """
                    UPDATE user_profiles
                    SET last_login = NOW(), updated_at = NOW()
                    WHERE id = $1
                    """,
                    user.id,
                )
            except Exception as e:
                logger.warning(f"Failed to update last_login: {e}")

            return {
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "email_confirmed_at": user.email_confirmed_at,
                    "created_at": user.created_at,
                    "last_sign_in_at": user.last_sign_in_at,
                    "user_metadata": user.user_metadata or {},
                    "app_metadata": user.app_metadata or {},
                },
                "session": {
                    "access_token": session.access_token,
                    "refresh_token": session.refresh_token,
                    "expires_in": session.expires_in,
                    "expires_at": session.expires_at,
                    "token_type": session.token_type,
                },
            }

        except AuthApiError as e:
            logger.warning(f"Supabase auth error during sign in: {e.message}")
            if "invalid" in e.message.lower() or "credentials" in e.message.lower():
                raise AuthError("Invalid email or password", "invalid_credentials")
            raise AuthError(f"Sign in failed: {e.message}", "supabase_error")
        except Exception as e:
            logger.error(f"Unexpected error during sign in: {e}")
            raise AuthError(f"Sign in failed: {str(e)}", "internal_error")

    async def sign_out(self, access_token: str) -> Dict[str, Any]:
        """
        Sign out user from Supabase Auth.

        Args:
            access_token: User's access token

        Returns:
            Dictionary with success status

        Raises:
            AuthError: If sign out fails
        """
        try:
            logger.info("Attempting to sign out user")

            # Set the session token for this operation
            self.supabase.auth.set_session(access_token, None)

            # Sign out
            self.supabase.auth.sign_out()

            logger.info("User signed out successfully")
            return {"message": "Successfully signed out"}

        except AuthApiError as e:
            logger.error(f"Supabase auth error during sign out: {e.message}")
            raise AuthError(f"Sign out failed: {e.message}", "supabase_error")
        except Exception as e:
            logger.error(f"Unexpected error during sign out: {e}")
            raise AuthError(f"Sign out failed: {str(e)}", "internal_error")

    async def refresh_session(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh access token using Supabase Auth.

        Args:
            refresh_token: Refresh token

        Returns:
            Dictionary with new session tokens

        Raises:
            AuthError: If token refresh fails
        """
        try:
            logger.info("Attempting to refresh session")

            # Refresh session with Supabase
            response = self.supabase.auth.refresh_session(refresh_token)

            if not response.session:
                raise AuthError("Token refresh failed", "refresh_failed")

            session = response.session
            user = response.user

            logger.info(
                f"Session refreshed successfully for user: {user.id if user else 'unknown'}"
            )

            return {
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "user_metadata": user.user_metadata or {},
                }
                if user
                else None,
                "session": {
                    "access_token": session.access_token,
                    "refresh_token": session.refresh_token,
                    "expires_in": session.expires_in,
                    "expires_at": session.expires_at,
                    "token_type": session.token_type,
                },
            }

        except AuthApiError as e:
            logger.error(f"Supabase auth error during token refresh: {e.message}")
            raise AuthError(f"Token refresh failed: {e.message}", "invalid_refresh_token")
        except Exception as e:
            logger.error(f"Unexpected error during token refresh: {e}")
            raise AuthError(f"Token refresh failed: {str(e)}", "internal_error")

    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user data from Supabase Auth and user_profiles.

        Args:
            user_id: User UUID

        Returns:
            Dictionary with user data or None if not found
        """
        try:
            # Get user from Supabase (using service role key)
            user_response = self.supabase.auth.admin.get_user_by_id(user_id)

            if not user_response.user:
                return None

            user = user_response.user

            # Get user profile data
            profile = await db_manager.fetchrow(
                """
                SELECT tier, full_name, subscription_start, subscription_end,
                       stripe_customer_id, stripe_subscription_id, metadata,
                       last_login, created_at, updated_at
                FROM user_profiles
                WHERE id = $1
                """,
                user_id,
            )

            return {
                "id": user.id,
                "email": user.email,
                "email_confirmed_at": user.email_confirmed_at,
                "phone": user.phone,
                "created_at": user.created_at,
                "last_sign_in_at": user.last_sign_in_at,
                "user_metadata": user.user_metadata or {},
                "app_metadata": user.app_metadata or {},
                "tier": profile["tier"] if profile else "free",
                "full_name": profile["full_name"] if profile else None,
                "subscription_start": profile["subscription_start"].isoformat()
                if profile and profile["subscription_start"]
                else None,
                "subscription_end": profile["subscription_end"].isoformat()
                if profile and profile["subscription_end"]
                else None,
                "stripe_customer_id": profile["stripe_customer_id"] if profile else None,
                "stripe_subscription_id": profile["stripe_subscription_id"] if profile else None,
                "metadata": profile["metadata"] if profile else {},
                "last_login": profile["last_login"].isoformat()
                if profile and profile["last_login"]
                else None,
            }

        except Exception as e:
            logger.error(f"Error fetching user {user_id}: {e}")
            return None

    async def update_user(
        self,
        user_id: str,
        email: Optional[str] = None,
        full_name: Optional[str] = None,
        user_metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Update user profile.

        Args:
            user_id: User UUID
            email: New email (if changing)
            full_name: New full name
            user_metadata: Additional user metadata

        Returns:
            Updated user data

        Raises:
            AuthError: If update fails
        """
        try:
            logger.info(f"Updating user profile: {user_id}")

            # Update Supabase auth user
            update_data = {}
            if email:
                update_data["email"] = email.lower()
            if user_metadata:
                update_data["data"] = user_metadata

            if update_data:
                user_response = self.supabase.auth.admin.update_user_by_id(user_id, update_data)
                _ = user_response.user  # noqa: F841
            else:
                user_response = self.supabase.auth.admin.get_user_by_id(user_id)
                _ = user_response.user  # noqa: F841

            # Update user profile
            if full_name is not None:
                await db_manager.execute(
                    """
                    UPDATE user_profiles
                    SET full_name = $1, updated_at = NOW()
                    WHERE id = $2
                    """,
                    full_name,
                    user_id,
                )

            logger.info(f"User profile updated successfully: {user_id}")

            return await self.get_user(user_id)

        except AuthApiError as e:
            logger.error(f"Supabase auth error during user update: {e.message}")
            raise AuthError(f"Update failed: {e.message}", "update_failed")
        except Exception as e:
            logger.error(f"Error updating user {user_id}: {e}")
            raise AuthError(f"Update failed: {str(e)}", "internal_error")

    async def get_user_tier(self, user_id: str) -> Dict[str, Any]:
        """
        Get user's subscription tier.

        Args:
            user_id: User UUID

        Returns:
            Dictionary with tier information
        """
        try:
            profile = await db_manager.fetchrow(
                """
                SELECT tier, subscription_start, subscription_end
                FROM user_profiles
                WHERE id = $1
                """,
                user_id,
            )

            if not profile:
                return {"tier": "free", "subscription_active": False}

            subscription_active = False
            if profile["subscription_end"]:
                subscription_active = profile["subscription_end"] > datetime.now()

            return {
                "tier": profile["tier"],
                "subscription_active": subscription_active,
                "subscription_start": profile["subscription_start"].isoformat()
                if profile["subscription_start"]
                else None,
                "subscription_end": profile["subscription_end"].isoformat()
                if profile["subscription_end"]
                else None,
            }

        except Exception as e:
            logger.error(f"Error fetching tier for user {user_id}: {e}")
            return {"tier": "free", "subscription_active": False}

    async def update_user_tier(
        self,
        user_id: str,
        tier: str,
        subscription_start: Optional[datetime] = None,
        subscription_end: Optional[datetime] = None,
        stripe_customer_id: Optional[str] = None,
        stripe_subscription_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Update user's subscription tier.

        Args:
            user_id: User UUID
            tier: New tier (free, paid, enterprise)
            subscription_start: Subscription start date
            subscription_end: Subscription end date
            stripe_customer_id: Stripe customer ID
            stripe_subscription_id: Stripe subscription ID

        Returns:
            Updated tier information

        Raises:
            AuthError: If update fails
        """
        try:
            logger.info(f"Updating tier for user {user_id} to {tier}")

            await db_manager.execute(
                """
                UPDATE user_profiles
                SET tier = $1,
                    subscription_start = $2,
                    subscription_end = $3,
                    stripe_customer_id = $4,
                    stripe_subscription_id = $5,
                    updated_at = NOW()
                WHERE id = $6
                """,
                tier,
                subscription_start,
                subscription_end,
                stripe_customer_id,
                stripe_subscription_id,
                user_id,
            )

            logger.info(f"Tier updated successfully for user {user_id}")
            return await self.get_user_tier(user_id)

        except Exception as e:
            logger.error(f"Error updating tier for user {user_id}: {e}")
            raise AuthError(f"Tier update failed: {str(e)}", "update_failed")

    async def reset_password_request(self, email: str) -> bool:
        """
        Request password reset via Supabase Auth.

        Args:
            email: User email address

        Returns:
            True if reset email sent successfully
        """
        try:
            logger.info(f"Password reset requested for: {email}")

            # Supabase will send reset email
            self.supabase.auth.reset_password_for_email(
                email.lower(),
                {"redirect_to": f"{settings.FRONTEND_URL}/reset-password"},
            )

            logger.info(f"Password reset email sent to: {email}")
            return True

        except AuthApiError as e:
            logger.error(f"Supabase auth error during password reset: {e.message}")
            # Return True to prevent email enumeration
            return True
        except Exception as e:
            logger.error(f"Error requesting password reset: {e}")
            return True


# Global auth service instance
auth_service = SupabaseAuthService()
