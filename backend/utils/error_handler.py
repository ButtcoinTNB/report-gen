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
    
    # Get exception traceback
    tb = traceback.format_exc()
    logger.debug(tb)
    
    # Determine the appropriate status code and error type
    error_info = ERROR_TYPE_MAPPING.get(type(exception), {
        "status_code": default_status_code,
        "error_type": "internal_error"
    })
    
    status_code = error_info["status_code"]
    error_type = error_info["error_type"]
    
    # Extract a simple error message string from the exception
    error_message = str(exception)
    # If error is a dictionary, try to simplify it to a string
    if error_message.startswith("{") and error_message.endswith("}"):
        try:
            error_dict = json.loads(error_message)
            if isinstance(error_dict, dict):
                # Try to extract a simple message from the dictionary
                if "detail" in error_dict:
                    error_message = str(error_dict["detail"])
                elif "message" in error_dict:
                    error_message = str(error_dict["message"])
                elif "error" in error_dict:
                    error_message = str(error_dict["error"])
        except:
            # If JSON parsing fails, keep the original message
            pass
    
    # Build error response
    error_response = {
        "status": "error",
        "error_type": error_type,
        "message": error_message,
        "operation": operation
    }
    
    # Include traceback in development environments if requested
    if include_traceback:
        error_response["traceback"] = tb
    
    # Raise HTTPException with a simplified string response if possible
    # This helps prevent complex objects from causing issues in the frontend
    raise HTTPException(
        status_code=status_code,
        detail=error_message if len(error_message) < 500 else f"Error during {operation}"
    )

def api_error_handler(func):
    """
    Decorator for API endpoint functions to standardize error handling.
    
    Example usage:
    @router.get("/endpoint")
    @api_error_handler
    async def my_endpoint():
        # This function's exceptions will be handled properly
        pass
    """
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except HTTPException:
            # Re-raise HTTP exceptions as they're already properly formatted
            raise
        except Exception as e:
            # Get function name for better error reporting
            operation = f"{func.__name__}"
            handle_exception(e, operation)
    
    # Return wrapper with the same name as the original function
    wrapper.__name__ = func.__name__
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