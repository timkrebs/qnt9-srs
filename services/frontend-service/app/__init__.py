"""
Frontend Service Package.

This package provides the web frontend for the QNT9 Stock Recommendation System.
It includes FastAPI application, API client for backend services, and configuration.
"""

__version__ = "1.0.0"
__author__ = "QNT9 Team"
__description__ = "Web frontend for QNT9 Stock Recommendation System"

# Export main components
from .app import app
from .config import settings

__all__ = [
    "app",
    "settings",
    "__version__",
]
