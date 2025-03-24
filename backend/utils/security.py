import os
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import jwt
from fastapi import HTTPException, Request

# Secret key for JWT validation - should be in environment variables
JWT_SECRET = os.environ.get("JWT_SECRET", "your-secret-key-for-development-only")


def get_user_from_request(request: Request) -> Optional[Dict[str, Any]]:
    """
    Extract and validate user from request headers or cookies
    Returns user info or None if no valid user found
    """
    # Get authorization header
    auth_header = request.headers.get("Authorization")

    # Try to get user from Authorization header (Bearer token)
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.replace("Bearer ", "")
        return validate_token(token)

    # Try to get user from cookies
    token = request.cookies.get("access_token")
    if token:
        return validate_token(token)

    # Try to get user ID from query parameters (less secure, use only for specific cases)
    user_id = request.query_params.get("user_id")
    if user_id:
        # This is a simplified approach. In production, you would validate this against a database
        return {"id": user_id, "source": "query_param", "role": "user"}

    # No user information found
    return None


def validate_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Validate JWT token and return user information
    """
    try:
        # Decode and validate the token
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])

        # Check if token is expired
        if "exp" in payload and datetime.utcnow() > datetime.fromtimestamp(
            payload["exp"]
        ):
            return None

        # Return user information from payload
        return {
            "id": payload.get("sub"),
            "email": payload.get("email"),
            "role": payload.get("role", "user"),
            "source": "token",
        }
    except jwt.PyJWTError:
        # Token is invalid
        return None


def validate_user(request: Request, required: bool = True) -> Optional[Dict[str, Any]]:
    """
    Validate user from request and optionally raise exception if no valid user found

    Args:
        request: The FastAPI request object
        required: Whether to raise an exception if no valid user found

    Returns:
        User information dictionary or None

    Raises:
        HTTPException: If required=True and no valid user found
    """
    user = get_user_from_request(request)

    if required and not user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token

    Args:
        data: Data to encode in the token
        expires_delta: Optional expiration time

    Returns:
        JWT token as string
    """
    to_encode = data.copy()

    # Set expiration time
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        # Default to 15 minutes
        expire = datetime.utcnow() + timedelta(minutes=15)

    to_encode.update({"exp": expire})

    # Create JWT token
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm="HS256")

    return encoded_jwt


def has_permission(user: Dict[str, Any], permission: str) -> bool:
    """
    Check if user has a specific permission

    Args:
        user: User information dictionary
        permission: Permission to check

    Returns:
        Boolean indicating if user has permission
    """
    # For simplicity, admins have all permissions
    if user.get("role") == "admin":
        return True

    # Check specific permissions (this would typically be more complex)
    user_permissions = user.get("permissions", [])

    return permission in user_permissions
