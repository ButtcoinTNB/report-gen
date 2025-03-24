"""
Authentication utility functions for the FastAPI application.
This is a minimal implementation since authentication is optional and not required
for core functionality.
"""

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
    # For now, just return a basic context
    # This can be expanded later if we implement full authentication
    return {"is_authenticated": bool(token), "context_id": "default"}
