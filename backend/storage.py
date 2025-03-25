"""
Storage utilities for Supabase integration.
"""

import os
from functools import lru_cache

from supabase import create_client
from storage3 import SyncStorageClient

from config import get_settings

settings = get_settings()

@lru_cache()
def get_storage() -> SyncStorageClient:
    """
    Get a Supabase storage client instance.
    Uses environment variables for configuration.
    """
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    
    if not url or not key:
        raise ValueError("Missing Supabase configuration. Please check your environment variables.")
    
    return create_client(url, key).storage 