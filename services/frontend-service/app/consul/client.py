"""
Consul Service Discovery Client.

Provides service registration, discovery, and health checking capabilities
for integrating with HashiCorp Consul.
"""

import logging
import os
from typing import Any, Dict, List, Optional

try:
    import consul
    from consul.base import ConsulException

    CONSUL_AVAILABLE = True
except ImportError:
    CONSUL_AVAILABLE = False
    ConsulException = Exception


logger = logging.getLogger(__name__)


def get_service_id(service_name: str) -> str:
    """
    Generate a unique service ID.

    Uses hostname to ensure unique IDs for multiple instances.

    Args:
        service_name: Name of the service

    Returns:
        Unique service ID
    """
    hostname = os.getenv("HOSTNAME", os.uname().nodename)
    return f"{service_name}-{hostname}"


class ConsulClient:
    """
    Consul service discovery and registration client.

    Provides methods for service registration, discovery, and health checks.
    Falls back gracefully when Consul is unavailable or disabled.
    """

    def __init__(
        self,
        enabled: bool = False,
        host: str = "consul",
        port: int = 8500,
        scheme: str = "http",
        token: Optional[str] = None,
    ):
        """
        Initialize Consul client.

        Args:
            enabled: Whether Consul is enabled
            host: Consul server hostname
            port: Consul HTTP API port
            scheme: HTTP or HTTPS
            token: Consul ACL token (if using ACLs)
        """
        self.enabled = enabled
        self.host = host
        self.port = port
        self.scheme = scheme
        self.token = token
        self.client: Optional[consul.Consul] = None

        if not CONSUL_AVAILABLE:
            logger.warning("python-consul2 library not installed, Consul disabled")
            self.enabled = False
            return

        if self.enabled:
            try:
                self.client = consul.Consul(
                    host=host, port=port, scheme=scheme, token=token
                )
                logger.info(f"Consul client initialized at {host}:{port}")
            except Exception as e:
                logger.error(f"Failed to initialize Consul client: {e}")
                self.enabled = False

    def register_service(
        self,
        service_id: str,
        service_name: str,
        port: int,
        address: Optional[str] = None,
        tags: Optional[List[str]] = None,
        meta: Optional[Dict[str, str]] = None,
        health_check_path: str = "/health",
        health_check_interval: str = "10s",
        health_check_timeout: str = "5s",
        deregister_timeout: str = "30s",
    ) -> bool:
        """
        Register service with Consul.

        Args:
            service_id: Unique service instance ID
            service_name: Service name for discovery
            port: Service port number
            address: Service IP/hostname (auto-detected if None)
            tags: Service tags for filtering
            meta: Service metadata
            health_check_path: Health check HTTP endpoint
            health_check_interval: How often to check health
            health_check_timeout: Health check timeout
            deregister_timeout: Auto-deregister after this time if unhealthy

        Returns:
            True if registered successfully, False otherwise
        """
        if not self.enabled or not self.client:
            logger.debug("Consul disabled, skipping service registration")
            return False

        try:
            # Auto-detect address if not provided
            if not address:
                address = os.getenv("SERVICE_HOST", os.uname().nodename)

            # Build health check configuration
            health_check = {
                "http": f"http://{address}:{port}{health_check_path}",
                "interval": health_check_interval,
                "timeout": health_check_timeout,
                "deregistercriticalserviceafter": deregister_timeout,
            }

            # Register the service
            self.client.agent.service.register(
                name=service_name,
                service_id=service_id,
                address=address,
                port=port,
                tags=tags or [],
                meta=meta or {},
                check=health_check,
            )

            logger.info(
                f"Service registered with Consul: {service_id} ({service_name}) at {address}:{port}"
            )
            return True

        except ConsulException as e:
            logger.error(f"Failed to register service with Consul {service_id}: {e}")
            return False

    def deregister_service(self, service_id: str) -> bool:
        """
        Deregister service from Consul.

        Args:
            service_id: Service instance ID to deregister

        Returns:
            True if deregistered successfully, False otherwise
        """
        if not self.enabled or not self.client:
            logger.debug("Consul disabled, skipping service deregistration")
            return False

        try:
            self.client.agent.service.deregister(service_id)
            logger.info(f"Service deregistered from Consul: {service_id}")
            return True

        except ConsulException as e:
            logger.error(f"Failed to deregister service from Consul {service_id}: {e}")
            return False

    def discover_service(
        self, service_name: str, tag: Optional[str] = None, passing_only: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Discover a healthy service instance.

        Args:
            service_name: Name of service to discover
            tag: Filter by tag (optional)
            passing_only: Only return healthy instances

        Returns:
            Service instance information or None if not found
        """
        if not self.enabled or not self.client:
            logger.debug("Consul disabled, skipping service discovery")
            return None

        try:
            # Get service instances
            _, services = self.client.health.service(
                service_name, tag=tag, passing=passing_only
            )

            if not services:
                logger.warning(
                    f"No healthy instances found for service {service_name} (tag={tag})"
                )
                return None

            # Return first available instance
            service = services[0]
            instance_info = {
                "service_id": service["Service"]["ID"],
                "service_name": service["Service"]["Service"],
                "address": service["Service"]["Address"],
                "port": service["Service"]["Port"],
                "tags": service["Service"]["Tags"],
                "meta": service["Service"].get("Meta", {}),
            }

            logger.debug(
                f"Service instance discovered: {service_name} -> {instance_info}"
            )

            return instance_info

        except ConsulException as e:
            logger.error(f"Failed to discover service {service_name}: {e}")
            return None

    def discover_all_instances(
        self, service_name: str, tag: Optional[str] = None, passing_only: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Discover all healthy service instances.

        Args:
            service_name: Name of service to discover
            tag: Filter by tag (optional)
            passing_only: Only return healthy instances

        Returns:
            List of service instance information
        """
        if not self.enabled or not self.client:
            logger.debug("Consul disabled, skipping service discovery")
            return []

        try:
            # Get service instances
            _, services = self.client.health.service(
                service_name, tag=tag, passing=passing_only
            )

            instances = []
            for service in services:
                instance_info = {
                    "service_id": service["Service"]["ID"],
                    "service_name": service["Service"]["Service"],
                    "address": service["Service"]["Address"],
                    "port": service["Service"]["Port"],
                    "tags": service["Service"]["Tags"],
                    "meta": service["Service"].get("Meta", {}),
                }
                instances.append(instance_info)

            logger.debug(
                f"Service instances discovered for {service_name}: {len(instances)} instances"
            )

            return instances

        except ConsulException as e:
            logger.error(f"Failed to discover service instances {service_name}: {e}")
            return []

    def get_service_url(
        self,
        service_name: str,
        default_url: Optional[str] = None,
        tag: Optional[str] = None,
        use_discovery: bool = True,
    ) -> Optional[str]:
        """
        Get service URL for HTTP requests.

        Discovers service via Consul or falls back to default URL.

        Args:
            service_name: Name of service to discover
            default_url: Fallback URL if discovery fails
            tag: Filter by tag (optional)
            use_discovery: Whether to use service discovery

        Returns:
            Service URL or None
        """
        # If discovery disabled, use default
        if not use_discovery or not self.enabled:
            return default_url

        # Try to discover service
        instance = self.discover_service(service_name, tag=tag)

        if instance:
            address = instance["address"]
            port = instance["port"]
            return f"http://{address}:{port}"

        # Fall back to default URL
        logger.warning(
            f"Service discovery failed for {service_name}, using default URL: {default_url}"
        )
        return default_url

    def health_check(self) -> bool:
        """
        Check if Consul is healthy and accessible.

        Returns:
            True if Consul is healthy, False otherwise
        """
        if not self.enabled or not self.client:
            return False

        try:
            # Check Consul agent health
            self.client.agent.self()
            return True
        except Exception as e:
            logger.error(f"Consul health check failed: {e}")
            return False
