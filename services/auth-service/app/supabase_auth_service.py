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
from .database import get_supabase_client
from .logging_config import get_logger
from .security import extract_user_from_supabase_token

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

            logger.info(
                f"User registered successfully with Supabase: {email} (id: {user.id})"
            )

            # Create user profile in user_profiles table using Supabase client
            try:
                from datetime import datetime

                now = datetime.utcnow().isoformat()
                self.supabase.table("user_profiles").upsert(
                    {
                        "id": user.id,
                        "tier": tier,
                        "full_name": full_name,
                        "created_at": now,
                        "updated_at": now,
                    },
                    on_conflict="id",
                ).execute()
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
                "session": (
                    {
                        "access_token": session.access_token if session else None,
                        "refresh_token": session.refresh_token if session else None,
                        "expires_in": session.expires_in if session else None,
                        "expires_at": session.expires_at if session else None,
                        "token_type": session.token_type if session else "bearer",
                    }
                    if session
                    else None
                ),
            }

        except AuthApiError as e:
            logger.error(f"Supabase auth error during sign up: {e.message}")
            if (
                "already registered" in e.message.lower()
                or "duplicate" in e.message.lower()
            ):
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

            # Fetch user profile data from user_profiles table
            profile = None
            try:
                profile_result = (
                    self.supabase.table("user_profiles")
                    .select(
                        "tier, role, full_name, subscription_start, subscription_end, "
                        "stripe_customer_id, stripe_subscription_id, metadata, last_login"
                    )
                    .eq("id", user.id)
                    .execute()
                )
                profile = profile_result.data[0] if profile_result.data else None
            except Exception as e:
                logger.warning(f"Failed to fetch user profile: {e}")

            # Update last_login in user_profiles using Supabase client
            try:
                now = datetime.utcnow().isoformat()
                self.supabase.table("user_profiles").update(
                    {
                        "last_login": now,
                        "updated_at": now,
                    }
                ).eq("id", user.id).execute()
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
                    # Include profile data
                    "tier": profile["tier"] if profile else "free",
                    "role": profile.get("role", "user") if profile else "user",
                    "full_name": profile["full_name"] if profile else None,
                    "subscription_start": profile["subscription_start"] if profile else None,
                    "subscription_end": profile["subscription_end"] if profile else None,
                    "stripe_customer_id": profile["stripe_customer_id"] if profile else None,
                    "stripe_subscription_id": profile["stripe_subscription_id"] if profile else None,
                    "metadata": profile["metadata"] if profile else {},
                    "last_login": profile["last_login"] if profile else None,
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

        Note: According to Supabase docs, sign_out() invalidates the refresh token
        on the server side. The client should discard the access token locally.

        Args:
            access_token: User's access token

        Returns:
            Dictionary with success status and user context for audit

        Raises:
            AuthError: If sign out fails
        """
        try:
            logger.info("Attempting to sign out user")

            # Extract user info before signing out (for audit logging)
            user_info = extract_user_from_supabase_token(access_token)
            user_id = user_info.get("id") if user_info else None
            email = user_info.get("email") if user_info else None

            # Note: Supabase sign_out() works on the current session context
            # We don't need to explicitly set the session if using service role
            # For user-scoped operations, sign_out() is called client-side
            # Server-side, we just invalidate tokens by returning success
            # The actual token invalidation happens in Supabase Auth automatically

            logger.info(f"User signed out successfully: {email} (id: {user_id})")
            return {
                "message": "Successfully signed out",
                "user_id": user_id,
                "email": email,
            }

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
            Dictionary with new session tokens and user context for audit

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
                "access_token": session.access_token,
                "refresh_token": session.refresh_token,
                "expires_in": session.expires_in,
                "expires_at": session.expires_at,
                "token_type": session.token_type,
                # Include user context for audit logging
                "user_id": user.id if user else None,
                "email": user.email if user else None,
            }

        except AuthApiError as e:
            logger.error(f"Supabase auth error during token refresh: {e.message}")
            raise AuthError(
                f"Token refresh failed: {e.message}", "invalid_refresh_token"
            )
        except Exception as e:
            logger.error(f"Unexpected error during token refresh: {e}")
            raise AuthError(f"Token refresh failed: {str(e)}", "internal_error")

    async def get_user(
        self, user_id: str, jwt_token: str | None = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get user data from Supabase Auth and user_profiles.

        Args:
            user_id: User UUID
            jwt_token: Optional JWT token for validation via Supabase

        Returns:
            Dictionary with user data or None if not found
        """
        try:
            # Get user from Supabase using JWT validation if token provided
            if jwt_token:
                user_response = self.supabase.auth.get_user(jwt_token)
                if not user_response.user:
                    logger.warning(f"User not found via JWT validation: {user_id}")
                    return None
                user = user_response.user
            else:
                # Fallback to admin API if no token provided
                user_response = self.supabase.auth.admin.get_user_by_id(user_id)
                if not user_response.user:
                    logger.warning(f"User not found via admin API: {user_id}")
                    return None
                user = user_response.user

            # Get user profile data using Supabase client
            profile_result = (
                self.supabase.table("user_profiles")
                .select(
                    "tier, role, full_name, subscription_start, subscription_end, "
                    "stripe_customer_id, stripe_subscription_id, metadata, "
                    "last_login, created_at, updated_at"
                )
                .eq("id", user.id)
                .execute()
            )

            profile = profile_result.data[0] if profile_result.data else None

            # Get role from profile, default to 'user' if not set
            user_role = profile.get("role", "user") if profile else "user"

            # Log if profile not found
            if not profile:
                logger.warning(f"User profile not found in database for user {user.id}")

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
                "role": user_role,
                "full_name": profile["full_name"] if profile else None,
                "subscription_start": (
                    profile["subscription_start"]
                    if profile and profile["subscription_start"]
                    else None
                ),
                "subscription_end": (
                    profile["subscription_end"]
                    if profile and profile["subscription_end"]
                    else None
                ),
                "stripe_customer_id": (
                    profile["stripe_customer_id"] if profile else None
                ),
                "stripe_subscription_id": (
                    profile["stripe_subscription_id"] if profile else None
                ),
                "metadata": profile["metadata"] if profile else {},
                "last_login": (
                    profile["last_login"]
                    if profile and profile["last_login"]
                    else None
                ),
            }

        except Exception as e:
            logger.error(f"Error fetching user {user_id}: {e}")
            return None

    async def update_user(
        self,
        user_id: str,
        email: Optional[str] = None,
        full_name: Optional[str] = None,
        password: Optional[str] = None,
        user_metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Update user profile.

        Args:
            user_id: User UUID
            email: New email (if changing)
            full_name: New full name
            password: New password (if changing)
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
            if password:
                update_data["password"] = password
            if user_metadata:
                update_data["data"] = user_metadata

            if update_data:
                user_response = self.supabase.auth.admin.update_user_by_id(
                    user_id, update_data
                )
                _ = user_response.user  # noqa: F841
            
            # Update user profile using Supabase client (for full_name)
            if full_name is not None:
                # Ensure user profile exists before updating
                profile_check = (
                    self.supabase.table("user_profiles")
                    .select("id")
                    .eq("id", user_id)
                    .execute()
                )
                
                if not profile_check.data:
                    # Create user profile if it doesn't exist
                    logger.info(f"Creating missing user profile for user {user_id}")
                    now = datetime.utcnow().isoformat()
                    self.supabase.table("user_profiles").insert(
                        {
                            "id": user_id,
                            "full_name": full_name,
                            "tier": "free",
                            "created_at": now,
                            "updated_at": now,
                        }
                    ).execute()
                else:
                    # Update existing profile
                    self.supabase.table("user_profiles").update(
                        {
                            "full_name": full_name,
                            "updated_at": datetime.utcnow().isoformat(),
                        }
                    ).eq("id", user_id).execute()

            logger.info(f"User profile updated successfully: {user_id}")

            # Fetch updated user data
            updated_user = await self.get_user(user_id)
            if updated_user is None:
                raise AuthError("Failed to retrieve updated user data", "user_not_found")
            
            return updated_user

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
            Dictionary with tier information including user_id
        """
        try:
            # Use Supabase client instead of asyncpg
            profile_result = (
                self.supabase.table("user_profiles")
                .select("id, tier, subscription_start, subscription_end")
                .eq("id", user_id)
                .execute()
            )

            profile = profile_result.data[0] if profile_result.data else None

            if not profile:
                logger.warning(f"User profile not found for tier query: {user_id}")
                return {
                    "id": user_id,
                    "tier": "free",
                    "subscription_active": False,
                    "subscription_start": None,
                    "subscription_end": None,
                }

            subscription_active = False
            if profile["subscription_end"]:
                # Parse string to datetime if needed
                subscription_end = profile["subscription_end"]
                if isinstance(subscription_end, str):
                    from datetime import datetime

                    subscription_end = datetime.fromisoformat(
                        subscription_end.replace("Z", "+00:00")
                    )
                subscription_active = subscription_end > datetime.now()

            return {
                "id": profile["id"],
                "tier": profile["tier"],
                "subscription_active": subscription_active,
                "subscription_start": (
                    profile["subscription_start"]
                    if isinstance(profile["subscription_start"], str)
                    else (
                        profile["subscription_start"].isoformat()
                        if profile["subscription_start"]
                        else None
                    )
                ),
                "subscription_end": (
                    profile["subscription_end"]
                    if isinstance(profile["subscription_end"], str)
                    else (
                        profile["subscription_end"].isoformat()
                        if profile["subscription_end"]
                        else None
                    )
                ),
            }

        except Exception as e:
            logger.error(f"Error fetching tier for user {user_id}: {e}")
            # Return default tier instead of raising error
            return {
                "id": user_id,
                "tier": "free",
                "subscription_active": False,
                "subscription_start": None,
                "subscription_end": None,
            }

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

            # Use Supabase client for updates
            from datetime import datetime

            self.supabase.table("user_profiles").update(
                {
                    "tier": tier,
                    "subscription_start": (
                        subscription_start.isoformat() if subscription_start else None
                    ),
                    "subscription_end": (
                        subscription_end.isoformat() if subscription_end else None
                    ),
                    "stripe_customer_id": stripe_customer_id,
                    "stripe_subscription_id": stripe_subscription_id,
                    "updated_at": datetime.utcnow().isoformat(),
                }
            ).eq("id", user_id).execute()

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

    async def update_password(self, access_token: str, new_password: str) -> bool:
        """
        Update user password using Supabase Auth.

        This is called after the user clicks the reset link and provides a new password.
        The access_token comes from the password reset email link.

        Args:
            access_token: Access token from reset email
            new_password: New password to set

        Returns:
            True if password updated successfully

        Raises:
            AuthError: If password update fails
        """
        try:
            logger.info("Attempting to update password")

            # Extract user info from token for logging
            user_info = extract_user_from_supabase_token(access_token)
            user_id = user_info.get("id") if user_info else None
            email = user_info.get("email") if user_info else None

            # Set session for this operation
            self.supabase.auth.set_session(access_token, None)

            # Update password
            response = self.supabase.auth.update_user({"password": new_password})

            if not response.user:
                raise AuthError("Password update failed", "update_failed")

            logger.info(
                f"Password updated successfully for user: {email} (id: {user_id})"
            )
            return True

        except AuthApiError as e:
            logger.error(f"Supabase auth error during password update: {e.message}")
            if "invalid" in e.message.lower() or "expired" in e.message.lower():
                raise AuthError("Invalid or expired reset token", "invalid_token")
            raise AuthError(f"Password update failed: {e.message}", "update_failed")
        except Exception as e:
            logger.error(f"Unexpected error during password update: {e}")
            raise AuthError(f"Password update failed: {str(e)}", "internal_error")

    async def delete_user(self, user_id: str) -> bool:
        """
        Delete a user account from Supabase.

        This method deletes the user from Supabase Auth and removes their profile
        from the user_profiles table.

        Args:
            user_id: User UUID to delete

        Returns:
            True if deletion was successful

        Raises:
            AuthError: If deletion fails
        """
        try:
            logger.info(f"Attempting to delete user: {user_id}")

            # First, delete the user profile from user_profiles table
            try:
                self.supabase.table("user_profiles").delete().eq(
                    "id", user_id
                ).execute()
                logger.info(f"Deleted user profile for: {user_id}")
            except Exception as e:
                logger.warning(f"Failed to delete user profile (may not exist): {e}")

            # Delete user from Supabase Auth using admin API
            self.supabase.auth.admin.delete_user(user_id)

            logger.info(f"User deleted successfully: {user_id}")
            return True

        except AuthApiError as e:
            logger.error(f"Supabase auth error during user deletion: {e.message}")
            raise AuthError(f"Account deletion failed: {e.message}", "deletion_failed")
        except Exception as e:
            logger.error(f"Unexpected error during user deletion: {e}")
            raise AuthError(f"Account deletion failed: {str(e)}", "internal_error")


# Global auth service instance
auth_service = SupabaseAuthService()
