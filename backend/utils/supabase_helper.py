"""
Utility functions for working with Supabase.
This module provides helper functions to create Supabase clients with proper connection pooling.
"""

import logging
import os
import threading
import time
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime, timedelta
from functools import lru_cache
from typing import Dict, Optional, Tuple

from supabase import Client, create_client

# Use imports with fallbacks for better compatibility across environments
try:
    # First try imports without 'backend.' prefix (for Render)
    from config import get_settings, settings
    from utils.error_handler import logger
except ImportError:
    # Fallback to imports with 'backend.' prefix (for local dev)
    from backend.config import get_settings, settings
    from backend.utils.error_handler import logger

# Configure logger
logger = logging.getLogger(__name__)


# Define specific exceptions for better error handling
class SupabaseConnectionError(Exception):
    """Raised when there's an issue connecting to Supabase"""

    pass


class SupabaseConfigError(Exception):
    """Raised when there's an issue with Supabase configuration"""

    pass


# Connection pool settings
MAX_CONNECTIONS = 10
MAX_RETRIES = 3
RETRY_DELAY = 1.0
CONNECTION_TIMEOUT = 30.0
CONNECTION_EXPIRY_SECONDS = 300  # 5 minutes


# Thread-safe connection pool with LRU eviction and expiration
class SupabaseConnectionPool:
    """Thread-safe connection pool for Supabase clients with LRU eviction and expiration"""

    def __init__(
        self, max_size=MAX_CONNECTIONS, expiry_seconds=CONNECTION_EXPIRY_SECONDS
    ):
        """
        Initialize the connection pool.

        Args:
            max_size: Maximum number of connections to keep in the pool
            expiry_seconds: Time in seconds after which a connection is considered stale
        """
        self._lock = threading.RLock()
        self._pool: Dict[str, Tuple[Client, datetime]] = (
            {}
        )  # {key: (client, last_used_time)}
        self._max_size = max_size
        self._expiry_seconds = expiry_seconds
        logger.info(
            f"Initialized Supabase connection pool: max_size={max_size}, expiry={expiry_seconds}s"
        )

    def get(self, key: str) -> Optional[Client]:
        """
        Get a client from the pool.

        Args:
            key: The unique key for the client

        Returns:
            The client if found in the pool, None otherwise
        """
        with self._lock:
            if key in self._pool:
                client, _ = self._pool[key]
                # Update last used time
                self._pool[key] = (client, datetime.now())
                return client
            return None

    def put(self, key: str, client: Client) -> None:
        """
        Add a client to the pool, evicting the least recently used client if necessary.

        Args:
            key: The unique key for the client
            client: The Supabase client to add to the pool
        """
        with self._lock:
            # Check if we need to evict
            if len(self._pool) >= self._max_size and key not in self._pool:
                self._evict_oldest()

            self._pool[key] = (client, datetime.now())

    def _evict_oldest(self) -> None:
        """Evict the least recently used client from the pool"""
        if not self._pool:
            return

        oldest_key = None
        oldest_time = None

        for key, (_, last_used) in self._pool.items():
            if oldest_time is None or last_used < oldest_time:
                oldest_key = key
                oldest_time = last_used

        if oldest_key:
            logger.debug(
                f"Evicting oldest Supabase connection: last used {oldest_time}"
            )
            del self._pool[oldest_key]

    def cleanup_expired(self) -> int:
        """
        Remove expired connections from the pool.

        Returns:
            Number of connections removed
        """
        with self._lock:
            now = datetime.now()
            expiration = timedelta(seconds=self._expiry_seconds)

            expired_keys = [
                key
                for key, (_, last_used) in self._pool.items()
                if now - last_used > expiration
            ]

            for key in expired_keys:
                logger.debug(f"Removing expired Supabase connection: {key}")
                del self._pool[key]

            return len(expired_keys)

    def clear(self) -> None:
        """Remove all connections from the pool"""
        with self._lock:
            self._pool.clear()

    def size(self) -> int:
        """Get the current size of the pool"""
        with self._lock:
            return len(self._pool)


# Initialize the global connection pool
_connection_pool = SupabaseConnectionPool(max_size=MAX_CONNECTIONS)


@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    """
    Get or create a Supabase client with connection pooling.

    Returns:
        A Supabase client instance from the pool

    Raises:
        SupabaseConfigError: If Supabase URL or key is missing
        SupabaseConnectionError: If connection fails after retries
    """
    client_key = f"{settings.SUPABASE_URL}:{settings.SUPABASE_KEY}"

    # Check if client already exists in pool
    client = _connection_pool.get(client_key)
    if client:
        logger.debug("Using existing Supabase client from pool")
        return client

    # Check if Supabase is properly configured
    if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
        logger.error("Supabase URL or key is missing in configuration")
        raise SupabaseConfigError(
            "Supabase URL or key is missing. Please check your environment variables."
        )

    # Temporarily unset any proxy environment variables that might cause issues
    proxy_env_backup = {}
    for var in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"]:
        if var in os.environ:
            proxy_env_backup[var] = os.environ[var]
            del os.environ[var]

    # Try to create the client with retries
    retry_count = 0
    last_error = None

    while retry_count < MAX_RETRIES:
        try:
            # Create client with minimal configuration - no proxy settings
            supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

            # Test the connection with a simple query to validate it works
            try:
                # Simple ping query to verify connection works
                supabase.table("reports").select("count", count="exact").limit(
                    1
                ).execute()

                # Add to pool and return
                _connection_pool.put(client_key, supabase)
                return supabase
            except Exception as test_error:
                # If test query fails, it might be a temporary issue or auth problem
                logger.warning(f"Supabase connection test failed: {str(test_error)}")
                raise

        except Exception as e:
            last_error = e
            retry_count += 1
            if retry_count < MAX_RETRIES:
                # Log and wait before retry
                logger.warning(
                    f"Supabase connection failed (attempt {retry_count}/{MAX_RETRIES}): {str(e)}"
                )
                time.sleep(RETRY_DELAY * retry_count)  # Progressive backoff
            else:
                # Final attempt failed
                logger.error(
                    f"Failed to create Supabase client after {MAX_RETRIES} attempts: {str(e)}"
                )
                break
        finally:
            # Restore environment variables regardless of success/failure
            if proxy_env_backup:
                for var, value in proxy_env_backup.items():
                    os.environ[var] = value

    # If we get here, all retries failed
    error_msg = f"Failed to connect to Supabase after {MAX_RETRIES} attempts"
    if last_error:
        error_msg += f": {str(last_error)}"
    raise SupabaseConnectionError(error_msg)


@contextmanager
def supabase_client_context():
    """
    Context manager for getting a Supabase client from the pool.

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
        client = get_supabase_client()
        yield client
    except Exception as e:
        logger.error(f"Error using Supabase client: {str(e)}")
        raise
    finally:
        # No explicit cleanup needed as we're managing the pool centrally
        pass


@asynccontextmanager
async def async_supabase_client_context():
    """
    Async context manager for getting a Supabase client from the pool.

    Yields:
        A Supabase client instance

    Example:
        ```
        async with async_supabase_client_context() as supabase:
            # Use supabase client here
            data = await supabase.table('reports').select('*').execute()
        ```
    """
    client = None
    try:
        client = get_supabase_client()
        yield client
    except Exception as e:
        logger.error(f"Error using Supabase client: {str(e)}")
        raise
    finally:
        # No explicit cleanup needed as we're managing the pool centrally
        pass


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
        with supabase_client_context() as supabase:
            return supabase.storage.from_(bucket).get_public_url(path)
    except Exception as e:
        logger.error(f"Error getting storage URL for {bucket}/{path}: {str(e)}")
        return None


def create_supabase_client() -> Client:
    """
    Create and return a configured Supabase client.

    Returns:
        Supabase Client instance

    Raises:
        Exception: If Supabase configuration is missing or invalid
    """
    settings = get_settings()

    if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
        raise Exception("Supabase configuration is missing")

    try:
        return create_client(
            supabase_url=settings.SUPABASE_URL, supabase_key=settings.SUPABASE_KEY
        )
    except Exception as e:
        raise Exception(f"Failed to create Supabase client: {str(e)}")


async def initialize_supabase_tables():
    """
    Initialize required Supabase tables if they don't exist.
    This should be called during application startup.
    """
    try:
        with supabase_client_context() as client:
            # Create share_links table if it doesn't exist
            client.rpc(
                "create_share_links_table",
                {
                    "table_name": "share_links",
                    "columns": """
                        token text primary key,
                        document_id text not null,
                        expires_at timestamp with time zone not null,
                        max_downloads integer not null,
                        remaining_downloads integer not null,
                        created_at timestamp with time zone not null default now(),
                        last_downloaded_at timestamp with time zone
                    """,
                },
            ).execute()

            # Create indexes for better query performance
            client.rpc(
                "create_index",
                {
                    "table_name": "share_links",
                    "index_name": "idx_share_links_expires_at",
                    "column_name": "expires_at",
                },
            ).execute()

            client.rpc(
                "create_index",
                {
                    "table_name": "share_links",
                    "index_name": "idx_share_links_document_id",
                    "column_name": "document_id",
                },
            ).execute()

            logger.info("Supabase tables initialized successfully")

    except Exception as e:
        # Log the error but don't raise it, as the tables might already exist
        logger.warning(f"Error initializing Supabase tables: {str(e)}")


async def cleanup_database():
    """
    Perform database cleanup operations.
    This should be called during application shutdown or on a schedule.
    """
    try:
        logger.info("Running database cleanup operations")

        with supabase_client_context() as client:
            # Example: Delete expired share links
            now = datetime.utcnow()
            result = (
                client.table("share_links")
                .delete()
                .lt("expires_at", now.isoformat())
                .execute()
            )

            if not result.error:
                logger.info(f"Deleted {len(result.data)} expired share links")
            else:
                logger.error(f"Error deleting expired share links: {result.error}")

    except Exception as e:
        logger.error(f"Error cleaning up database: {str(e)}")


def cleanup_expired_connections() -> int:
    """
    Clean up expired Supabase connections from the pool.
    This should be called periodically to prevent stale connections.

    Returns:
        Number of connections removed
    """
    removed = _connection_pool.cleanup_expired()
    if removed > 0:
        logger.info(f"Cleaned up {removed} expired Supabase connections")
    return removed


def close_all_connections() -> None:
    """
    Close all Supabase connections in the pool.
    This should be called during application shutdown.
    """
    logger.info(
        f"Closing all Supabase connections (pool size: {_connection_pool.size()})"
    )
    _connection_pool.clear()
    logger.info("All Supabase connections closed")
