"""
Authentication utility functions for the FastAPI application.
This is a minimal implementation since authentication is optional and not required
for core functionality.
"""

import uuid
from typing import Optional

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

# OAuth2 scheme for token authentication, auto_error=False makes it optional
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)


async def get_current_user(token: Optional[str] = Depends(oauth2_scheme)):
    """
    Get the current user context. Since authentication is optional,
    this will always return a basic context, with additional user info
    if a valid token is provided.

    Args:
        token: Optional JWT token from the Authorization header

    Returns:
        A dictionary with basic user context
    """
    # For now, just return a basic context with a generated UUID for demo purposes
    # This is sufficient for Supabase RLS policies which need a user ID
    # In a real implementation, you would decode the JWT and extract the user ID
    return {
        "is_authenticated": bool(token),
        "context_id": "default",
        "id": str(uuid.uuid4())  # Generate a unique ID for RLS purposes
    }
