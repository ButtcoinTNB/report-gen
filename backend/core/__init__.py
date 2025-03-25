"""
Core package for fundamental application components.

This package contains core types, utilities, and other components that are
used across different parts of the application. By isolating these components
in their own package, we avoid circular import dependencies.
"""

# Export types that should be accessible directly from core package
from .types import ErrorResponse, ErrorDetail, ErrorSeverity, DataResponse

__all__ = [
    "ErrorResponse",
    "ErrorDetail", 
    "ErrorSeverity",
    "DataResponse"
] 