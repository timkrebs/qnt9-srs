"""
Supabase database configuration for search service.

This module provides Supabase PostgreSQL connection string construction
using environment variables. Supabase offers free PostgreSQL hosting
with connection pooling and built-in security features.

Connection string format:
postgresql://postgres:[password]@db.[project-ref].supabase.co:5432/postgres

Environment variables required:
- PROJECT_URL: https://[project-ref].supabase.co
- DATABASE_PASSWORD: Database password from Supabase dashboard
- API_KEY: Optional, for Supabase client operations
"""

import logging
import os
import re
from typing import Optional

logger = logging.getLogger(__name__)

# Supabase configuration constants
SUPABASE_POSTGRES_PORT = 5432
SUPABASE_DATABASE_NAME = "postgres"
SUPABASE_USER = "postgres"
SUPABASE_HOST_PREFIX = "db"


def extract_project_reference(project_url: str) -> Optional[str]:
    """
    Extract project reference from Supabase PROJECT_URL.

    Args:
        project_url: Supabase project URL (e.g., https://jlshmxtbrfckmqfpjboy.supabase.co)

    Returns:
        Project reference string or None if extraction fails

    Example:
        >>> extract_project_reference("https://jlshmxtbrfckmqfpjboy.supabase.co")
        "jlshmxtbrfckmqfpjboy"
    """
    pattern = r"https://([a-z0-9]+)\.supabase\.co"
    match = re.match(pattern, project_url)

    if match:
        return match.group(1)

    logger.warning(f"Could not extract project reference from: {project_url}")
    return None


def build_supabase_connection_string() -> Optional[str]:
    """
    Build PostgreSQL connection string for Supabase database.

    Constructs connection string using environment variables:
    - PROJECT_URL: Supabase project URL
    - DATABASE_PASSWORD: Database password

    Connection string format:
    postgresql://postgres:[password]@db.[project-ref].supabase.co:5432/postgres

    Returns:
        PostgreSQL connection string or None if required variables missing

    Example:
        >>> os.environ["PROJECT_URL"] = "https://abc123.supabase.co"
        >>> os.environ["DATABASE_PASSWORD"] = "mypassword"
        >>> build_supabase_connection_string()
        "postgresql://postgres:mypassword@db.abc123.supabase.co:5432/postgres"
    """
    project_url = os.getenv("PROJECT_URL")
    database_password = os.getenv("DATABASE_PASSWORD")

    if not project_url or not database_password:
        logger.warning(
            "Supabase configuration incomplete: Missing PROJECT_URL or DATABASE_PASSWORD"
        )
        return None

    project_ref = extract_project_reference(project_url)
    if not project_ref:
        logger.error("Failed to extract project reference from PROJECT_URL")
        return None

    # Construct connection string for direct Supabase PostgreSQL connection
    # Format: postgresql://postgres:[password]@db.[project-ref].supabase.co:5432/postgres
    connection_string = (
        f"postgresql://{SUPABASE_USER}:{database_password}"
        f"@{SUPABASE_HOST_PREFIX}.{project_ref}.supabase.co:{SUPABASE_POSTGRES_PORT}/{SUPABASE_DATABASE_NAME}"
    )

    logger.info(f"Supabase connection string built for project: {project_ref}")
    return connection_string


def get_supabase_connection_string() -> Optional[str]:
    """
    Get Supabase PostgreSQL connection string with error handling.

    Wrapper function that safely attempts to build the connection string
    and handles any exceptions that may occur.

    Returns:
        PostgreSQL connection string or None if construction fails
    """
    try:
        return build_supabase_connection_string()
    except Exception as e:
        logger.error(f"Error building Supabase connection string: {e}")
        return None
