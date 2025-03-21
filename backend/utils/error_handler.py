"""
Utility for standardized error handling across all API endpoints.
This ensures consistent error responses and logging throughout the application.
"""

import logging
import traceback
import json
from typing import Dict, Any, Optional, Type, Union, Callable
from functools import wraps
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

# Import the standard APIResponse model
from api.schemas import APIResponse

# Import our custom exceptions
from utils.exceptions import (
    BaseAPIException,
    ValidationException,
    BadRequestException,
    NotFoundException,
    InternalServerException
)

# Configure logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Exception mapping for converting standard exceptions to our custom exceptions
EXCEPTION_MAPPING = {
    ValidationError: lambda e: ValidationException(str(e), details=str(e.errors())),
    ValueError: lambda e: BadRequestException(str(e)),
    KeyError: lambda e: BadRequestException(f"Missing required key: {str(e)}"),
    FileNotFoundError: lambda e: NotFoundException(f"File not found: {str(e)}"),
    PermissionError: lambda e: ForbiddenException(str(e)),
    NotImplementedError: lambda e: InternalServerException(f"Not implemented: {str(e)}"),
    TimeoutError: lambda e: GatewayTimeoutException(str(e)),
    ConnectionError: lambda e: ServiceUnavailableException(f"Connection error: {str(e)}"),
}

def handle_exception(
    exception: Exception, 
    operation: str, 
    include_traceback: bool = False,
) -> BaseAPIException:
    """
    Handles exceptions in a standardized way across all API endpoints.
    Converts standard exceptions to our custom exception hierarchy.
    
    Args:
        exception: The exception that was raised
        operation: Description of the operation that failed (e.g., "fetching report")
        include_traceback: Whether to include the full traceback in the log
        
    Returns:
        A BaseAPIException instance suitable for raising
    """
    # Log the exception
    logger.error(f"Error during {operation}: {str(exception)}")
    
    # Include the full traceback for critical errors
    if include_traceback:
        logger.error(traceback.format_exc())
    
    # If it's already a BaseAPIException, return it directly
    if isinstance(exception, BaseAPIException):
        return exception
    
    # Determine the appropriate exception based on the exception class
    exception_class = exception.__class__
    
    # Check if we have a mapping for this exception
    if exception_class in EXCEPTION_MAPPING:
        # Convert to our custom exception
        return EXCEPTION_MAPPING[exception_class](exception)
    
    # Default to internal server error if not mapped
    return InternalServerException(
        message=f"Internal error during {operation}: {str(exception)}",
        details={"exception_type": exception_class.__name__}
    )

def api_error_handler(func: Callable):
    """
    Decorator that standardizes error handling for API endpoints.
    Catches exceptions, converts them to appropriate responses using our custom exceptions.
    
    Usage:
        @router.get("/items/{item_id}")
        @api_error_handler
        async def get_item(item_id: str):
            # Implementation
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            # Get the function name for the error message
            operation = func.__name__
            
            # Convert to our custom exception
            api_exception = handle_exception(e, operation)
            
            # Return standardized error response
            return JSONResponse(
                status_code=api_exception.status_code,
                content=APIResponse(
                    status="error",
                    message=api_exception.detail["message"],
                    code=api_exception.code
                ).dict()
            )
    
    return wrapper

async def api_exception_handler(request: Request, exc: BaseAPIException):
    """
    Global exception handler for FastAPI that handles our custom exceptions.
    Ensures consistent error responses even for unhandled exceptions.
    
    Usage:
        # In main.py
        app.add_exception_handler(BaseAPIException, api_exception_handler)
    """
    logger.error(f"API Exception: {exc.detail}")
    
    return JSONResponse(
        status_code=exc.status_code,
        content=APIResponse(
            status="error",
            message=exc.detail["message"],
            code=exc.code,
            data=exc.details
        ).dict()
    )

def retry_operation(
    operation_func,
    max_retries: int = 3,
    operation_name: str = "API operation",
    retry_exceptions: Optional[Union[Type[Exception], tuple]] = None,
):
    """
    Retry helper that attempts to execute an operation multiple times before giving up.
    
    Args:
        operation_func: The function to execute
        max_retries: Maximum number of retry attempts
        operation_name: Name of the operation for error messages
        retry_exceptions: Exception types that should trigger a retry
        
    Returns:
        The result of the operation if successful
        
    Raises:
        BaseAPIException: If all retry attempts fail
    """
    # Default to retrying on connection and timeout errors
    if retry_exceptions is None:
        retry_exceptions = (ConnectionError, TimeoutError)
    
    retry_count = 0
    last_exception = None
    
    while retry_count < max_retries:
        try:
            return operation_func()
        except retry_exceptions as e:
            retry_count += 1
            last_exception = e
            
            # Log the retry attempt
            logger.warning(
                f"Retry {retry_count}/{max_retries} for {operation_name} after error: {str(e)}"
            )
            
            # If we've reached max retries, break out
            if retry_count >= max_retries:
                break
                
    # If we get here, all retries failed
    api_exception = handle_exception(
        last_exception, 
        f"{operation_name} after {max_retries} retries",
        include_traceback=True
    )
    
    raise api_exception 