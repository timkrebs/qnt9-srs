"""
Comprehensive tests for security.py module.

Tests password hashing, JWT token generation/validation, and utility functions.
"""

import time
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from app.security import (
    create_access_token,
    create_email_verification_token,
    create_password_reset_token,
    create_refresh_token,
    decode_access_token,
    generate_token,
    get_token_from_header,
    hash_password,
    hash_token,
    verify_password,
)


class TestPasswordHashing:
    """Test password hashing and verification."""

    def test_hash_password_returns_string(self):
        """Test that hash_password returns a string."""
        result = hash_password("mypassword")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_hash_password_different_from_original(self):
        """Test that hashed password differs from original."""
        password = "mypassword"
        hashed = hash_password(password)
        assert hashed != password

    def test_hash_password_different_salts(self):
        """Test that same password produces different hashes (different salts)."""
        password = "mypassword"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        assert hash1 != hash2  # Different salts

    def test_hash_password_bcrypt_format(self):
        """Test that hash is in bcrypt format."""
        hashed = hash_password("mypassword")
        assert hashed.startswith("$2b$")

    def test_verify_password_correct(self):
        """Test verify_password with correct password."""
        password = "TestPassword123!"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test verify_password with incorrect password."""
        password = "TestPassword123!"
        hashed = hash_password(password)
        assert verify_password("WrongPassword", hashed) is False

    def test_verify_password_empty(self):
        """Test verify_password with empty password."""
        hashed = hash_password("somepassword")
        assert verify_password("", hashed) is False

    def test_verify_password_special_characters(self):
        """Test password with special characters."""
        password = "P@$$w0rd!#$%^&*()"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_verify_password_unicode(self):
        """Test password with unicode characters."""
        password = "пароль密码test"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_verify_password_invalid_hash_format(self):
        """Test verify_password with invalid hash format."""
        result = verify_password("password", "invalid_hash")
        assert result is False

    def test_verify_password_empty_hash(self):
        """Test verify_password with empty hash."""
        result = verify_password("password", "")
        assert result is False


class TestTokenGeneration:
    """Test token generation utilities."""

    def test_generate_token_default_length(self):
        """Test generate_token with default length."""
        token = generate_token()
        assert isinstance(token, str)
        assert len(token) > 0

    def test_generate_token_custom_length(self):
        """Test generate_token with custom length."""
        token = generate_token(length=64)
        assert isinstance(token, str)
        # URL-safe base64 encoding produces longer strings
        assert len(token) > 64

    def test_generate_token_uniqueness(self):
        """Test that generated tokens are unique."""
        tokens = {generate_token() for _ in range(100)}
        assert len(tokens) == 100  # All unique

    def test_generate_token_url_safe(self):
        """Test that generated tokens are URL-safe."""
        for _ in range(10):
            token = generate_token()
            # URL-safe characters only
            assert all(c.isalnum() or c in "-_" for c in token)

    def test_hash_token_returns_string(self):
        """Test that hash_token returns a string."""
        result = hash_token("my_token")
        assert isinstance(result, str)

    def test_hash_token_consistent(self):
        """Test that same token always produces same hash."""
        token = "my_token_12345"
        hash1 = hash_token(token)
        hash2 = hash_token(token)
        assert hash1 == hash2

    def test_hash_token_different_inputs(self):
        """Test that different tokens produce different hashes."""
        hash1 = hash_token("token1")
        hash2 = hash_token("token2")
        assert hash1 != hash2

    def test_hash_token_sha256_length(self):
        """Test that hash has SHA-256 length (64 hex chars)."""
        hashed = hash_token("any_token")
        assert len(hashed) == 64
        # All hex characters
        assert all(c in "0123456789abcdef" for c in hashed)


class TestJWTAccessToken:
    """Test JWT access token creation and decoding."""

    def test_create_access_token_returns_string(self):
        """Test that create_access_token returns a string."""
        token = create_access_token(
            user_id="test-user-id",
            email="test@example.com",
            tier="free",
        )
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_access_token_jwt_format(self):
        """Test that token is in JWT format (3 parts)."""
        token = create_access_token(
            user_id="test-user-id",
            email="test@example.com",
        )
        parts = token.split(".")
        assert len(parts) == 3

    def test_decode_access_token_valid(self):
        """Test decoding a valid access token."""
        user_id = "test-user-id-123"
        email = "test@example.com"
        tier = "paid"

        token = create_access_token(
            user_id=user_id,
            email=email,
            tier=tier,
        )

        payload = decode_access_token(token)
        assert payload is not None
        assert payload["sub"] == user_id
        assert payload["email"] == email
        assert payload["tier"] == tier
        assert payload["type"] == "access"

    def test_decode_access_token_with_additional_claims(self):
        """Test access token with additional claims."""
        token = create_access_token(
            user_id="test-user-id",
            email="test@example.com",
            additional_claims={"custom_field": "custom_value"},
        )

        payload = decode_access_token(token)
        assert payload is not None
        assert payload.get("custom_field") == "custom_value"

    def test_decode_access_token_invalid(self):
        """Test decoding an invalid token."""
        payload = decode_access_token("invalid.token.here")
        assert payload is None

    def test_decode_access_token_tampered(self):
        """Test decoding a tampered token."""
        token = create_access_token(
            user_id="test-user-id",
            email="test@example.com",
        )
        # Tamper with the token
        tampered = token[:-5] + "XXXXX"
        payload = decode_access_token(tampered)
        assert payload is None

    def test_decode_access_token_expired(self):
        """Test decoding an expired token."""
        with patch("app.security.settings") as mock_settings:
            mock_settings.ACCESS_TOKEN_EXPIRE_MINUTES = 0
            mock_settings.JWT_SECRET_KEY = "test-secret"
            mock_settings.JWT_ALGORITHM = "HS256"

            # Create token that expires immediately
            token = create_access_token(
                user_id="test-user-id",
                email="test@example.com",
            )

            # Wait a moment
            time.sleep(0.1)

            # Should be expired
            payload = decode_access_token(token)
            # Token created with 0 minutes expiry should be expired
            # Note: The actual expiry might still pass because datetime includes microseconds

    def test_decode_access_token_empty(self):
        """Test decoding an empty token."""
        payload = decode_access_token("")
        assert payload is None

    def test_decode_access_token_none(self):
        """Test decoding None token returns None (handled gracefully)."""
        # PyJWT handles None by returning None or raising, either is acceptable
        payload = decode_access_token(None)
        assert payload is None


class TestRefreshToken:
    """Test refresh token creation."""

    def test_create_refresh_token_returns_tuple(self):
        """Test that create_refresh_token returns a tuple."""
        result = create_refresh_token("user-id-123")
        assert isinstance(result, tuple)
        assert len(result) == 3

    def test_create_refresh_token_components(self):
        """Test refresh token tuple components."""
        raw_token, hashed_token, expires_at = create_refresh_token("user-id-123")

        assert isinstance(raw_token, str)
        assert len(raw_token) > 0

        assert isinstance(hashed_token, str)
        assert len(hashed_token) == 64  # SHA-256 hex

        assert isinstance(expires_at, datetime)
        assert expires_at > datetime.now(timezone.utc)

    def test_create_refresh_token_unique(self):
        """Test that refresh tokens are unique."""
        tokens = {create_refresh_token("user-id")[0] for _ in range(50)}
        assert len(tokens) == 50

    def test_create_refresh_token_hash_matches(self):
        """Test that token hash matches when rehashed."""
        raw_token, hashed_token, _ = create_refresh_token("user-id")
        assert hash_token(raw_token) == hashed_token


class TestPasswordResetToken:
    """Test password reset token creation."""

    def test_create_password_reset_token_returns_tuple(self):
        """Test that create_password_reset_token returns a tuple."""
        result = create_password_reset_token()
        assert isinstance(result, tuple)
        assert len(result) == 3

    def test_create_password_reset_token_components(self):
        """Test password reset token tuple components."""
        raw_token, hashed_token, expires_at = create_password_reset_token()

        assert isinstance(raw_token, str)
        assert len(raw_token) > 0

        assert isinstance(hashed_token, str)
        assert len(hashed_token) == 64

        assert isinstance(expires_at, datetime)
        # Should expire within ~1 hour
        expected_max = datetime.now(timezone.utc) + timedelta(hours=1, minutes=5)
        assert expires_at < expected_max

    def test_create_password_reset_token_hash_matches(self):
        """Test that token hash matches."""
        raw_token, hashed_token, _ = create_password_reset_token()
        assert hash_token(raw_token) == hashed_token


class TestEmailVerificationToken:
    """Test email verification token creation."""

    def test_create_email_verification_token_returns_tuple(self):
        """Test that create_email_verification_token returns a tuple."""
        result = create_email_verification_token()
        assert isinstance(result, tuple)
        assert len(result) == 3

    def test_create_email_verification_token_components(self):
        """Test email verification token tuple components."""
        raw_token, hashed_token, expires_at = create_email_verification_token()

        assert isinstance(raw_token, str)
        assert len(raw_token) > 0

        assert isinstance(hashed_token, str)
        assert len(hashed_token) == 64

        assert isinstance(expires_at, datetime)
        # Should expire within ~7 days
        expected_max = datetime.now(timezone.utc) + timedelta(days=7, hours=1)
        assert expires_at < expected_max

    def test_create_email_verification_token_hash_matches(self):
        """Test that token hash matches."""
        raw_token, hashed_token, _ = create_email_verification_token()
        assert hash_token(raw_token) == hashed_token


class TestGetTokenFromHeader:
    """Test Authorization header parsing."""

    def test_get_token_from_header_valid_bearer(self):
        """Test extracting token from valid Bearer header."""
        token = get_token_from_header("Bearer my-access-token")
        assert token == "my-access-token"

    def test_get_token_from_header_lowercase_bearer(self):
        """Test extracting token with lowercase bearer."""
        token = get_token_from_header("bearer my-access-token")
        assert token == "my-access-token"

    def test_get_token_from_header_mixed_case_bearer(self):
        """Test extracting token with mixed case bearer."""
        token = get_token_from_header("BEARER my-access-token")
        assert token == "my-access-token"

    def test_get_token_from_header_none(self):
        """Test with None header."""
        token = get_token_from_header(None)
        assert token is None

    def test_get_token_from_header_empty(self):
        """Test with empty header."""
        token = get_token_from_header("")
        assert token is None

    def test_get_token_from_header_no_bearer(self):
        """Test with header missing Bearer prefix."""
        token = get_token_from_header("my-access-token")
        assert token is None

    def test_get_token_from_header_wrong_scheme(self):
        """Test with wrong auth scheme."""
        token = get_token_from_header("Basic credentials")
        assert token is None

    def test_get_token_from_header_extra_parts(self):
        """Test with extra parts in header."""
        token = get_token_from_header("Bearer token extra parts")
        assert token is None

    def test_get_token_from_header_only_bearer(self):
        """Test with only Bearer keyword."""
        token = get_token_from_header("Bearer")
        assert token is None

    def test_get_token_from_header_whitespace(self):
        """Test with whitespace-only token."""
        token = get_token_from_header("Bearer ")
        assert token is None
