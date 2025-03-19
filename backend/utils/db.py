"""
Database utility functions for the FastAPI application.
Using Supabase for all database operations.
"""

from utils.supabase_helper import create_supabase_client
from utils.error_handler import logger

def get_db():
    """
    Get a Supabase client for database operations.
    
    Returns:
        A Supabase client instance
        
    Notes:
        This replaces the SQLAlchemy session for database operations
    """
    try:
        # Create Supabase client without proxy parameter
        return create_supabase_client()
    except Exception as e:
        logger.error(f"Database connection error: {str(e)}")
        raise

# Backwards compatibility function for code that expects a session
def get_db_session():
    """
    Legacy function for code that expects a SQLAlchemy session.
    This should be migrated to use the Supabase client directly.
    
    Returns:
        A Supabase client that can be used for database operations
    """
    return get_db() 