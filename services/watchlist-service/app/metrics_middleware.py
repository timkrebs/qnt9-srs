"""
Metrics middleware for FastAPI applications.

Automatically tracks HTTP request metrics for all endpoints.
"""

import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable


class PrometheusMiddleware(BaseHTTPMiddleware):
    """
    Middleware to automatically track Prometheus metrics for all HTTP requests.
    
    Tracks:
    - Request count by method, endpoint, and status code
    - Request duration by method and endpoint
    """
    
    def __init__(self, app, track_func: Callable):
        """
        Initialize the middleware.
        
        Args:
            app: FastAPI application
            track_func: Function to call for tracking metrics (method, endpoint, status, duration)
        """
        super().__init__(app)
        self.track_func = track_func
    
    async def dispatch(self, request: Request, call_next):
        """
        Process the request and track metrics.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware or route handler
            
        Returns:
            HTTP response
        """
        start_time = time.time()
        
        # Process request
        response = await call_next(request)
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Extract endpoint path (remove query parameters)
        endpoint = request.url.path
        
        # Track metrics
        self.track_func(
            method=request.method,
            endpoint=endpoint,
            status_code=response.status_code,
            duration=duration
        )
        
        return response
