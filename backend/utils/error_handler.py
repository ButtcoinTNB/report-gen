"""
Utility for standardized error handling across all API endpoints.
This ensures consistent error responses and logging throughout the application.
"""

import logging
import traceback
from functools import wraps
from typing import Any, Callable, Dict, Optional, Type, Union

# Import the standard APIResponse model
from api.schemas import APIResponse
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError

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
EXCEPTION_MAPPING = {
    ValidationError: lambda e: ValidationException(str(e), details=str(e.errors())),
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


class ErrorResponse(BaseModel):
    """Standardized error response model"""

    status: str = "error"
    message: str
    code: int
    detail: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    transactionId: Optional[str] = None
    request_id: Optional[str] = None
    retryable: bool = False
    docs_link: Optional[str] = None


class ErrorCodes:
    """Error codes for the application"""

    VALIDATION_ERROR = "validation_error"
    NOT_FOUND = "not_found"
    UNAUTHORIZED = "unauthorized"
    FORBIDDEN = "forbidden"
    INTERNAL_ERROR = "internal_error"
    NETWORK_ERROR = "network_error"
    EXTERNAL_API_ERROR = "external_api_error"
    DATABASE_ERROR = "database_error"
    TIMEOUT_ERROR = "timeout_error"
    STORAGE_ERROR = "storage_error"


class ErrorHandler:
    """
    Centralized error handling utility for standardized error responses
    """

    # Error categories with default settings
    ERROR_TYPES = {
        "authentication": {
            "status_code": status.HTTP_401_UNAUTHORIZED,
            "retryable": False,
            "message": "Authentication failed",
        },
        "authorization": {
            "status_code": status.HTTP_403_FORBIDDEN,
            "retryable": False,
            "message": "You don't have permission to perform this action",
        },
        "not_found": {
            "status_code": status.HTTP_404_NOT_FOUND,
            "retryable": False,
            "message": "The requested resource was not found",
        },
        "validation": {
            "status_code": status.HTTP_422_UNPROCESSABLE_ENTITY,
            "retryable": False,
            "message": "Validation error",
        },
        "rate_limit": {
            "status_code": status.HTTP_429_TOO_MANY_REQUESTS,
            "retryable": True,
            "message": "Rate limit exceeded",
        },
        "service_unavailable": {
            "status_code": status.HTTP_503_SERVICE_UNAVAILABLE,
            "retryable": True,
            "message": "Service temporarily unavailable",
        },
        "timeout": {
            "status_code": status.HTTP_504_GATEWAY_TIMEOUT,
            "retryable": True,
            "message": "Operation timed out",
        },
        "internal": {
            "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
            "retryable": False,
            "message": "Internal server error",
        },
        "dependency": {
            "status_code": status.HTTP_503_SERVICE_UNAVAILABLE,
            "retryable": True,
            "message": "Dependency failure",
        },
        "conflict": {
            "status_code": status.HTTP_409_CONFLICT,
            "retryable": False,
            "message": "Resource conflict",
        },
        "cancelled": {
            "status_code": HTTP_499_CLIENT_CLOSED_REQUEST,
            "retryable": False,
            "message": "Operation cancelled",
        },
        "bad_request": {
            "status_code": status.HTTP_400_BAD_REQUEST,
            "retryable": False,
            "message": "Bad request",
        },
    }

    @classmethod
    def raise_error(
        cls,
        error_type: str,
        message: Optional[str] = None,
        detail: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        transaction_id: Optional[str] = None,
        request_id: Optional[str] = None,
        retryable: Optional[bool] = None,
        log_error: bool = True,
    ) -> None:
        """
        Raise a standardized HTTP exception

        Args:
            error_type: The type of error (must be in ERROR_TYPES)
            message: Override for the default error message
            detail: Additional details about the error
            context: Contextual information about the error
            transaction_id: ID of the transaction for tracing
            request_id: ID of the request for tracing
            retryable: Override whether the error is retryable
            log_error: Whether to log the error

        Raises:
            HTTPException: Standardized error response
        """
        if error_type not in cls.ERROR_TYPES:
            error_type = "internal"
            detail = f"Unknown error type: {error_type}"

        error_config = cls.ERROR_TYPES[error_type]

        # Prepare the error response
        error_response = ErrorResponse(
            status="error",
            message=message or error_config["message"],
            code=error_config["status_code"],
            detail=detail,
            context=context or {},
            transactionId=transaction_id,
            request_id=request_id,
            retryable=retryable if retryable is not None else error_config["retryable"],
        )

        # Log the error if needed
        if log_error:
            log_context = {
                "error_type": error_type,
                "status_code": error_config["status_code"],
                "transaction_id": transaction_id,
                "request_id": request_id,
                "context": context,
            }

            logger.error(f"Error: {error_response.message}", extra=log_context)

            if detail:
                logger.error(f"Detail: {detail}")

            # Add stack trace for internal errors
            if error_type == "internal":
                logger.error(f"Stack trace: {traceback.format_exc()}")

        # Raise the HTTP exception
        raise HTTPException(
            status_code=error_config["status_code"], detail=error_response.dict()
        )

    @classmethod
    def format_error(
        cls,
        error_type: str,
        message: Optional[str] = None,
        detail: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        transaction_id: Optional[str] = None,
        request_id: Optional[str] = None,
        retryable: Optional[bool] = None,
        log_error: bool = True,
    ) -> Dict[str, Any]:
        """
        Format a standardized error response without raising an exception

        Args:
            error_type: The type of error (must be in ERROR_TYPES)
            message: Override for the default error message
            detail: Additional details about the error
            context: Contextual information about the error
            transaction_id: ID of the transaction for tracing
            request_id: ID of the request for tracing
            retryable: Override whether the error is retryable
            log_error: Whether to log the error

        Returns:
            Dict[str, Any]: Standardized error response
        """
        if error_type not in cls.ERROR_TYPES:
            error_type = "internal"
            detail = f"Unknown error type: {error_type}"

        error_config = cls.ERROR_TYPES[error_type]

        # Prepare the error response
        error_response = ErrorResponse(
            status="error",
            message=message or error_config["message"],
            code=error_config["status_code"],
            detail=detail,
            context=context or {},
            transactionId=transaction_id,
            request_id=request_id,
            retryable=retryable if retryable is not None else error_config["retryable"],
        )

        # Log the error if needed
        if log_error:
            log_context = {
                "error_type": error_type,
                "status_code": error_config["status_code"],
                "transaction_id": transaction_id,
                "request_id": request_id,
                "context": context,
            }

            logger.error(f"Error: {error_response.message}", extra=log_context)

            if detail:
                logger.error(f"Detail: {detail}")

        return error_response.dict()

    @classmethod
    def handle_exception(
        cls,
        exception: Exception,
        error_type: str = "internal",
        message: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        transaction_id: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> None:
        """
        Handle an exception by raising a standardized HTTP exception

        Args:
            exception: The exception to handle
            error_type: The type of error
            message: Override for the default error message
            context: Contextual information about the error
            transaction_id: ID of the transaction for tracing
            request_id: ID of the request for tracing

        Raises:
            HTTPException: Standardized error response
        """
        # If it's already an HTTPException, extract the status code and detail
        if isinstance(exception, HTTPException):
            status_code = exception.status_code

            # Try to parse the detail if it's a dictionary
            if isinstance(exception.detail, dict) and "message" in exception.detail:
                detail = exception.detail.get("message")
            else:
                detail = str(exception.detail)

            # Map HTTP status code to error type
            for err_type, config in cls.ERROR_TYPES.items():
                if config["status_code"] == status_code:
                    error_type = err_type
                    break
        else:
            detail = str(exception)

        cls.raise_error(
            error_type=error_type,
            message=message,
            detail=detail,
            context=context,
            transaction_id=transaction_id,
            request_id=request_id,
            log_error=True,
        )


# Convenience function for raising errors
def raise_error(*args, **kwargs):
    """Convenience function for raising standardized errors"""
    return ErrorHandler.raise_error(*args, **kwargs)


# Convenience function for formatting errors
def format_error(*args, **kwargs):
    """Convenience function for formatting standardized errors"""
    return ErrorHandler.format_error(*args, **kwargs)


# Convenience function for handling exceptions
def handle_exception(*args, **kwargs):
    """Convenience function for handling exceptions"""
    return ErrorHandler.handle_exception(*args, **kwargs)


# Original error handler (kept for backward compatibility)
def legacy_handle_exception(
    exception: Exception, request: Request, error_info: Dict[str, Any] = None
) -> JSONResponse:
    """
    Handle exceptions and return standardized error responses

    Args:
        exception: The exception to handle
        request: The FastAPI request object
        error_info: Additional error information

    Returns:
        JSONResponse: Standardized error response
    """
    # ... rest of existing legacy function ...


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
            api_exception = extended_handle_exception(e, operation)

            # Return standardized error response
            return JSONResponse(
                status_code=api_exception.status_code,
                content=APIResponse(
                    status="error",
                    message=api_exception.detail["message"],
                    code=api_exception.code,
                ).dict(),
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
            data=exc.details,
        ).dict(),
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
    api_exception = extended_handle_exception(
        last_exception,
        f"{operation_name} after {max_retries} retries",
        include_traceback=True,
    )

    raise api_exception
