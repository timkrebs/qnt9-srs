"""
Graceful shutdown handler for FastAPI services.

Handles SIGTERM and SIGINT signals to ensure proper cleanup of resources
before service termination.
"""

import asyncio
import signal
import sys
from typing import Callable, List, Optional

from .logging_config import get_logger

logger = get_logger(__name__)


class GracefulShutdownHandler:
    """
    Manages graceful shutdown of FastAPI application.
    
    Handles SIGTERM and SIGINT signals, allowing proper cleanup
    of database connections, caches, and other resources.
    """
    
    def __init__(self, service_name: str):
        """
        Initialize shutdown handler.
        
        Args:
            service_name: Name of the service for logging
        """
        self.service_name = service_name
        self.shutdown_event = asyncio.Event()
        self.cleanup_callbacks: List[Callable] = []
        self.is_shutting_down = False
        
    def register_cleanup(self, callback: Callable) -> None:
        """
        Register a cleanup callback to be called during shutdown.
        
        Callbacks are executed in reverse registration order (LIFO).
        
        Args:
            callback: Async or sync function to call during cleanup
        """
        self.cleanup_callbacks.append(callback)
        logger.debug(f"Registered cleanup callback: {callback.__name__}")
    
    def setup_signal_handlers(self) -> None:
        """
        Setup signal handlers for SIGTERM and SIGINT.
        
        Should be called during application startup.
        """
        def signal_handler(signum: int, frame) -> None:
            """Handle shutdown signals."""
            signal_name = signal.Signals(signum).name
            logger.info(
                f"Received {signal_name} signal, initiating graceful shutdown",
                extra={"extra_fields": {"signal": signal_name}}
            )
            
            if self.is_shutting_down:
                logger.warning("Shutdown already in progress, ignoring signal")
                return
            
            self.is_shutting_down = True
            
            asyncio.create_task(self._perform_shutdown())
        
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        
        logger.info(
            f"Signal handlers registered for {self.service_name}",
            extra={"extra_fields": {"signals": ["SIGTERM", "SIGINT"]}}
        )
    
    async def _perform_shutdown(self) -> None:
        """
        Perform graceful shutdown sequence.
        
        Executes all registered cleanup callbacks in reverse order.
        """
        logger.info(f"Starting graceful shutdown sequence for {self.service_name}")
        
        cleanup_count = len(self.cleanup_callbacks)
        logger.info(f"Executing {cleanup_count} cleanup callbacks")
        
        for idx, callback in enumerate(reversed(self.cleanup_callbacks), 1):
            try:
                callback_name = callback.__name__
                logger.debug(f"Executing cleanup {idx}/{cleanup_count}: {callback_name}")
                
                if asyncio.iscoroutinefunction(callback):
                    await callback()
                else:
                    callback()
                
                logger.debug(f"Completed cleanup: {callback_name}")
                
            except Exception as e:
                logger.error(
                    f"Error in cleanup callback {callback.__name__}: {e}",
                    exc_info=True
                )
        
        logger.info(f"Graceful shutdown completed for {self.service_name}")
        self.shutdown_event.set()
        
        sys.exit(0)
    
    async def wait_for_shutdown(self) -> None:
        """
        Wait for shutdown signal.
        
        Useful for keeping the application running in background tasks.
        """
        await self.shutdown_event.wait()


_shutdown_handler: Optional[GracefulShutdownHandler] = None


def get_shutdown_handler(service_name: str = "service") -> GracefulShutdownHandler:
    """
    Get or create global shutdown handler instance.
    
    Args:
        service_name: Name of the service
        
    Returns:
        GracefulShutdownHandler instance
    """
    global _shutdown_handler
    
    if _shutdown_handler is None:
        _shutdown_handler = GracefulShutdownHandler(service_name)
    
    return _shutdown_handler


def setup_graceful_shutdown(
    service_name: str,
    cleanup_callbacks: Optional[List[Callable]] = None
) -> GracefulShutdownHandler:
    """
    Setup graceful shutdown for a service.
    
    Args:
        service_name: Name of the service
        cleanup_callbacks: Optional list of cleanup functions
        
    Returns:
        Configured GracefulShutdownHandler
    """
    handler = get_shutdown_handler(service_name)
    
    if cleanup_callbacks:
        for callback in cleanup_callbacks:
            handler.register_cleanup(callback)
    
    handler.setup_signal_handlers()
    
    return handler
