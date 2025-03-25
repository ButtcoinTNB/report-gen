"""
Database connection utilities for the application.
"""

import os
from functools import lru_cache
from typing import Any, Callable

from supabase import create_client, Client
from postgrest._async.client import AsyncPostgrestClient

from config import get_settings

settings = get_settings()

@lru_cache()
def get_supabase() -> Client:
    """
    Get a Supabase client instance.
    Uses environment variables for configuration.
    """
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    
    if not url or not key:
        raise ValueError("Missing Supabase configuration. Please check your environment variables.")
    
    return create_client(url, key)

def get_db() -> Callable[[str], AsyncPostgrestClient]:
    """
    Get a database client factory.
    
    Returns:
        Callable that creates an AsyncPostgrestClient for a given table
    """
    client = get_supabase()
    return client.table

# Export necessary components
__all__ = ["get_db", "get_supabase"] 