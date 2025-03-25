"""
Type definitions for Supabase responses and related types.
"""

from typing import Generic, List, Optional, TypeVar

T = TypeVar('T')

class SupabaseError:
    """Supabase error type"""
    def __init__(self, message: str, code: Optional[str] = None):
        self.message = message
        self.code = code

class APIResponse(Generic[T]):
    """Generic Supabase API response"""
    def __init__(
        self,
        data: Optional[List[T]] = None,
        error: Optional[SupabaseError] = None,
        count: Optional[int] = None
    ):
        self.data = data or []
        self.error = error
        self.count = count

    def __await__(self):
        """Make this response awaitable"""
        yield
        return self

class SingleAPIResponse(Generic[T]):
    """Generic Supabase API response for single record operations"""
    def __init__(
        self,
        data: Optional[T] = None,
        error: Optional[SupabaseError] = None
    ):
        self.data = data
        self.error = error

    def __await__(self):
        """Make this response awaitable"""
        yield
        return self 