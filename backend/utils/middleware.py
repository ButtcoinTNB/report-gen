"""
Middleware utilities for the FastAPI application.

This module contains middleware classes that can be applied to the FastAPI app.
"""

import time
import uuid
import os
from typing import Callable, Dict, Any
from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from backend.utils.error_handler import logger

# Check if we're in production mode
IS_PRODUCTION = os.getenv("NODE_ENV") == "production"

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that logs all requests and responses along with timing information.
    
    Logs detailed information about each request including:
    - Request ID (generated unique ID for request tracing)
    - HTTP method and path
    - Client IP address
    - Request headers (optional)
    - Response status code
    - Response time in milliseconds
    - Response size
    """
    
    def __init__(
        self, 
        app: ASGIApp, 
        log_headers: bool = False,
        exclude_paths: list = None
    ):
        """
        Initialize the middleware.
        
        Args:
            app: The ASGI application
            log_headers: Whether to include request headers in logs (default: False)
            exclude_paths: List of path prefixes to exclude from logging
        """
        super().__init__(app)
        self.log_headers = log_headers
        self.exclude_paths = exclude_paths or []
    
    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        """
        Process a request with logging.
        
        Args:
            request: The incoming request
            call_next: Function to call the next middleware or route handler
            
        Returns:
            The response from the route handler
        """
        # Skip logging for excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)
        
        # Generate a unique request ID
        request_id = str(uuid.uuid4())
        
        # Get client IP, handling proxy forwarding
        client_host = request.client.host if request.client else "unknown"
        forwarded_for = request.headers.get("x-forwarded-for")
        client_ip = forwarded_for.split(",")[0] if forwarded_for else client_host
        
        # Log request details
        logger.info(
            f"Request started | ID: {request_id} | {request.method} {request.url.path} | "
            f"Client: {client_ip}"
        )
        
        # Log headers if enabled
        if self.log_headers:
            logger.debug(f"Request headers | ID: {request_id} | {dict(request.headers)}")
        
        # Process the request and measure timing
        start_time = time.time()
        
        try:
            response = await call_next(request)
            
            # Calculate processing time in milliseconds
            process_time = (time.time() - start_time) * 1000
            
            # Get response size if available
            size = len(response.body) if hasattr(response, "body") else 0
            
            # Log completion with timing info
            logger.info(
                f"Request completed | ID: {request_id} | {request.method} {request.url.path} | "
                f"Status: {response.status_code} | {process_time:.2f}ms | {size} bytes"
            )
            
            # Add the request ID to response headers for tracking
            response.headers["X-Request-ID"] = request_id
            return response
            
        except Exception as e:
            # Log exceptions
            process_time = (time.time() - start_time) * 1000
            logger.error(
                f"Request failed | ID: {request_id} | {request.method} {request.url.path} | "
                f"Error: {str(e)} | {process_time:.2f}ms"
            )
            raise


def setup_middleware(app: FastAPI) -> None:
    """
    Set up all middleware for the FastAPI application.
    
    Args:
        app: The FastAPI application
    """
    # Add request logging middleware with environment-appropriate settings
    app.add_middleware(
        RequestLoggingMiddleware,
        log_headers=not IS_PRODUCTION,  # Only log headers in development
        exclude_paths=[
            "/docs", 
            "/openapi.json", 
            "/redoc", 
            "/favicon.ico",
            "/health",  # Don't log health checks in production
            "/metrics"  # Don't log metrics endpoints in production
        ]
    ) 