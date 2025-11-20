"""Consul service discovery package."""

from .client import ConsulClient, get_service_id

__all__ = ["ConsulClient", "get_service_id"]
