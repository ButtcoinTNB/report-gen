"""
Utility for standardized error handling across all API endpoints.
This ensures consistent error responses and logging throughout the application.
"""

import logging
import traceback
import json
from typing import Dict, Any, Optional, Type, Union
from fastapi import HTTPException
from pydantic import ValidationError

# Import the standard APIResponse model
from api.schemas import APIResponse

# Configure logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Error type mapping for common exceptions
ERROR_TYPE_MAPPING = {
    ValidationError: {"status_code": 422, "error_type": "validation_error"},
    ValueError: {"status_code": 400, "error_type": "value_error"},
    KeyError: {"status_code": 400, "error_type": "key_error"},
    FileNotFoundError: {"status_code": 404, "error_type": "file_not_found"},
    PermissionError: {"status_code": 403, "error_type": "permission_error"},
    NotImplementedError: {"status_code": 501, "error_type": "not_implemented"},
    TimeoutError: {"status_code": 504, "error_type": "timeout_error"},
    ConnectionError: {"status_code": 503, "error_type": "connection_error"},
    # Add custom AI service exceptions
    "AIServiceError": {"status_code": 500, "error_type": "ai_service_error"},
    "AIConnectionError": {"status_code": 503, "error_type": "ai_connection_error"},
    "AITimeoutError": {"status_code": 504, "error_type": "ai_timeout_error"},
    "AIResponseError": {"status_code": 500, "error_type": "ai_response_error"},
    "AIParsingError": {"status_code": 422, "error_type": "ai_parsing_error"},
}

def handle_exception(
    exception: Exception, 
    operation: str, 
    default_status_code: int = 500,
    include_traceback: bool = False,
) -> Dict[str, Any]:
    """
    Handles exceptions in a standardized way across all API endpoints.
    
    Args:
        exception: The exception that was raised
        operation: Description of the operation that failed (e.g., "fetching report")
        default_status_code: HTTP status code to use if the exception type isn't mapped
        include_traceback: Whether to include the full traceback in the response
        
    Returns:
        A dictionary with standardized error details
    """
    # Log the exception
    logger.error(f"Error during {operation}: {str(exception)}")
    
    # Include the full traceback for critical errors
    if include_traceback:
        logger.error(traceback.format_exc())
    
    # Determine the error type and status code based on the exception class
    exception_class = exception.__class__
    exception_class_name = exception_class.__name__
    
    # Check for exact match first
    if exception_class in ERROR_TYPE_MAPPING:
        error_info = ERROR_TYPE_MAPPING[exception_class]
    # Then check for class name match (for custom exceptions)
    elif exception_class_name in ERROR_TYPE_MAPPING:
        error_info = ERROR_TYPE_MAPPING[exception_class_name]
    # Default to internal server error if not mapped
    else:
        error_info = {
            "status_code": default_status_code,
            "error_type": "internal_error"
        }
    
    # For AI service errors, use the status_code from the exception if available
    if hasattr(exception, 'status_code') and exception_class_name.startswith('AI'):
        error_info["status_code"] = getattr(exception, 'status_code')
    
    # Create the standard error response using APIResponse model
    error_response = APIResponse(
        status="error",
        message=str(exception),
        code=error_info["error_type"].upper()
    ).dict()
    
    # Add additional fields for debugging
    error_response["operation"] = operation
    error_response["exception_type"] = exception_class_name
    
    # If there's an original exception, include its details
    if hasattr(exception, 'original_exception') and getattr(exception, 'original_exception'):
        original = getattr(exception, 'original_exception')
        error_response["original_error"] = str(original)
        error_response["original_type"] = original.__class__.__name__
    
    # Raise an HTTP exception with the standardized response
    raise HTTPException(
        status_code=error_info["status_code"],
        detail=error_response
    )

def api_error_handler(func):
    """
    Decorator for API route handlers that standardizes error handling.
    Wraps the function in a try-except block and handles exceptions using handle_exception.
    """
    from functools import wraps
    
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            # Call the original function
            result = await func(*args, **kwargs)
            
            # If the result is already an APIResponse, return it as is
            if isinstance(result, APIResponse):
                return result
                
            # If the result is a dict, wrap it in an APIResponse
            if isinstance(result, dict):
                return APIResponse(
                    status="success",
                    data=result
                )
            
            # Otherwise, just return the result (for other response types)
            return result
            
        except Exception as e:
            # Handle any exceptions that occur
            error_details = handle_exception(e, f"{func.__name__}")
            
            # Determine the appropriate status code
            exception_class = e.__class__
            exception_class_name = exception_class.__name__
            
            if exception_class in ERROR_TYPE_MAPPING:
                status_code = ERROR_TYPE_MAPPING[exception_class]["status_code"]
            elif exception_class_name in ERROR_TYPE_MAPPING:
                status_code = ERROR_TYPE_MAPPING[exception_class_name]["status_code"]
            else:
                status_code = 500
                
            # Raise HTTPException with the error details
            raise HTTPException(status_code=status_code, detail=error_details)
    
    return wrapper

def retry_operation(
    operation_func,
    max_retries: int = 3,
    operation_name: str = "API operation",
    retry_exceptions: Optional[Union[Type[Exception], tuple]] = None,
):
    """
    Retries an operation multiple times before giving up.
    
    Args:
        operation_func: The function to execute
        max_retries: Maximum number of retry attempts
        operation_name: Name of the operation for error reporting
        retry_exceptions: Exception types that should trigger a retry
        
    Returns:
        The result of the operation function
        
    Raises:
        HTTPException: If all retries fail
    """
    if retry_exceptions is None:
        retry_exceptions = (ConnectionError, TimeoutError)
    
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            return operation_func()
        except retry_exceptions as e:
            last_exception = e
            logger.warning(
                f"Retry attempt {attempt + 1}/{max_retries} for {operation_name} failed: {str(e)}"
            )
    
    # If we get here, all retries failed
    if last_exception:
        handle_exception(
            last_exception, 
            f"{operation_name} (after {max_retries} retries)"
        )
    else:
        handle_exception(
            Exception(f"All {max_retries} retry attempts failed"), 
            operation_name
        ) 