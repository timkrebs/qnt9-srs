"""
Authentication service using Supabase.

Provides business logic for user authentication, registration,
and profile management using Supabase Auth.
"""

from typing import Any, Dict, Optional

from gotrue.errors import AuthApiError

from .logging_config import get_logger
from .supabase_client import get_supabase_client

logger = get_logger(__name__)


class AuthService:
    """
    Service class for authentication operations.

    Handles user registration, login, logout, and profile management
    using Supabase Auth.
    """

    def __init__(self) -> None:
        """Initialize auth service with Supabase client."""
        self.client = get_supabase_client()

    async def sign_up(
        self,
        email: str,
        password: str,
        full_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Register a new user.

        Args:
            email: User email address
            password: User password
            full_name: Optional full name

        Returns:
            Dictionary containing user data and session

        Raises:
            AuthApiError: If registration fails
        """
        try:
            logger.info(f"Attempting to register user: {email}")

            # Prepare user metadata
            user_metadata = {}
            if full_name:
                user_metadata["full_name"] = full_name

            # Sign up with Supabase
            response = self.client.auth.sign_up(
                {
                    "email": email,
                    "password": password,
                    "options": {"data": user_metadata} if user_metadata else {},
                }
            )

            if not response.user:
                raise ValueError("User registration failed - no user returned")

            logger.info(f"User registered successfully: {email}")

            return {
                "user": {
                    "id": response.user.id,
                    "email": response.user.email,
                    "full_name": response.user.user_metadata.get("full_name"),
                    "created_at": response.user.created_at,
                },
                "session": {
                    "access_token": response.session.access_token
                    if response.session
                    else None,
                    "refresh_token": response.session.refresh_token
                    if response.session
                    else None,
                },
            }

        except AuthApiError as e:
            logger.error(f"Registration failed for {email}: {e.message}")
            raise
        except Exception as e:
            logger.exception(f"Unexpected error during registration: {e}")
            raise

    async def sign_in(
        self,
        email: str,
        password: str,
    ) -> Dict[str, Any]:
        """
        Sign in a user with email and password.

        Args:
            email: User email
            password: User password

        Returns:
            Dictionary containing user data and session tokens

        Raises:
            AuthApiError: If sign in fails
        """
        try:
            logger.info(f"User sign in attempt: {email}")

            response = self.client.auth.sign_in_with_password(
                {"email": email, "password": password}
            )

            if not response.user or not response.session:
                raise ValueError("Sign in failed - no user or session returned")

            logger.info(f"User signed in successfully: {email}")

            return {
                "user": {
                    "id": response.user.id,
                    "email": response.user.email,
                    "full_name": response.user.user_metadata.get("full_name"),
                },
                "session": {
                    "access_token": response.session.access_token,
                    "refresh_token": response.session.refresh_token,
                    "expires_at": response.session.expires_at,
                },
            }

        except AuthApiError as e:
            logger.error(f"Sign in failed for {email}: {e.message}")
            raise
        except Exception as e:
            logger.exception(f"Unexpected error during sign in: {e}")
            raise

    async def sign_out(self, access_token: str) -> bool:
        """
        Sign out a user.

        Args:
            access_token: User's access token

        Returns:
            True if sign out successful

        Raises:
            AuthApiError: If sign out fails
        """
        try:
            logger.info("User sign out attempt")

            # Set the session for the sign out
            self.client.auth.set_session(access_token, "")
            self.client.auth.sign_out()

            logger.info("User signed out successfully")
            return True

        except AuthApiError as e:
            logger.error(f"Sign out failed: {e.message}")
            raise
        except Exception as e:
            logger.exception(f"Unexpected error during sign out: {e}")
            raise

    async def get_user(self, access_token: str) -> Optional[Dict[str, Any]]:
        """
        Get user information from access token.

        Args:
            access_token: User's JWT access token

        Returns:
            User information dictionary or None if invalid

        Raises:
            AuthApiError: If token validation fails
        """
        try:
            response = self.client.auth.get_user(access_token)

            if not response.user:
                return None

            return {
                "id": response.user.id,
                "email": response.user.email,
                "full_name": response.user.user_metadata.get("full_name"),
                "email_confirmed_at": response.user.email_confirmed_at,
                "created_at": response.user.created_at,
            }

        except AuthApiError as e:
            logger.error(f"Get user failed: {e.message}")
            return None
        except Exception as e:
            logger.exception(f"Unexpected error getting user: {e}")
            return None

    async def update_user(
        self,
        access_token: str,
        email: Optional[str] = None,
        password: Optional[str] = None,
        full_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Update user information.

        Args:
            access_token: User's access token
            email: New email (optional)
            password: New password (optional)
            full_name: New full name (optional)

        Returns:
            Updated user information

        Raises:
            AuthApiError: If update fails
        """
        try:
            logger.info("Updating user information")

            # Build update attributes
            attributes = {}
            if email:
                attributes["email"] = email
            if password:
                attributes["password"] = password

            # Update user metadata
            user_metadata = {}
            if full_name:
                user_metadata["full_name"] = full_name

            if user_metadata:
                attributes["data"] = user_metadata

            # Set session and update
            self.client.auth.set_session(access_token, "")
            response = self.client.auth.update_user(attributes)

            if not response.user:
                raise ValueError("User update failed - no user returned")

            logger.info("User updated successfully")

            return {
                "id": response.user.id,
                "email": response.user.email,
                "full_name": response.user.user_metadata.get("full_name"),
            }

        except AuthApiError as e:
            logger.error(f"User update failed: {e.message}")
            raise
        except Exception as e:
            logger.exception(f"Unexpected error updating user: {e}")
            raise

    async def refresh_session(
        self,
        refresh_token: str,
    ) -> Dict[str, Any]:
        """
        Refresh an expired session.

        Args:
            refresh_token: User's refresh token

        Returns:
            New session with access and refresh tokens

        Raises:
            AuthApiError: If refresh fails
        """
        try:
            logger.info("Refreshing user session")

            response = self.client.auth.refresh_session(refresh_token)

            if not response.session:
                raise ValueError("Session refresh failed")

            logger.info("Session refreshed successfully")

            return {
                "access_token": response.session.access_token,
                "refresh_token": response.session.refresh_token,
                "expires_at": response.session.expires_at,
            }

        except AuthApiError as e:
            logger.error(f"Session refresh failed: {e.message}")
            raise
        except Exception as e:
            logger.exception(f"Unexpected error refreshing session: {e}")
            raise

    async def reset_password_request(self, email: str) -> bool:
        """
        Request password reset email.

        Args:
            email: User email address

        Returns:
            True if request successful

        Raises:
            AuthApiError: If request fails
        """
        try:
            logger.info(f"Password reset requested for: {email}")

            self.client.auth.reset_password_email(email)

            logger.info(f"Password reset email sent to: {email}")
            return True

        except AuthApiError as e:
            logger.error(f"Password reset request failed: {e.message}")
            raise
        except Exception as e:
            logger.exception(f"Unexpected error requesting password reset: {e}")
            raise


# Global auth service instance
auth_service = AuthService()
