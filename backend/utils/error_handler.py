"""
Utility for standardized error handling across all API endpoints.
This ensures consistent error responses and logging throughout the application.
"""

import logging
import traceback
from functools import wraps
from typing import (
    Any,
    Callable,
    Dict,
    Optional,
    TypeVar,
    Union,
    Type,
    NoReturn,
    cast,
    Awaitable,
)

# Import from core package - using the correct path with backend as root
from core.types import ErrorResponse, ErrorDetail, ErrorSeverity

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError

# Import our custom exceptions
from utils.exceptions import (
    BadRequestException,
    BaseAPIException,
    ForbiddenException,
    GatewayTimeoutException,
    InternalServerException,
    NotFoundException,
    ServiceUnavailableException,
    ValidationException,
)

# Configure logger
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Define custom status code that's not in starlette.status
HTTP_499_CLIENT_CLOSED_REQUEST = 499

# Exception mapping for converting standard exceptions to our custom exceptions
EXCEPTION_MAPPING: Dict[Type[Exception], Callable[[Exception], BaseAPIException]] = {
    ValidationError: lambda e: ValidationException(str(e), details=str(getattr(e, 'errors', lambda: 'Validation error')())),
    ValueError: lambda e: BadRequestException(str(e)),
    KeyError: lambda e: BadRequestException(f"Missing required key: {str(e)}"),
    FileNotFoundError: lambda e: NotFoundException(f"File not found: {str(e)}"),
    PermissionError: lambda e: ForbiddenException(str(e)),
    NotImplementedError: lambda e: InternalServerException(
        f"Not implemented: {str(e)}"
    ),
    TimeoutError: lambda e: GatewayTimeoutException(str(e)),
    ConnectionError: lambda e: ServiceUnavailableException(
        f"Connection error: {str(e)}"
    ),
}

T = TypeVar("T")

# Convenience function for raising errors
def raise_error(
    message: str,
    detail: Optional[ErrorDetail] = None,
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
) -> NoReturn:
    """Raise an HTTP exception with a standardized error response"""
    error_response = ErrorResponse(message=message, detail=detail)
    raise HTTPException(status_code=status_code, detail=error_response.model_dump())


# Convenience function for handling exceptions
def handle_exception(
    exception: Exception,
    message: Optional[str] = None,
) -> JSONResponse:
    """
    Handle an exception and return a standardized error response

    Args:
        exception: The exception to handle
        message: Custom message to use instead of the exception message

    Returns:
        JSONResponse with standardized error format
    """
    error_detail = ErrorDetail(
        code="internal_error",
        message=str(exception),
        severity=ErrorSeverity.ERROR
    )
    
    error_response = ErrorResponse(
        message=message or str(exception),
        detail=error_detail
    )
    
    logger.error(f"Error occurred: {str(exception)}")
    logger.error(f"Stack trace: {traceback.format_exc()}")
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response.model_dump()
    )


def extended_handle_exception(
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
        details={"exception_type": exception_class.__name__},
    )


def api_error_handler(func: Callable[..., Any]):
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
    async def wrapper(*args: Any, **kwargs: Any):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            # Get the function name for the error message
            operation = func.__name__

            # Convert to our custom exception
            api_exception = extended_handle_exception(e, operation)
            
            # Extract the error message - api_exception.detail is a dict
            detail_dict = api_exception.detail if isinstance(api_exception.detail, dict) else {}
            error_message = detail_dict.get("message", str(e)) if detail_dict else str(e)
            
            # Create error detail with proper typing
            error_detail: ErrorDetail = {
                "code": api_exception.code,
                "message": error_message,
                "severity": ErrorSeverity.ERROR
            }
            
            # Create an error response using our core ErrorResponse type
            error_response = ErrorResponse(
                message=error_message,
                detail=error_detail
            )

            # Return standardized error response
            return JSONResponse(
                status_code=api_exception.status_code,
                content=error_response.model_dump()
            )

    return wrapper


async def api_exception_handler(request: Request, exc: BaseAPIException) -> JSONResponse:
    """
    Global exception handler for FastAPI that handles our custom exceptions.
    Ensures consistent error responses even for unhandled exceptions.

    Usage:
        # In main.py
        app.add_exception_handler(BaseAPIException, api_exception_handler)
    """
    logger.error(f"API Exception: {exc.detail}")
    
    # Extract the error message - exc.detail is a dict
    detail_dict = exc.detail if isinstance(exc.detail, dict) else {}
    error_message = detail_dict.get("message", "An error occurred") if detail_dict else "An error occurred"
    
    # Create error detail with proper typing
    error_detail: ErrorDetail = {
        "code": exc.code,
        "message": error_message,
        "severity": ErrorSeverity.ERROR
    }
    
    # Add any additional details if available
    if exc.details:
        error_detail["params"] = exc.details
    
    # Create a standardized error response
    error_response = ErrorResponse(
        message=error_message,
        detail=error_detail
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump()
    )


def retry_operation(
    operation_func: Callable[[], Any],
    max_retries: int = 3,
    operation_name: str = "API operation",
    retry_exceptions: Optional[Union[Type[Exception], tuple[Type[Exception], ...]]] = None,
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
    last_exception: Optional[Exception] = None

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
    if last_exception is not None:
        api_exception = extended_handle_exception(
            last_exception,
            f"{operation_name} after {max_retries} retries",
            include_traceback=True,
        )
        raise api_exception
    else:
        # This should never happen, but just in case
        raise InternalServerException(f"Failed to execute {operation_name} after {max_retries} retries")


# Type for functions that can be synchronous or asynchronous
SyncOrAsyncCallable = Callable[..., Union[T, Awaitable[T]]]

def error_handler(func: SyncOrAsyncCallable[T]) -> Callable[..., Awaitable[Union[T, JSONResponse]]]:
    """
    Decorator for function-based views that handles exceptions and returns standardized error responses.
    
    Args:
        func: The function to wrap with error handling
        
    Returns:
        A wrapped function that handles exceptions
    """
    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Union[T, JSONResponse]:
        try:
            result = func(*args, **kwargs)
            # If it's awaitable, await it
            if hasattr(result, '__await__'):
                return await cast(Awaitable[T], result)
            return cast(T, result)
        except Exception as e:
            return handle_exception(e)

    return wrapper
