"""
Authentication service for handling user authentication with Supabase.
"""

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

# Use imports with fallbacks for better compatibility across environments
try:
    # First try imports without 'backend.' prefix (for Render)
    from utils.supabase_client import supabase
except ImportError:
    # Fallback to imports with 'backend.' prefix (for local dev)
    from backend.utils.supabase_client import supabase

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """
    Get the current authenticated user from the JWT token.
    This function is used as a dependency in protected routes.
    """
    try:
        # Get the JWT token from the Authorization header
        token = credentials.credentials

        # Verify the token and get user information
        user = supabase.get_client().auth.get_user(token)

        if not user:
            raise HTTPException(
                status_code=401, detail="Invalid authentication credentials"
            )

        return user.user
    except Exception as e:
        raise HTTPException(
            status_code=401, detail=f"Invalid authentication credentials: {str(e)}"
        )
