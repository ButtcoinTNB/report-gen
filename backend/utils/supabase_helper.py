# pyright: reportReturnType=false

"""
Utility functions for working with Supabase.
This module provides helper functions to create Supabase clients with proper connection pooling.
"""

import logging
import threading
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime, timedelta
from typing import (
    Dict,
    Optional,
    Tuple,
    cast,
    TypeVar,
    Any,
    List,
    Generic,
    AsyncIterator,
)

from supabase import create_client
from supabase.client import Client, ClientOptions
from postgrest.base_request_builder import APIResponse
from supabase.lib.auth_client import SupabaseAuthClient

# Import only one version of APIResponse to avoid conflicts
try:
    from postgrest.base_request_builder import APIResponse
except ImportError:
    from postgrest._async.request import APIResponse

T = TypeVar("T")  # Define a generic type variable

# Use imports with fallbacks for better compatibility across environments
try:
    # First try imports without 'backend.' prefix (for Render)
    from config import get_settings, settings
    from utils.error_handler import logger
except ImportError:
    # Fallback to imports with 'backend.' prefix (for local dev)
    from config import get_settings, settings
    from utils.error_handler import logger

# Configure logger
logger = logging.getLogger(__name__)

import asyncio
import time
from postgrest.deprecated_client import Client
from postgrest.types import APIResponse


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
RETRY_DELAY = 1.0  # Base delay between retries in seconds
CONNECTION_TIMEOUT = 3600  # 1 hour in seconds
CONNECTION_EXPIRY_SECONDS = 300
POOL_CLEANUP_INTERVAL = 60  # Cleanup interval in seconds


# Thread-safe connection pool with LRU eviction and expiration
class SupabaseConnectionPool:
    """A thread-safe connection pool for Supabase clients."""

    def __init__(self, url: str, key: str, options: Optional[ClientOptions] = None):
        self.url = url
        self.key = key
        self.options = options
        self.pool: Dict[str, Tuple[Client, float]] = {}
        self.lock = asyncio.Lock()
        self._cleanup_task = None
        self._start_cleanup_task()

    def _start_cleanup_task(self):
        """Start the periodic cleanup task if not already running."""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._periodic_cleanup())

    async def _periodic_cleanup(self):
        """Periodically clean up expired connections."""
        while True:
            try:
                await asyncio.sleep(POOL_CLEANUP_INTERVAL)
                await self.cleanup_expired()
            except Exception as e:
                logger.error(f"Error during connection pool cleanup: {str(e)}")

    async def cleanup_expired(self) -> None:
        """Clean up expired connections from the pool"""
        async with self.lock:
            current_time = time.time()
            expired_keys: List[str] = []

            for key, (client, last_used) in self.pool.items():
                if current_time - last_used > CONNECTION_TIMEOUT:
                    expired_keys.append(key)
                    try:
                        await client.auth.sign_out()
                    except Exception as e:
                        logger.warning(f"Error signing out expired client: {str(e)}")

            for key in expired_keys:
                del self.pool[key]

            if expired_keys:
                logger.info(f"Cleaned up {len(expired_keys)} expired connections")

    async def get(self, key: str) -> Optional[Client]:
        """
        Get a client from the pool.

        Args:
            key: The unique key for the client

        Returns:
            The client if found in the pool, None otherwise
        """
        async with self.lock:
            if key in self.pool:
                client, _ = self.pool[key]
                # Update last used time
                self.pool[key] = (client, time.time())
                return client
            return None

    async def put(self, key: str, client: Client) -> None:
        """
        Add a client to the pool, evicting the least recently used client if necessary.

        Args:
            key: The unique key for the client
            client: The Supabase client to add to the pool
        """
        async with self.lock:
            # Check if we need to evict
            if len(self.pool) >= MAX_CONNECTIONS and key not in self.pool:
                await self.evict_oldest()

            self.pool[key] = (client, time.time())

    async def evict_oldest(self) -> None:
        """Evict the least recently used client from the pool"""
        if not self.pool:
            return

        oldest_key = None
        oldest_time = None

        for key, (client, last_used) in self.pool.items():
            if oldest_time is None or last_used < oldest_time:
                oldest_key = key
                oldest_time = last_used

        if oldest_key:
            logger.debug(
                f"Evicting oldest Supabase connection: last used {oldest_time}"
            )
            client, _ = self.pool[oldest_key]
            try:
                await client.auth.sign_out()
            except Exception as e:
                logger.warning(f"Error signing out client during eviction: {str(e)}")
            del self.pool[oldest_key]

    async def size(self) -> int:
        """Get the current size of the pool"""
        async with self.lock:
            return len(self.pool)

    async def get_session(self, client: Client) -> Optional[Dict[str, Any]]:
        """Get the current session from the client"""
        try:
            session = await client.auth.get_session()
            return session.model_dump() if session else None
        except Exception as e:
            logger.error(f"Error getting session: {str(e)}")
            return None


# Initialize the global connection pool
_connection_pool = SupabaseConnectionPool(settings.SUPABASE_URL, settings.SUPABASE_KEY)


async def create_supabase_client() -> Client:
    """
    Create and return a configured Supabase client.

    Returns:
        Supabase Client instance

    Raises:
        Exception: If Supabase configuration is missing or invalid
    """
    settings_obj = get_settings()

    if not settings_obj.SUPABASE_URL or not settings_obj.SUPABASE_KEY:
        raise SupabaseConfigError("Supabase configuration is missing")

    try:
        client = await create_client(
            supabase_url=settings_obj.SUPABASE_URL,
            supabase_key=settings_obj.SUPABASE_KEY,
        )
        return client
    except Exception as e:
        raise SupabaseConnectionError(f"Failed to create Supabase client: {str(e)}")


# Keep for compatibility with existing code
def get_supabase_client() -> Client:
    """
    Synchronous function to get a Supabase client.
    Note: In most new code, you should use the async version instead.

    Returns:
        A Supabase client instance
    """
    # This is a simplified version that should only be used in synchronous contexts
    client_key = f"{settings.SUPABASE_URL}:{settings.SUPABASE_KEY}"

    # Check if client already exists in pool
    client = _connection_pool.get(client_key)
    if client:
        return client

    # Create a new synchronous client - not ideal, but necessary for backward compatibility
    from supabase import create_client as create_sync_client

    supabase = create_sync_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    _connection_pool.put(
        client_key, cast(Client, supabase)
    )  # Type casting for compatibility
    return cast(Client, supabase)


@contextmanager
def supabase_client_context():
    """
    Context manager for Supabase client access.
    Ensures connections are returned to the pool after use.

    Usage:
        with supabase_client_context() as supabase:
            response = supabase.table("reports").select("*").execute()
    """
    # When a client is needed, get one from pool (or create new one if needed)
    client = get_supabase_client()

    try:
        # Provide the client to the calling code
        yield client
    except Exception as e:
        logger.error(f"Error in Supabase operation: {str(e)}")
        raise
    finally:
        # No explicit cleanup needed as we're managing the pool centrally
        pass


@asynccontextmanager
async def async_supabase_client_context() -> AsyncIterator[Client]:
    """
    Async context manager for Supabase client access.
    Ensures connections are properly managed and includes retry logic.

    Usage:
        async with async_supabase_client_context() as supabase:
            response = await supabase.table("reports").select("*").execute()

    Raises:
        SupabaseConnectionError: If unable to establish connection after retries
        SupabaseConfigError: If Supabase configuration is invalid
    """
    client = None
    attempt = 0
    last_error = None

    while attempt < MAX_RETRIES:
        try:
            client = await create_supabase_client()
            # Test the connection
            await client.auth.get_session()
            break
        except Exception as e:
            attempt += 1
            last_error = e
            logger.warning(
                f"Failed to create Supabase client (attempt {attempt}/{MAX_RETRIES}): {str(e)}"
            )
            if attempt < MAX_RETRIES:
                import asyncio
                await asyncio.sleep(RETRY_DELAY * attempt)  # Exponential backoff
            continue

    if client is None:
        raise SupabaseConnectionError(
            f"Failed to establish Supabase connection after {MAX_RETRIES} attempts. "
            f"Last error: {str(last_error)}"
        )

    try:
        yield client
    finally:
        if client:
            try:
                await client.auth.sign_out()
            except Exception as e:
                logger.warning(f"Error during Supabase client sign out: {str(e)}")


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
        # Use synchronous client
        client = get_supabase_client()
        return client.storage.from_(bucket).get_public_url(path)
    except Exception as e:
        logger.error(f"Error getting storage URL for {bucket}/{path}: {str(e)}")
        return None


# Define a sync version for use in synchronous code
async def get_supabase_storage_url_async(bucket: str, path: str) -> Optional[str]:
    """
    Async version to get the public URL for a file in Supabase Storage

    Args:
        bucket: The storage bucket name
        path: The path to the file in storage

    Returns:
        The public URL of the file, or None if there's an error
    """
    try:
        # Create async client
        client = await create_supabase_client()
        # Use the client to get a storage URL
        # Type checker doesn't recognize that this isn't awaitable
        return _get_storage_url_from_client(client, bucket, path)  # type: ignore
    except Exception as e:
        logger.error(f"Error getting storage URL for {bucket}/{path}: {str(e)}")
        return None


def _get_storage_url_from_client(client: Client, bucket: str, path: str) -> str:
    """Helper function to get storage URL from a client instance."""
    # get_public_url is a synchronous method that returns a string directly
    return client.storage.from_(bucket).get_public_url(path)  # type: ignore


async def get_supabase_connection_status() -> dict:
    """
    Check the status of the Supabase connection.

    Returns:
        A dictionary with status information
    """
    try:
        client = await create_supabase_client()
        # Use the client to do a simple query to check connection
        await client.table("reports").select("*").limit(1).execute()

        return {
            "status": "connected",
            "pool_size": _connection_pool.size(),
            "url": (
                settings.SUPABASE_URL.split("@")[-1]
                if "@" in settings.SUPABASE_URL
                else settings.SUPABASE_URL
            ),
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "pool_size": _connection_pool.size(),
        }


async def initialize_supabase_tables():
    """
    Initialize required Supabase tables if they don't exist.
    This should be called during application startup.
    """
    try:
        client = await create_supabase_client()

        # Create share_links table if it doesn't exist
        await client.rpc(
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
        await client.rpc(
            "create_index",
            {
                "table_name": "share_links",
                "index_name": "idx_share_links_expires_at",
                "column_name": "expires_at",
            },
        ).execute()

        await client.rpc(
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

        client = await create_supabase_client()

        # Example: Delete expired share links
        now = datetime.utcnow()
        result = (
            await client.table("share_links")
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


class ResourceTracker(Generic[T]):
    def __init__(
        self, name: str, cleanup_func: callable, resource_type: str = "resource"
    ):
        self.name = name
        self.cleanup_func = cleanup_func
        self.resource_type = resource_type
        self._resources: Dict[str, T] = {}


async def check_token_expiry(supabase: Client) -> Dict[str, Any]:
    result: APIResponse[Dict[str, Any]] = (
        await supabase.table("tokens").select("*").execute()
    )

    if result.error:
        raise Exception(f"Error checking token expiry: {result.error}")
    if len(result.data) == 0:
        raise Exception("No tokens found")

    return result.data[0]


def create_presigned_url(
    bucket_name: str,
    file_path: str,
    max_size: int = 10485760,  # 10MB default
    expiry_seconds: int = 3600,  # 1 hour default
) -> Tuple[str, Dict[str, Any]]:
    # Implementation of create_presigned_url function
    pass


async def get_report_by_id(supabase: Client, report_id: str) -> Dict[str, Any]:
    """Get a report by its ID."""
    result: APIResponse[Dict[str, Any]] = (
        await supabase.table("reports").select("*").eq("id", report_id).execute()
    )

    if result.error:
        raise SupabaseConnectionError(f"Error getting report: {result.error}")
    if len(result.data) == 0:
        raise SupabaseConnectionError(f"Report not found: {report_id}")

    return cast(Dict[str, Any], result.data[0])


async def get_reports(supabase: Client) -> List[Dict[str, Any]]:
    """Get all reports."""
    result: APIResponse[List[Dict[str, Any]]] = (
        await supabase.table("reports").select("*").execute()
    )

    if result.error:
        raise SupabaseConnectionError(f"Error getting reports: {result.error}")

    return cast(List[Dict[str, Any]], result.data)


async def call_function(
    supabase: Client, function_name: str, params: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Call a Supabase Edge Function."""
    result: APIResponse[Dict[str, Any]] = await supabase.rpc(
        function_name, params
    ).execute()

    if result.error:
        raise SupabaseConnectionError(
            f"Error calling function {function_name}: {result.error}"
        )

    return cast(Dict[str, Any], result.data)


async def get_connection(self) -> Tuple[Client, int]:
    async with self._lock:
        current_time = time.time()
        

async def add_connection(self, client: Client) -> int:
    async with self._lock:
        connection_id = self._next_connection_id
