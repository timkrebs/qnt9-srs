"""
Vault KV Integration for Search Service - Static Database Credentials.

This module handles authentication with HashiCorp Vault and retrieval of
static database credentials from KV v2 secrets engine.
"""

import logging
import os
from typing import Dict, Optional

import hvac
from hvac.exceptions import Forbidden, InvalidPath

logger = logging.getLogger(__name__)

# Vault configuration constants
DEFAULT_VAULT_NAMESPACE = "admin"
DEFAULT_KV_PATH = "kv/data/database/qnt9-srs"
DEFAULT_KV_MOUNT_POINT = "kv"
VAULT_CLIENT_TIMEOUT = 10


class VaultKVClient:
    """
    Client for managing Vault KV stored credentials.

    Provides secure retrieval of database credentials from HashiCorp Vault
    using KV v2 secrets engine with optional credential caching.

    Attributes:
        vault_addr: Vault server address
        vault_namespace: Vault namespace
        vault_token: Vault authentication token
        kv_path: Path to database secrets in KV
        client: HVAC Vault client instance
    """

    def __init__(
        self,
        vault_addr: Optional[str] = None,
        vault_namespace: Optional[str] = None,
        vault_token: Optional[str] = None,
        kv_path: str = DEFAULT_KV_PATH,
    ):
        """
        Initialize the Vault client.

        Args:
            vault_addr: Vault server address (defaults to VAULT_ADDR env var)
            vault_namespace: Vault namespace (defaults to VAULT_NAMESPACE env var)
            vault_token: Vault token (defaults to VAULT_TOKEN env var)
            kv_path: Path to database secrets in KV

        Raises:
            ValueError: If required Vault configuration is missing or authentication fails
        """
        self.vault_addr = vault_addr or os.getenv("VAULT_ADDR")
        self.vault_namespace = vault_namespace or os.getenv(
            "VAULT_NAMESPACE", DEFAULT_VAULT_NAMESPACE
        )
        self.vault_token = vault_token or os.getenv("VAULT_TOKEN")
        self.kv_path = kv_path

        if not all([self.vault_addr, self.vault_token]):
            raise ValueError(
                "Missing required Vault configuration. Please set VAULT_ADDR "
                "and VAULT_TOKEN environment variables."
            )

        logger.info(f"Initializing Vault client: {self.vault_addr}")
        self.client = hvac.Client(
            url=self.vault_addr,
            token=self.vault_token,
            namespace=self.vault_namespace,
            timeout=VAULT_CLIENT_TIMEOUT,
        )

        logger.debug("Verifying Vault authentication...")
        if not self.client.is_authenticated():
            raise ValueError("Vault authentication failed. Check your VAULT_TOKEN.")

        logger.info("Vault authentication successful")

        self._cached_credentials: Optional[Dict[str, str]] = None

    def get_db_credentials(self, force_refresh: bool = False) -> Dict[str, str]:
        """
        Get database credentials from Vault KV.

        Credentials are cached after first retrieval to reduce Vault requests.
        Use force_refresh to bypass cache and retrieve fresh credentials.

        Args:
            force_refresh: Force retrieval even if credentials are cached

        Returns:
            Dictionary with database connection details

        Raises:
            ValueError: If credentials not found or access denied
        """
        if not force_refresh and self._cached_credentials:
            logger.debug("Using cached credentials")
            return self._cached_credentials

        try:
            logger.debug(f"Reading from Vault KV path: {self.kv_path}")

            # Extract path components for KV v2 API
            clean_path = self._clean_kv_path(self.kv_path)

            response = self.client.secrets.kv.v2.read_secret_version(
                path=clean_path,
                mount_point=DEFAULT_KV_MOUNT_POINT,
            )

            logger.debug("Successfully read secret from Vault")
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
                f"Access denied to Vault path {self.kv_path}. "
                f"Check your VAULT_TOKEN permissions."
            ) from e
        except Exception as e:
            logger.error(f"Unexpected error reading from Vault: {str(e)}")
            raise

    def _clean_kv_path(self, path: str) -> str:
        """
        Clean KV path by removing common prefixes.

        Args:
            path: Raw KV path

        Returns:
            Cleaned path suitable for KV v2 API
        """
        return path.replace("kv/data/", "").replace("kv/", "")


def get_db_connection_string() -> str:
    """
    Helper function to get PostgreSQL connection string from Vault.

    Retrieves database credentials from Vault and constructs a SQLAlchemy-
    compatible PostgreSQL connection string.

    Returns:
        PostgreSQL connection string in SQLAlchemy format

    Raises:
        ValueError: If credentials cannot be retrieved from Vault
    """
    vault_client = VaultKVClient()
    credentials = vault_client.get_db_credentials()

    connection_string = (
        f"postgresql://{credentials['username']}:{credentials['password']}"
        f"@{credentials['host']}:{credentials.get('port', 5432)}/{credentials['database']}"
    )

    return connection_string
