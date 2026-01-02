"""
Validation utilities for authentication service.

Provides validators for password strength, email format, and input sanitization.
"""

import re
from typing import Tuple


class PasswordValidator:
    """
    Password strength validator.

    Enforces production-grade password policies:
    - Minimum 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character
    - Maximum 128 characters (prevent DoS)
    """

    MIN_LENGTH = 8
    MAX_LENGTH = 128

    UPPERCASE_PATTERN = re.compile(r"[A-Z]")
    LOWERCASE_PATTERN = re.compile(r"[a-z]")
    DIGIT_PATTERN = re.compile(r"\d")
    SPECIAL_CHAR_PATTERN = re.compile(r'[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\;\'`~]')

    @classmethod
    def validate(cls, password: str) -> Tuple[bool, str]:
        """
        Validate password strength.

        Args:
            password: Password string to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not password:
            return False, "Password is required"

        if len(password) < cls.MIN_LENGTH:
            return False, f"Password must be at least {cls.MIN_LENGTH} characters long"

        if len(password) > cls.MAX_LENGTH:
            return False, f"Password must not exceed {cls.MAX_LENGTH} characters"

        if not cls.UPPERCASE_PATTERN.search(password):
            return False, "Password must contain at least one uppercase letter"

        if not cls.LOWERCASE_PATTERN.search(password):
            return False, "Password must contain at least one lowercase letter"

        if not cls.DIGIT_PATTERN.search(password):
            return False, "Password must contain at least one digit"

        if not cls.SPECIAL_CHAR_PATTERN.search(password):
            return False, "Password must contain at least one special character"

        return True, ""

    @classmethod
    def get_requirements_message(cls) -> str:
        """Get password requirements message for user display."""
        return (
            f"Password must be {cls.MIN_LENGTH}-{cls.MAX_LENGTH} characters long and contain "
            "at least one uppercase letter, one lowercase letter, one digit, "
            "and one special character (!@#$%^&*(),.?\":{}|<>_-+=[]\\;'`~)"
        )


def validate_email_format(email: str) -> Tuple[bool, str]:
    """
    Additional email validation beyond Pydantic EmailStr.

    Checks for common security issues and malformed addresses.

    Args:
        email: Email address to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not email:
        return False, "Email is required"

    if len(email) > 320:
        return False, "Email address is too long"

    if email.count("@") != 1:
        return False, "Email must contain exactly one @ symbol"

    local_part, domain = email.rsplit("@", 1)

    if len(local_part) == 0:
        return False, "Email local part cannot be empty"

    if len(local_part) > 64:
        return False, "Email local part is too long"

    if len(domain) == 0:
        return False, "Email domain cannot be empty"

    if len(domain) > 255:
        return False, "Email domain is too long"

    if ".." in email:
        return False, "Email cannot contain consecutive dots"

    if domain.startswith(".") or domain.endswith("."):
        return False, "Email domain cannot start or end with a dot"

    return True, ""


def sanitize_full_name(full_name: str) -> str:
    """
    Sanitize full name input.

    Removes potential XSS vectors and limits length.

    Args:
        full_name: User's full name

    Returns:
        Sanitized full name
    """
    if not full_name:
        return ""

    sanitized = full_name.strip()

    sanitized = re.sub(r"[<>\"\'&]", "", sanitized)

    if len(sanitized) > 255:
        sanitized = sanitized[:255]

    return sanitized
