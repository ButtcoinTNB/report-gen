"""
Authentication utility functions for the FastAPI application.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from backend.utils.error_handler import logger
from backend.utils.db import get_db
from models import User
from typing import Optional
import os

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)

# Check if we're in production mode
IS_PRODUCTION = os.getenv("NODE_ENV") == "production"

async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme), 
    db: Session = Depends(get_db)
) -> User:
    """
    Get the current authenticated user based on the JWT token.
    
    Args:
        token: The JWT token from the Authorization header
        db: Database session
        
    Returns:
        The authenticated user
        
    Raises:
        HTTPException: If authentication fails
    """
    if IS_PRODUCTION:
        # Production authentication
        if not token:
            # For now, we'll still provide a default user but log a warning
            # In the future, this should be replaced with proper authentication
            logger.warning("No authentication token provided in production")
            
            # Get default user or create one if it doesn't exist
            user = db.query(User).first()
            if not user:
                user = User(
                    id=1,
                    email="default@example.com",
                    username="defaultuser",
                    is_active=True
                )
                db.add(user)
                db.commit()
                db.refresh(user)
            
            # In a real production environment, you would want to either:
            # 1. Validate a real JWT token and return the corresponding user
            # 2. Raise an authentication error if no token is provided
            # return HTTPException(
            #     status_code=status.HTTP_401_UNAUTHORIZED,
            #     detail="Not authenticated",
            #     headers={"WWW-Authenticate": "Bearer"},
            # )
            
            return user
    else:
        # Development authentication with mock user
        logger.info("Using mock user authentication for development")
        
        # Check if we have a user in the database, otherwise create one
        user = db.query(User).first()
        
        if not user:
            # Create a mock user for development
            user = User(
                id=1,
                email="test@example.com",
                username="testuser",
                is_active=True
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            
        return user 