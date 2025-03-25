"""
Core type definitions for the application.

This module contains fundamental type definitions that are used across
different parts of the application. By placing these here, we avoid circular
import dependencies between modules.
"""

from enum import Enum
from typing import Any, Dict, Generic, Optional, TypeVar
from typing_extensions import TypedDict
from pydantic import BaseModel
from pydantic.generics import GenericModel


class ErrorSeverity(str, Enum):
    """Severity levels for errors"""
    DEBUG = "debug"
    INFO = "info" 
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ErrorDetail(TypedDict, total=False):
    """Details about an error"""
    code: str
    message: str
    params: Dict[str, Any]
    hint: str
    severity: ErrorSeverity


class ErrorResponse(BaseModel):
    """Standard error response format"""
    status: str = "error"
    message: str
    detail: Optional[ErrorDetail] = None
    
    class Config:
        schema_extra: Dict[str, Any] = {
            "example": {
                "status": "error",
                "message": "An error occurred",
                "detail": {
                    "code": "resource_not_found",
                    "message": "The requested resource was not found",
                    "hint": "Check that the ID is correct"
                }
            }
        }


# Generic type for data responses
T = TypeVar('T')

class DataResponse(GenericModel, Generic[T]):
    """Standard data response format"""
    status: str = "success"
    data: T
    
    class Config:
        schema_extra: Dict[str, Any] = {
            "example": {
                "status": "success",
                "data": {}
            }
        } 