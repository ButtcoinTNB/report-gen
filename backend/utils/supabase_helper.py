"""
Utility functions for working with Supabase.
This module provides helper functions to create Supabase clients without proxy-related issues.
"""

import os
import time
from contextlib import contextmanager
from typing import Optional
from supabase import create_client, Client
from config import settings
from utils.error_handler import logger

# Define specific exceptions for better error handling
class SupabaseConnectionError(Exception):
    """Raised when there's an issue connecting to Supabase"""
    pass

class SupabaseConfigError(Exception):
    """Raised when there's an issue with Supabase configuration"""
    pass

def create_supabase_client(max_retries: int = 3, retry_delay: float = 1.0) -> Client:
    """
    Creates a Supabase client with proxy environment variables temporarily unset.
    Implements retry logic for better reliability.
    
    Args:
        max_retries: Maximum number of connection attempts
        retry_delay: Delay between retries in seconds
    
    Returns:
        A Supabase client instance
        
    Raises:
        SupabaseConfigError: If Supabase URL or key is missing
        SupabaseConnectionError: If connection fails after retries
    """
    # Check if Supabase is properly configured
    if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
        logger.error("Supabase URL or key is missing in configuration")
        raise SupabaseConfigError("Supabase URL or key is missing. Please check your environment variables.")
    
    # Temporarily unset any proxy environment variables that might cause issues
    proxy_env_backup = {}
    for var in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy']:
        if var in os.environ:
            proxy_env_backup[var] = os.environ[var]
            del os.environ[var]
    
    # Try to create the client with retries
    retry_count = 0
    last_error = None
    
    while retry_count < max_retries:
        try:
            # Create client with minimal configuration - no proxy settings
            supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
            
            # Test the connection with a simple query to validate it works
            try:
                # Simple ping query to verify connection works
                supabase.table("reports").select("count", count="exact").limit(1).execute()
                return supabase
            except Exception as test_error:
                # If test query fails, it might be a temporary issue or auth problem
                logger.warning(f"Supabase connection test failed: {str(test_error)}")
                raise
                
        except Exception as e:
            last_error = e
            retry_count += 1
            if retry_count < max_retries:
                # Log and wait before retry
                logger.warning(f"Supabase connection failed (attempt {retry_count}/{max_retries}): {str(e)}")
                time.sleep(retry_delay)
            else:
                # Final attempt failed
                logger.error(f"Failed to create Supabase client after {max_retries} attempts: {str(e)}")
                break
        finally:
            # Restore environment variables regardless of success/failure
            if proxy_env_backup:
                for var, value in proxy_env_backup.items():
                    os.environ[var] = value
    
    # If we get here, all retries failed
    error_msg = f"Failed to connect to Supabase after {max_retries} attempts"
    if last_error:
        error_msg += f": {str(last_error)}"
    raise SupabaseConnectionError(error_msg)

@contextmanager
def supabase_client_context():
    """
    Context manager for creating and using a Supabase client with proxy environment variables
    temporarily unset.
    
    Yields:
        A Supabase client instance
        
    Example:
        ```
        with supabase_client_context() as supabase:
            # Use supabase client here
            data = supabase.table('reports').select('*').execute()
        ```
    """
    client = None
    try:
        client = create_supabase_client()
        yield client
    finally:
        # No need to close the client, but we'll log any failures
        if client is None:
            logger.warning("Supabase client context manager failed to create client")

def get_supabase_storage_url(bucket: str, path: str) -> Optional[str]:
    """
    Get the public URL for a file in Supabase Storage
    
    Args:
        bucket: The storage bucket name
        path: The path to the file in storage
        
    Returns:
        The public URL of the file, or None if there's an error
    """
    try:
        supabase = create_supabase_client()
        return supabase.storage.from_(bucket).get_public_url(path)
    except Exception as e:
        logger.error(f"Error getting storage URL for {bucket}/{path}: {str(e)}")
        return None 