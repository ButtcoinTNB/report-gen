"""
Standardized exception hierarchy for the application.
Ensures consistent error handling and responses across all endpoints.
"""

from fastapi import HTTPException, status
from typing import Any, Dict, Optional

class BaseAPIException(HTTPException):
    """Base exception for all API errors with standardized format"""
    def __init__(
        self, 
        status_code: int, 
        code: str, 
        message: str, 
        details: Any = None,
        headers: Optional[Dict[str, Any]] = None
    ):
        self.code = code
        self.details = details
        # Format the detail dict in a consistent way
        detail = {
            "code": code,
            "message": message
        }
        if details:
            detail["details"] = details
            
        super().__init__(status_code=status_code, detail=detail, headers=headers)


# 4xx Client Error Exceptions

class NotFoundException(BaseAPIException):
    """404 Not Found"""
    def __init__(self, message: str = "Resource not found", details: Any = None):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND, 
            code="NOT_FOUND", 
            message=message, 
            details=details
        )


class FileNotFoundError(NotFoundException):
    """404 File Not Found - Specialized version of NotFoundException"""
    def __init__(self, message: str = "File not found", details: Any = None):
        super().__init__(message=message, details=details)


class ProcessingError(BaseAPIException):
    """422 Processing Error"""
    def __init__(self, message: str = "Error processing request", details: Any = None):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code="PROCESSING_ERROR",
            message=message,
            details=details
        )


class ValidationException(BaseAPIException):
    """422 Validation Error"""
    def __init__(self, message: str = "Validation error", details: Any = None):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, 
            code="VALIDATION_ERROR", 
            message=message, 
            details=details
        )


class BadRequestException(BaseAPIException):
    """400 Bad Request"""
    def __init__(self, message: str = "Invalid request", details: Any = None):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST, 
            code="BAD_REQUEST", 
            message=message, 
            details=details
        )


class AuthenticationException(BaseAPIException):
    """401 Unauthorized"""
    def __init__(self, message: str = "Authentication required", details: Any = None):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            code="UNAUTHORIZED", 
            message=message, 
            details=details
        )


class ForbiddenException(BaseAPIException):
    """403 Forbidden"""
    def __init__(self, message: str = "Access forbidden", details: Any = None):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN, 
            code="FORBIDDEN", 
            message=message, 
            details=details
        )


class ConflictException(BaseAPIException):
    """409 Conflict"""
    def __init__(self, message: str = "Resource conflict", details: Any = None):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT, 
            code="CONFLICT", 
            message=message, 
            details=details
        )


class TooManyRequestsException(BaseAPIException):
    """429 Too Many Requests"""
    def __init__(self, message: str = "Rate limit exceeded", details: Any = None):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, 
            code="RATE_LIMIT_EXCEEDED", 
            message=message, 
            details=details
        )


# 5xx Server Error Exceptions

class InternalServerException(BaseAPIException):
    """500 Internal Server Error"""
    def __init__(self, message: str = "Internal server error", details: Any = None):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            code="INTERNAL_ERROR", 
            message=message, 
            details=details
        )


class ServiceUnavailableException(BaseAPIException):
    """503 Service Unavailable"""
    def __init__(self, message: str = "Service unavailable", details: Any = None):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, 
            code="SERVICE_UNAVAILABLE", 
            message=message, 
            details=details
        )


class GatewayTimeoutException(BaseAPIException):
    """504 Gateway Timeout"""
    def __init__(self, message: str = "Gateway timeout", details: Any = None):
        super().__init__(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT, 
            code="GATEWAY_TIMEOUT", 
            message=message, 
            details=details
        )


# Custom Domain Exceptions

class AIServiceException(BaseAPIException):
    """AI Service Error"""
    def __init__(self, message: str = "AI service error", details: Any = None):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            code="AI_SERVICE_ERROR", 
            message=message, 
            details=details
        )


class FileProcessingException(BaseAPIException):
    """Exception raised when there's an error processing files"""
    def __init__(
        self, 
        message: str = "File processing error", 
        code: str = "file_processing_error",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            status_code=500,
            code=code,
            message=message, 
            details=details
        )


class DatabaseException(BaseAPIException):
    """Database Error"""
    def __init__(self, message: str = "Database error", details: Any = None):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            code="DATABASE_ERROR", 
            message=message, 
            details=details
        ) 