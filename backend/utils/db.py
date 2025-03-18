"""
Database utility functions for the FastAPI application.
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from config import settings
from utils.error_handler import logger

# Create SQLAlchemy engine and session factory
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Database dependency
def get_db():
    """
    Get a database session dependency for FastAPI routes.
    
    Yields:
        A SQLAlchemy database session
        
    Notes:
        The session is automatically closed when the request is complete
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database error: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close() 