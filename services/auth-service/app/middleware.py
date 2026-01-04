"""
Middleware and dependency functions for the auth service.
"""

from .rate_limiter import (check_auth_rate_limit,
                           check_password_reset_rate_limit)

__all__ = ["check_auth_rate_limit", "check_password_reset_rate_limit"]
