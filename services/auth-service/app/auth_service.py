"""
Authentication service using PostgreSQL.

Provides business logic for user authentication, registration,
and profile management using local PostgreSQL database.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from uuid import UUID

from .config import settings
from .database import db_manager
from .logging_config import get_logger
from .security import (
    create_access_token,
    create_email_verification_token,
    create_password_reset_token,
    create_refresh_token,
    hash_password,
    hash_token,
    verify_password,
)

logger = get_logger(__name__)


class AuthError(Exception):
    """Base exception for authentication errors."""

    def __init__(self, message: str, code: str = "auth_error"):
        self.message = message
        self.code = code
        super().__init__(self.message)


class AuthService:
    """
    Service class for authentication operations.

    Handles user registration, login, logout, and profile management
    using PostgreSQL database with JWT tokens.
    """

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
            Dictionary containing user data and session tokens

        Raises:
            AuthError: If registration fails
        """
        try:
            logger.info(f"Attempting to register user: {email}")

            # Check if email already exists
            existing_user = await db_manager.fetchrow(
                "SELECT id FROM users WHERE email = $1", email.lower()
            )

            if existing_user:
                logger.warning(f"Registration failed - email already exists: {email}")
                raise AuthError("Email already registered", "email_exists")

            # Hash password
            password_hash = hash_password(password)

            # Create user
            user_row = await db_manager.fetchrow(
                """
                INSERT INTO users (email, password_hash, full_name, tier, created_at)
                VALUES ($1, $2, $3, 'free', NOW())
                RETURNING id, email, full_name, tier, created_at, email_verified
                """,
                email.lower(),
                password_hash,
                full_name,
            )

            user_id = str(user_row["id"])
            logger.info(f"User created successfully: {email} (id: {user_id})")

            # Create tokens
            access_token = create_access_token(
                user_id=user_id,
                email=user_row["email"],
                tier=user_row["tier"],
            )

            raw_refresh, hashed_refresh, refresh_expires = create_refresh_token(user_id)

            # Store refresh token
            await db_manager.execute(
                """
                INSERT INTO refresh_tokens (user_id, token_hash, expires_at)
                VALUES ($1, $2, $3)
                """,
                user_row["id"],
                hashed_refresh,
                refresh_expires,
            )

            return {
                "user": {
                    "id": user_id,
                    "email": user_row["email"],
                    "full_name": user_row["full_name"],
                    "created_at": (
                        user_row["created_at"].isoformat() if user_row["created_at"] else None
                    ),
                    "tier": user_row["tier"],
                    "email_verified": user_row["email_verified"],
                },
                "session": {
                    "access_token": access_token,
                    "refresh_token": raw_refresh,
                    "expires_at": int(
                        (
                            datetime.now(timezone.utc)
                            + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
                        ).timestamp()
                    ),
                },
            }

        except AuthError:
            raise
        except Exception as e:
            logger.exception(f"Unexpected error during registration: {e}")
            raise AuthError(f"Registration failed: {str(e)}", "registration_error")

    async def sign_in(
        self,
        email: str,
        password: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Sign in a user with email and password.

        Args:
            email: User email
            password: User password
            ip_address: Client IP address for audit
            user_agent: Client user agent for audit

        Returns:
            Dictionary containing user data and session tokens

        Raises:
            AuthError: If sign in fails
        """
        try:
            logger.info(f"User sign in attempt: {email}")

            # Fetch user
            user_row = await db_manager.fetchrow(
                """
                SELECT id, email, password_hash, full_name, tier, 
                       email_verified, created_at, subscription_end, is_active
                FROM users
                WHERE email = $1
                """,
                email.lower(),
            )

            if not user_row:
                logger.warning(f"Sign in failed - user not found: {email}")
                raise AuthError("Invalid email or password", "invalid_credentials")

            if not user_row["is_active"]:
                logger.warning(f"Sign in failed - account disabled: {email}")
                raise AuthError("Account is disabled", "account_disabled")

            # Verify password
            if not verify_password(password, user_row["password_hash"]):
                logger.warning(f"Sign in failed - invalid password: {email}")
                raise AuthError("Invalid email or password", "invalid_credentials")

            user_id = str(user_row["id"])

            # Update last login
            await db_manager.execute(
                "UPDATE users SET last_login = NOW() WHERE id = $1", user_row["id"]
            )

            # Create tokens
            access_token = create_access_token(
                user_id=user_id,
                email=user_row["email"],
                tier=user_row["tier"],
            )

            raw_refresh, hashed_refresh, refresh_expires = create_refresh_token(user_id)

            # Store refresh token
            await db_manager.execute(
                """
                INSERT INTO refresh_tokens (user_id, token_hash, expires_at, ip_address, user_agent)
                VALUES ($1, $2, $3, $4, $5)
                """,
                user_row["id"],
                hashed_refresh,
                refresh_expires,
                ip_address,
                user_agent,
            )

            logger.info(f"User signed in successfully: {email}")

            return {
                "user": {
                    "id": user_id,
                    "email": user_row["email"],
                    "full_name": user_row["full_name"],
                    "tier": user_row["tier"],
                    "email_verified": user_row["email_verified"],
                    "subscription_end": (
                        user_row["subscription_end"].isoformat()
                        if user_row["subscription_end"]
                        else None
                    ),
                },
                "session": {
                    "access_token": access_token,
                    "refresh_token": raw_refresh,
                    "expires_at": int(
                        (
                            datetime.now(timezone.utc)
                            + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
                        ).timestamp()
                    ),
                },
            }

        except AuthError:
            raise
        except Exception as e:
            logger.exception(f"Unexpected error during sign in: {e}")
            raise AuthError(f"Sign in failed: {str(e)}", "signin_error")

    async def sign_out(self, refresh_token: str) -> bool:
        """
        Sign out a user by revoking their refresh token.

        Args:
            refresh_token: The refresh token to revoke

        Returns:
            True if sign out successful
        """
        try:
            logger.info("User sign out attempt")

            token_hash = hash_token(refresh_token)

            # Revoke the refresh token
            result = await db_manager.execute(
                """
                UPDATE refresh_tokens
                SET revoked = TRUE, revoked_at = NOW()
                WHERE token_hash = $1 AND revoked = FALSE
                """,
                token_hash,
            )

            logger.info("User signed out successfully")
            return True

        except Exception as e:
            logger.exception(f"Unexpected error during sign out: {e}")
            raise AuthError(f"Sign out failed: {str(e)}", "signout_error")

    async def refresh_session(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh an expired session using a refresh token.

        Args:
            refresh_token: User's refresh token

        Returns:
            New session with access and refresh tokens

        Raises:
            AuthError: If refresh fails
        """
        try:
            logger.info("Refreshing user session")

            token_hash = hash_token(refresh_token)

            # Find and validate refresh token
            token_row = await db_manager.fetchrow(
                """
                SELECT rt.id, rt.user_id, rt.expires_at, rt.revoked,
                       u.email, u.tier, u.full_name, u.is_active
                FROM refresh_tokens rt
                JOIN users u ON u.id = rt.user_id
                WHERE rt.token_hash = $1
                """,
                token_hash,
            )

            if not token_row:
                raise AuthError("Invalid refresh token", "invalid_token")

            if token_row["revoked"]:
                raise AuthError("Refresh token has been revoked", "token_revoked")

            if token_row["expires_at"] < datetime.now(timezone.utc):
                raise AuthError("Refresh token has expired", "token_expired")

            if not token_row["is_active"]:
                raise AuthError("Account is disabled", "account_disabled")

            user_id = str(token_row["user_id"])

            # Revoke old refresh token
            await db_manager.execute(
                "UPDATE refresh_tokens SET revoked = TRUE, revoked_at = NOW() WHERE id = $1",
                token_row["id"],
            )

            # Create new tokens
            access_token = create_access_token(
                user_id=user_id,
                email=token_row["email"],
                tier=token_row["tier"],
            )

            raw_refresh, hashed_refresh, refresh_expires = create_refresh_token(user_id)

            # Store new refresh token
            await db_manager.execute(
                """
                INSERT INTO refresh_tokens (user_id, token_hash, expires_at)
                VALUES ($1, $2, $3)
                """,
                token_row["user_id"],
                hashed_refresh,
                refresh_expires,
            )

            logger.info(f"Session refreshed successfully for user {user_id}")

            return {
                "access_token": access_token,
                "refresh_token": raw_refresh,
                "expires_at": int(
                    (
                        datetime.now(timezone.utc)
                        + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
                    ).timestamp()
                ),
            }

        except AuthError:
            raise
        except Exception as e:
            logger.exception(f"Unexpected error refreshing session: {e}")
            raise AuthError(f"Session refresh failed: {str(e)}", "refresh_error")

    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user information by ID.

        Args:
            user_id: User's UUID

        Returns:
            User information dictionary or None if not found
        """
        try:
            user_row = await db_manager.fetchrow(
                """
                SELECT id, email, full_name, tier, email_verified,
                       email_verified_at, created_at, subscription_start,
                       subscription_end, last_login
                FROM users
                WHERE id = $1 AND is_active = TRUE
                """,
                UUID(user_id),
            )

            if not user_row:
                return None

            return {
                "id": str(user_row["id"]),
                "email": user_row["email"],
                "full_name": user_row["full_name"],
                "tier": user_row["tier"],
                "email_verified": user_row["email_verified"],
                "email_verified_at": (
                    user_row["email_verified_at"].isoformat()
                    if user_row["email_verified_at"]
                    else None
                ),
                "created_at": (
                    user_row["created_at"].isoformat() if user_row["created_at"] else None
                ),
                "subscription_start": (
                    user_row["subscription_start"].isoformat()
                    if user_row["subscription_start"]
                    else None
                ),
                "subscription_end": (
                    user_row["subscription_end"].isoformat()
                    if user_row["subscription_end"]
                    else None
                ),
                "last_login": (
                    user_row["last_login"].isoformat() if user_row["last_login"] else None
                ),
            }

        except Exception as e:
            logger.exception(f"Error getting user {user_id}: {e}")
            return None

    async def update_user(
        self,
        user_id: str,
        email: Optional[str] = None,
        full_name: Optional[str] = None,
        password: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Update user information.

        Args:
            user_id: User's UUID
            email: New email (optional)
            full_name: New full name (optional)
            password: New password (optional)

        Returns:
            Updated user information

        Raises:
            AuthError: If update fails
        """
        try:
            logger.info(f"Updating user information for {user_id}")

            updates = []
            params = []
            param_index = 1

            if email:
                # Check if email is already taken
                existing = await db_manager.fetchrow(
                    "SELECT id FROM users WHERE email = $1 AND id != $2",
                    email.lower(),
                    UUID(user_id),
                )
                if existing:
                    raise AuthError("Email already in use", "email_exists")
                updates.append(f"email = ${param_index}")
                params.append(email.lower())
                param_index += 1

            if full_name is not None:
                updates.append(f"full_name = ${param_index}")
                params.append(full_name)
                param_index += 1

            if password:
                updates.append(f"password_hash = ${param_index}")
                params.append(hash_password(password))
                param_index += 1

            if not updates:
                raise AuthError("No fields to update", "no_updates")

            params.append(UUID(user_id))
            query = f"""
                UPDATE users
                SET {', '.join(updates)}, updated_at = NOW()
                WHERE id = ${param_index}
                RETURNING id, email, full_name, tier
            """

            user_row = await db_manager.fetchrow(query, *params)

            if not user_row:
                raise AuthError("User not found", "user_not_found")

            logger.info(f"User updated successfully: {user_id}")

            return {
                "id": str(user_row["id"]),
                "email": user_row["email"],
                "full_name": user_row["full_name"],
                "tier": user_row["tier"],
            }

        except AuthError:
            raise
        except Exception as e:
            logger.exception(f"Error updating user {user_id}: {e}")
            raise AuthError(f"Update failed: {str(e)}", "update_error")

    async def reset_password_request(self, email: str) -> bool:
        """
        Request password reset email.

        Args:
            email: User email address

        Returns:
            True (always returns True for security - don't reveal if email exists)
        """
        try:
            logger.info(f"Password reset requested for: {email}")

            user_row = await db_manager.fetchrow(
                "SELECT id FROM users WHERE email = $1 AND is_active = TRUE", email.lower()
            )

            if user_row:
                # Create password reset token
                raw_token, hashed_token, expires_at = create_password_reset_token()

                # Invalidate any existing tokens
                await db_manager.execute(
                    "UPDATE password_reset_tokens SET used = TRUE WHERE user_id = $1 AND used = FALSE",
                    user_row["id"],
                )

                # Store new token
                await db_manager.execute(
                    """
                    INSERT INTO password_reset_tokens (user_id, token_hash, expires_at)
                    VALUES ($1, $2, $3)
                    """,
                    user_row["id"],
                    hashed_token,
                    expires_at,
                )

                # TODO: Send email with reset link containing raw_token
                logger.info(f"Password reset token created for {email}")

            return True

        except Exception as e:
            logger.exception(f"Error requesting password reset: {e}")
            return True  # Don't reveal errors

    async def get_user_tier(self, user_id: str) -> Dict[str, Any]:
        """
        Get user tier information.

        Args:
            user_id: User UUID

        Returns:
            Dictionary containing tier information
        """
        try:
            user_row = await db_manager.fetchrow(
                """
                SELECT id, tier, subscription_start, subscription_end
                FROM users
                WHERE id = $1
                """,
                UUID(user_id),
            )

            if not user_row:
                return {
                    "id": user_id,
                    "tier": "free",
                    "subscription_start": None,
                    "subscription_end": None,
                }

            return {
                "id": str(user_row["id"]),
                "tier": user_row["tier"],
                "subscription_start": (
                    user_row["subscription_start"].isoformat()
                    if user_row["subscription_start"]
                    else None
                ),
                "subscription_end": (
                    user_row["subscription_end"].isoformat()
                    if user_row["subscription_end"]
                    else None
                ),
            }

        except Exception as e:
            logger.error(f"Failed to fetch tier for user {user_id}: {e}")
            raise AuthError(f"Failed to fetch tier: {str(e)}", "tier_fetch_error")

    async def update_user_tier(
        self,
        user_id: str,
        tier: str,
    ) -> Dict[str, Any]:
        """
        Update user tier.

        Args:
            user_id: User UUID
            tier: New tier ('free', 'paid', 'enterprise')

        Returns:
            Dictionary containing updated tier information
        """
        try:
            logger.info(f"Updating tier for user {user_id} to: {tier}")

            subscription_start = datetime.now(timezone.utc)
            subscription_end = None

            if tier in ("paid", "enterprise"):
                subscription_end = subscription_start + timedelta(days=365)

            user_row = await db_manager.fetchrow(
                """
                UPDATE users
                SET tier = $1,
                    subscription_start = $2,
                    subscription_end = $3,
                    updated_at = NOW()
                WHERE id = $4
                RETURNING id, email, tier, subscription_start, subscription_end
                """,
                tier,
                subscription_start,
                subscription_end,
                UUID(user_id),
            )

            if not user_row:
                raise AuthError("User not found", "user_not_found")

            logger.info(f"Tier updated successfully for user {user_id}")

            return {
                "id": str(user_row["id"]),
                "email": user_row["email"],
                "tier": user_row["tier"],
                "subscription_start": (
                    user_row["subscription_start"].isoformat()
                    if user_row["subscription_start"]
                    else None
                ),
                "subscription_end": (
                    user_row["subscription_end"].isoformat()
                    if user_row["subscription_end"]
                    else None
                ),
            }

        except AuthError:
            raise
        except Exception as e:
            logger.error(f"Failed to update tier for user {user_id}: {e}")
            raise AuthError(f"Failed to update tier: {str(e)}", "tier_update_error")


# Global auth service instance
auth_service = AuthService()
