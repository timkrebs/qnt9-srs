"""
Vault Database Integration for FastAPI
This module handles authentication with Vault and retrieval of dynamic database credentials.
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Dict, Optional

import hvac

logger = logging.getLogger(__name__)


class VaultDBClient:
    """Client for managing Vault database credentials"""

    def __init__(
        self,
        vault_addr: Optional[str] = None,
        vault_namespace: Optional[str] = None,
        role_id: Optional[str] = None,
        secret_id: Optional[str] = None,
        db_secrets_path: str = "database",
        db_role_name: str = "qnt9-srs-fastapi-role",
    ):
        """
        Initialize the Vault client

        Args:
            vault_addr: Vault server address (defaults to VAULT_ADDR env var)
            vault_namespace: Vault namespace (defaults to VAULT_NAMESPACE env var)
            role_id: AppRole role ID (defaults to VAULT_APPROLE_ROLE_ID env var)
            secret_id: AppRole secret ID (defaults to VAULT_APPROLE_SECRET_ID env var)
            db_secrets_path: Path to database secrets engine (defaults to "database")
            db_role_name: Role name for database credentials (defaults to "qnt9-srs-fastapi-role")
        """
        self.vault_addr = vault_addr or os.getenv("VAULT_ADDR")
        self.vault_namespace = vault_namespace or os.getenv("VAULT_NAMESPACE", "admin")
        self.role_id = role_id or os.getenv("VAULT_APPROLE_ROLE_ID")
        self.secret_id = secret_id or os.getenv("VAULT_APPROLE_SECRET_ID")
        self.db_secrets_path = db_secrets_path
        self.db_role_name = db_role_name

        if not all([self.vault_addr, self.role_id, self.secret_id]):
            raise ValueError(
                "Missing required Vault configuration. Please set VAULT_ADDR, "
                "VAULT_APPROLE_ROLE_ID, and VAULT_APPROLE_SECRET_ID environment variables."
            )

        self.client = hvac.Client(url=self.vault_addr, namespace=self.vault_namespace)

        self._current_lease_id = None
        self._current_credentials = None
        self._lease_expiration = None

        # Authenticate on initialization
        self._authenticate()

    def _authenticate(self):
        """Authenticate with Vault using AppRole"""
        try:
            auth_response = self.client.auth.approle.login(
                role_id=self.role_id,
                secret_id=self.secret_id,
            )
            logger.info("Successfully authenticated with Vault")
            return auth_response
        except Exception as e:
            logger.error(f"Failed to authenticate with Vault: {e}")
            raise

    def _is_token_valid(self) -> bool:
        """Check if the current token is still valid"""
        try:
            return self.client.is_authenticated()
        except Exception:
            return False

    def _ensure_authenticated(self):
        """Ensure we have a valid authentication token"""
        if not self._is_token_valid():
            logger.info("Token expired or invalid, re-authenticating...")
            self._authenticate()

    def get_db_credentials(self, force_refresh: bool = False) -> Dict[str, str]:
        """
        Get database credentials from Vault

        Args:
            force_refresh: Force retrieval of new credentials even if current ones are valid

        Returns:
            Dictionary with 'username' and 'password' keys
        """
        # Check if we should reuse existing credentials
        if not force_refresh and self._current_credentials and self._lease_expiration:
            if datetime.now() < self._lease_expiration - timedelta(minutes=5):
                logger.debug("Using cached credentials")
                return self._current_credentials

        # Ensure we're authenticated
        self._ensure_authenticated()

        try:
            # Request new database credentials
            response = self.client.secrets.database.generate_credentials(
                name=self.db_role_name,
                mount_point=self.db_secrets_path,
            )

            credentials = {
                "username": response["data"]["username"],
                "password": response["data"]["password"],
            }

            # Store lease information
            self._current_lease_id = response["lease_id"]
            self._current_credentials = credentials

            # Calculate expiration time (with 5 minute buffer)
            lease_duration = response.get("lease_duration", 3600)
            self._lease_expiration = datetime.now() + timedelta(seconds=lease_duration)

            logger.info(
                f"Retrieved new database credentials. "
                f"Lease ID: {self._current_lease_id}, "
                f"Duration: {lease_duration}s, "
                f"Username: {credentials['username']}"
            )

            return credentials

        except Exception as e:
            logger.error(f"Failed to retrieve database credentials: {e}")
            raise

    def renew_lease(self) -> bool:
        """
        Renew the current database credential lease

        Returns:
            True if renewal was successful, False otherwise
        """
        if not self._current_lease_id:
            logger.warning("No active lease to renew")
            return False

        try:
            self._ensure_authenticated()

            response = self.client.sys.renew_lease(lease_id=self._current_lease_id)

            # Update expiration time
            lease_duration = response.get("lease_duration", 3600)
            self._lease_expiration = datetime.now() + timedelta(seconds=lease_duration)

            logger.info(
                f"Renewed lease {self._current_lease_id}. "
                f"New duration: {lease_duration}s"
            )

            return True

        except Exception as e:
            logger.error(f"Failed to renew lease: {e}")
            return False

    def revoke_lease(self) -> bool:
        """
        Revoke the current database credential lease

        Returns:
            True if revocation was successful, False otherwise
        """
        if not self._current_lease_id:
            logger.warning("No active lease to revoke")
            return False

        try:
            self._ensure_authenticated()

            self.client.sys.revoke_lease(lease_id=self._current_lease_id)

            logger.info(f"Revoked lease {self._current_lease_id}")

            # Clear cached credentials
            self._current_lease_id = None
            self._current_credentials = None
            self._lease_expiration = None

            return True

        except Exception as e:
            logger.error(f"Failed to revoke lease: {e}")
            return False

    def get_connection_string(
        self,
        host: Optional[str] = None,
        port: int = 5432,
        database: Optional[str] = None,
        force_refresh: bool = False,
    ) -> str:
        """
        Get a complete PostgreSQL connection string with dynamic credentials

        Args:
            host: Database host (defaults to DB_HOST env var)
            port: Database port (defaults to 5432)
            database: Database name (defaults to DB_NAME env var)
            force_refresh: Force retrieval of new credentials

        Returns:
            PostgreSQL connection string
        """
        host = host or os.getenv("DB_HOST")
        database = database or os.getenv("DB_NAME")

        if not all([host, database]):
            raise ValueError(
                "Missing database configuration. Please set DB_HOST and DB_NAME."
            )

        creds = self.get_db_credentials(force_refresh=force_refresh)

        return (
            f"postgresql://{creds['username']}:{creds['password']}"
            f"@{host}:{port}/{database}?sslmode=require"
        )


# Singleton instance for application use
_vault_client: Optional[VaultDBClient] = None


def get_vault_client() -> VaultDBClient:
    """
    Get or create the global VaultDBClient instance

    Returns:
        VaultDBClient instance
    """
    global _vault_client
    if _vault_client is None:
        _vault_client = VaultDBClient()
    return _vault_client


def get_db_connection_string(force_refresh: bool = False) -> str:
    """
    Convenience function to get database connection string

    Args:
        force_refresh: Force retrieval of new credentials

    Returns:
        PostgreSQL connection string with dynamic credentials
    """
    client = get_vault_client()
    return client.get_connection_string(force_refresh=force_refresh)
