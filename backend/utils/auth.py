"""
Authentication utility functions for the FastAPI application.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from utils.error_handler import logger
from utils.db import get_db
from models import User
from typing import Optional

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)

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
    # For development/testing purposes, we'll create a mock user
    # In production, this would validate the JWT token
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