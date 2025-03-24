from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from typing import Union, Dict, Any
import traceback

# Use imports with fallbacks for better compatibility across environments
try:
    # First try imports without 'backend.' prefix (for Render)
    from utils.monitoring import logger
except ImportError:
    # Fallback to imports with 'backend.' prefix (for local dev)
    from backend.utils.monitoring import logger

class ErrorResponse:
    def __init__(
        self,
        message: str,
        code: str = None,
        details: Dict[str, Any] = None,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    ):
        self.message = message
        self.code = code or "INTERNAL_ERROR"
        self.details = details or {}
        self.status_code = status_code
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            "error": {
                "message": self.message,
                "code": self.code,
                "details": self.details
            }
        }

async def error_handler_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as exc:
        return await handle_exception(exc, request)

async def handle_exception(exc: Exception, request: Request) -> JSONResponse:
    """Handle different types of exceptions and return appropriate responses"""
    
    # Handle validation errors
    if isinstance(exc, RequestValidationError):
        return validation_exception_handler(exc)
        
    # Handle HTTP exceptions
    if isinstance(exc, StarletteHTTPException):
        return http_exception_handler(exc)
        
    # Handle all other exceptions
    return internal_exception_handler(exc, request)

def validation_exception_handler(exc: RequestValidationError) -> JSONResponse:
    """Handle request validation errors"""
    errors = []
    for error in exc.errors():
        errors.append({
            "field": " -> ".join(str(x) for x in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })
        
    response = ErrorResponse(
        message="Validation error",
        code="VALIDATION_ERROR",
        details={"errors": errors},
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
    )
    
    logger.warning(f"Validation error: {errors}")
    return JSONResponse(
        status_code=response.status_code,
        content=response.to_dict()
    )

def http_exception_handler(exc: StarletteHTTPException) -> JSONResponse:
    """Handle HTTP exceptions"""
    response = ErrorResponse(
        message=str(exc.detail),
        code=f"HTTP_{exc.status_code}",
        status_code=exc.status_code
    )
    
    logger.warning(f"HTTP error {exc.status_code}: {exc.detail}")
    return JSONResponse(
        status_code=response.status_code,
        content=response.to_dict()
    )

def internal_exception_handler(exc: Exception, request: Request) -> JSONResponse:
    """Handle unexpected internal errors"""
    # Log the full error with stack trace
    logger.error(
        f"Internal error processing request {request.method} {request.url}: {str(exc)}",
        exc_info=True
    )
    
    # In development, include stack trace
    details = {}
    if request.app.debug:
        details["stack_trace"] = traceback.format_exc()
    
    response = ErrorResponse(
        message="An unexpected error occurred",
        code="INTERNAL_ERROR",
        details=details
    )
    
    return JSONResponse(
        status_code=response.status_code,
        content=response.to_dict()
    )

# Error code mapping for common scenarios
ERROR_CODES = {
    "VALIDATION_ERROR": status.HTTP_422_UNPROCESSABLE_ENTITY,
    "NOT_FOUND": status.HTTP_404_NOT_FOUND,
    "UNAUTHORIZED": status.HTTP_401_UNAUTHORIZED,
    "FORBIDDEN": status.HTTP_403_FORBIDDEN,
    "RATE_LIMIT_EXCEEDED": status.HTTP_429_TOO_MANY_REQUESTS,
    "INTERNAL_ERROR": status.HTTP_500_INTERNAL_SERVER_ERROR,
    "BAD_REQUEST": status.HTTP_400_BAD_REQUEST,
    "SERVICE_UNAVAILABLE": status.HTTP_503_SERVICE_UNAVAILABLE
} 