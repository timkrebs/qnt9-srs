"""
Vault KV Integration for Search Service - Static Database Credentials
This module handles authentication with Vault and retrieval of static database credentials from KV v2.
Adapted from auth-service pattern for search-service.
"""
import logging
import os
from typing import Dict, Optional

import hvac
from hvac.exceptions import Forbidden, InvalidPath

logger = logging.getLogger(__name__)


class VaultKVClient:
    """Client for managing Vault KV stored credentials"""

    def __init__(
        self,
        vault_addr: Optional[str] = None,
        vault_namespace: Optional[str] = None,
        vault_token: Optional[str] = None,
        kv_path: str = "kv/data/database/qnt9-srs",
    ):
        """
        Initialize the Vault client

        Args:
            vault_addr: Vault server address (defaults to VAULT_ADDR env var)
            vault_namespace: Vault namespace (defaults to VAULT_NAMESPACE env var)
            vault_token: Vault token (defaults to VAULT_TOKEN env var)
            kv_path: Path to database secrets in KV (defaults to "kv/data/database/qnt9-srs")
        """
        self.vault_addr = vault_addr or os.getenv("VAULT_ADDR")
        self.vault_namespace = vault_namespace or os.getenv("VAULT_NAMESPACE", "admin")
        self.vault_token = vault_token or os.getenv("VAULT_TOKEN")
        self.kv_path = kv_path

        if not all([self.vault_addr, self.vault_token]):
            raise ValueError(
                "Missing required Vault configuration. Please set VAULT_ADDR "
                "and VAULT_TOKEN environment variables."
            )

        print(f"Initializing Vault client: {self.vault_addr}")
        self.client = hvac.Client(
            url=self.vault_addr, token=self.vault_token, namespace=self.vault_namespace, timeout=10
        )

        print("Verifying Vault authentication...")
        # Verify authentication
        if not self.client.is_authenticated():
            raise ValueError("Vault authentication failed. Check your VAULT_TOKEN.")

        print("Vault authentication successful")
        logger.info("Successfully authenticated with Vault")

        self._cached_credentials = None

    def get_db_credentials(self, force_refresh: bool = False) -> Dict[str, str]:
        """
        Get database credentials from Vault KV

        Args:
            force_refresh: Force retrieval even if credentials are cached

        Returns:
            Dictionary with database connection details
        """
        # Check cache
        if not force_refresh and self._cached_credentials:
            logger.debug("Using cached credentials")
            return self._cached_credentials

        try:
            # Read from KV v2
            print(f"Reading from Vault KV path: {self.kv_path}")
            logger.debug(f"Attempting to read credentials from path: {self.kv_path}")
            response = self.client.secrets.kv.v2.read_secret_version(
                path=self.kv_path.replace("kv/data/", "").replace("kv/", ""), mount_point="kv"
            )

            print("Successfully read secret from Vault")
            credentials = response["data"]["data"]

            # Cache credentials
            self._cached_credentials = credentials

            logger.info(f"Retrieved database credentials from Vault: {self.kv_path}")

            return credentials

        except InvalidPath as e:
            logger.error(f"Secret path not found in Vault: {self.kv_path}")
            raise ValueError(
                f"Database credentials not found in Vault at {self.kv_path}. "
                f"Please run terraform apply to create them."
            ) from e
        except Forbidden as e:
            logger.error(f"Permission denied reading from Vault: {self.kv_path}")
            raise ValueError(
                f"Access denied to Vault path {self.kv_path}. Check your VAULT_TOKEN permissions."
            ) from e
        except Exception as e:
            logger.error(f"Unexpected error reading from Vault: {str(e)}")
            raise


def get_db_connection_string() -> str:
    """
    Helper function to get PostgreSQL connection string from Vault

    Returns:
        PostgreSQL connection string in SQLAlchemy format
    """
    vault_client = VaultKVClient()
    credentials = vault_client.get_db_credentials()

    # Build PostgreSQL connection string
    connection_string = (
        f"postgresql://{credentials['username']}:{credentials['password']}"
        f"@{credentials['host']}:{credentials.get('port', 5432)}/{credentials['database']}"
    )

    return connection_string
