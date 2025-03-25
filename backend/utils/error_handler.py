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
    ClassVar,
    NoReturn,
)
from typing_extensions import TypedDict

# Import the standard APIResponse model
from api.schemas import APIResponse
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ValidationError

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

T = TypeVar("T")
ErrorType = str
StatusCode = int


class ErrorConfig(TypedDict):
    status_code: int
    message: str
    retryable: bool


class ErrorResponse(BaseModel):
    """Standardized error response model"""

    error_type: ErrorType = Field(description="Type of error that occurred")
    message: str = Field(description="Human-readable error message")
    code: StatusCode = Field(description="HTTP status code")
    retryable: bool = Field(
        default=False, description="Whether the operation can be retried"
    )
    detail: Optional[str] = Field(default=None, description="Additional error details")
    context: Dict[str, Any] = Field(default_factory=dict, description="Error context")
    transaction_id: Optional[str] = Field(
        default=None, description="Transaction ID for tracing"
    )
    request_id: Optional[str] = Field(
        default=None, description="Request ID for tracing"
    )

    ERROR_TYPES: ClassVar[Dict[ErrorType, ErrorConfig]] = {
        "VALIDATION_ERROR": {
            "status_code": status.HTTP_400_BAD_REQUEST,
            "message": "Invalid request parameters",
            "retryable": False,
        },
        "INTERNAL_ERROR": {
            "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
            "message": "An internal error occurred",
            "retryable": True,
        },
    }

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()

    @classmethod
    def format_error(
        cls,
        error_type: ErrorType,
        message: str,
        code: StatusCode,
        retryable: bool = False,
        detail: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        transaction_id: Optional[str] = None,
        request_id: Optional[str] = None,
        log_error: bool = True,
    ) -> Dict[str, Any]:
        if error_type not in cls.ERROR_TYPES:
            error_type = "INTERNAL_ERROR"
            detail = f"Unknown error type: {error_type}"

        error_config = cls.ERROR_TYPES[error_type]
        try:
            error_response = cls(
                error_type=error_type,
                message=str(message),
                code=code or error_config["status_code"],
                retryable=(
                    retryable if retryable is not None else error_config["retryable"]
                ),
                detail=detail,
                context=context or {},
                transaction_id=transaction_id,
                request_id=request_id,
            )
        except ValidationError as e:
            logger.error(f"Error creating error response: {e}")
            error_response = cls(
                error_type="INTERNAL_ERROR",
                message="Error creating error response",
                code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e),
            )

        if log_error:
            logger.error(
                f"Error occurred: {error_response.error_type} - {error_response.message}",
                extra={"error_details": error_response.to_dict()},
            )
            if error_type == "INTERNAL_ERROR":
                logger.error(f"Stack trace: {traceback.format_exc()}")

        return error_response.to_dict()

    @classmethod
    def raise_error(
        cls,
        error_type: ErrorType,
        message: str,
        code: StatusCode = status.HTTP_500_INTERNAL_SERVER_ERROR,
        retryable: bool = False,
        detail: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        transaction_id: Optional[str] = None,
        request_id: Optional[str] = None,
        log_error: bool = True,
    ) -> NoReturn:
        error_dict = cls.format_error(
            error_type=error_type,
            message=message,
            code=code,
            retryable=retryable,
            detail=detail,
            context=context,
            transaction_id=transaction_id,
            request_id=request_id,
            log_error=log_error,
        )
        raise HTTPException(status_code=code, detail=error_dict)

    @classmethod
    def handle_exception(
        cls,
        exception: Exception,
        error_type: ErrorType = "INTERNAL_ERROR",
        message: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        transaction_id: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> JSONResponse:
        error_dict = cls.format_error(
            error_type=error_type,
            message=message or str(exception),
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            retryable=False,
            detail=str(exception),
            context=context or {},
            transaction_id=transaction_id,
            request_id=request_id,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=error_dict
        )


# Convenience function for raising errors
def raise_error(*args, **kwargs):
    """Convenience function for raising standardized errors"""
    return ErrorResponse.raise_error(*args, **kwargs)


# Convenience function for formatting errors
def format_error(*args, **kwargs):
    """Convenience function for formatting standardized errors"""
    return ErrorResponse.format_error(*args, **kwargs)


# Convenience function for handling exceptions
def handle_exception(*args, **kwargs):
    """Convenience function for handling exceptions"""
    return ErrorResponse.handle_exception(*args, **kwargs)


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


def error_handler(func: Callable[..., T]) -> Callable[..., Union[T, JSONResponse]]:
    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Union[T, JSONResponse]:
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            return ErrorResponse.handle_exception(e)

    return wrapper
