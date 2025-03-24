import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Generic, Optional, Set, TypeVar

# Configure logger
logger = logging.getLogger(__name__)

T = TypeVar("T")


class ResourceTracker(Generic[T]):
    """
    A class for tracking resources that need cleanup

    ResourceTracker helps manage lifecycle of resources like connections,
    temporary files, and other system resources that need explicit cleanup.
    """

    def __init__(
        self, cleanup_func: Callable[[T], None], resource_type: str = "resource"
    ):
        """
        Initialize a resource tracker

        Args:
            cleanup_func: Function to call to clean up the resource
            resource_type: Type of resource for logging purposes
        """
        self.resources: Dict[str, Dict[str, Any]] = {}
        self.cleanup_func = cleanup_func
        self.resource_type = resource_type
        self.last_cleanup = datetime.now()

    def register(self, resource: T, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Register a resource for tracking

        Args:
            resource: The resource to track
            metadata: Optional metadata about the resource

        Returns:
            str: Resource ID
        """
        resource_id = str(uuid.uuid4())
        self.resources[resource_id] = {
            "resource": resource,
            "registered_at": datetime.now(),
            "last_accessed": datetime.now(),
            "metadata": metadata or {},
        }

        logger.debug(f"Registered {self.resource_type} with ID {resource_id}")
        return resource_id

    def get(self, resource_id: str) -> Optional[T]:
        """
        Get a tracked resource

        Args:
            resource_id: ID of the resource

        Returns:
            Optional[T]: The resource if found, None otherwise
        """
        if resource_id not in self.resources:
            return None

        # Update last accessed time
        self.resources[resource_id]["last_accessed"] = datetime.now()
        return self.resources[resource_id]["resource"]

    def update_metadata(self, resource_id: str, metadata: Dict[str, Any]) -> bool:
        """
        Update metadata for a tracked resource

        Args:
            resource_id: ID of the resource
            metadata: New metadata to merge with existing

        Returns:
            bool: True if resource was found and updated, False otherwise
        """
        if resource_id not in self.resources:
            return False

        # Merge the new metadata with existing
        self.resources[resource_id]["metadata"].update(metadata)
        self.resources[resource_id]["last_accessed"] = datetime.now()
        return True

    def release(self, resource_id: str) -> bool:
        """
        Release a tracked resource, cleaning it up

        Args:
            resource_id: ID of the resource

        Returns:
            bool: True if resource was found and released, False otherwise
        """
        if resource_id not in self.resources:
            return False

        try:
            resource = self.resources[resource_id]["resource"]
            self.cleanup_func(resource)
            del self.resources[resource_id]
            logger.debug(f"Released {self.resource_type} with ID {resource_id}")
            return True
        except Exception as e:
            logger.error(
                f"Error releasing {self.resource_type} with ID {resource_id}: {e}"
            )
            # Still remove it from tracking
            if resource_id in self.resources:
                del self.resources[resource_id]
            return False

    def cleanup_stale(self, max_age_minutes: int = 30) -> int:
        """
        Clean up stale resources not accessed recently

        Args:
            max_age_minutes: Maximum age in minutes before a resource is considered stale

        Returns:
            int: Number of resources cleaned up
        """
        now = datetime.now()
        cutoff = now - timedelta(minutes=max_age_minutes)
        stale_ids = [
            rid
            for rid, data in self.resources.items()
            if data["last_accessed"] < cutoff
        ]

        cleaned_count = 0
        for rid in stale_ids:
            if self.release(rid):
                cleaned_count += 1

        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} stale {self.resource_type}s")

        self.last_cleanup = now
        return cleaned_count


class DependencyManager:
    """
    Central manager for application dependencies and resources

    Provides a unified interface for managing application resources,
    ensuring proper cleanup and lifecycle management.
    """

    def __init__(self):
        """Initialize the dependency manager"""
        self.trackers: Dict[str, ResourceTracker] = {}
        self.connections: Dict[str, Any] = {}
        self.cleanup_tasks: Set[asyncio.Task] = set()
        self._shutdown_requested = False

        # Start background cleanup
        self._start_cleanup_task()

    def register_tracker(
        self,
        name: str,
        cleanup_func: Callable[[Any], None],
        resource_type: str = "resource",
    ) -> ResourceTracker:
        """
        Register a new resource tracker

        Args:
            name: Name for the tracker
            cleanup_func: Function to call to clean up tracked resources
            resource_type: Type of resource for logging purposes

        Returns:
            ResourceTracker: The new tracker
        """
        tracker = ResourceTracker(cleanup_func, resource_type)
        self.trackers[name] = tracker
        return tracker

    def get_tracker(self, name: str) -> Optional[ResourceTracker]:
        """
        Get a resource tracker by name

        Args:
            name: Name of the tracker

        Returns:
            Optional[ResourceTracker]: The tracker if found, None otherwise
        """
        return self.trackers.get(name)

    def register_connection(
        self, name: str, connection: Any, close_method: str = "close"
    ) -> None:
        """
        Register a connection-like object

        Args:
            name: Name for the connection
            connection: The connection object
            close_method: Name of the method to call to close the connection
        """
        self.connections[name] = {
            "connection": connection,
            "close_method": close_method,
            "registered_at": datetime.now(),
        }
        logger.debug(f"Registered connection '{name}'")

    def get_connection(self, name: str) -> Optional[Any]:
        """
        Get a connection by name

        Args:
            name: Name of the connection

        Returns:
            Optional[Any]: The connection if found, None otherwise
        """
        if name not in self.connections:
            return None

        return self.connections[name]["connection"]

    def close_connection(self, name: str) -> bool:
        """
        Close a connection by name

        Args:
            name: Name of the connection

        Returns:
            bool: True if connection was found and closed, False otherwise
        """
        if name not in self.connections:
            return False

        try:
            conn_info = self.connections[name]
            close_method = getattr(conn_info["connection"], conn_info["close_method"])
            close_method()
            del self.connections[name]
            logger.debug(f"Closed connection '{name}'")
            return True
        except Exception as e:
            logger.error(f"Error closing connection '{name}': {e}")
            # Still remove it from tracking
            if name in self.connections:
                del self.connections[name]
            return False

    def _start_cleanup_task(self) -> None:
        """Start the background cleanup task"""

        async def cleanup_loop():
            while not self._shutdown_requested:
                try:
                    # Run cleanup on each tracker
                    for name, tracker in self.trackers.items():
                        # Only run cleanup every 5 minutes per tracker
                        if datetime.now() - tracker.last_cleanup > timedelta(minutes=5):
                            tracker.cleanup_stale()

                    # Wait for next cleanup cycle
                    await asyncio.sleep(60)  # Check every minute
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Error in cleanup loop: {e}")
                    await asyncio.sleep(60)  # Wait before retrying

        # Create and store the task
        cleanup_task = asyncio.create_task(cleanup_loop())
        self.cleanup_tasks.add(cleanup_task)
        cleanup_task.add_done_callback(self.cleanup_tasks.discard)

    async def shutdown(self) -> None:
        """Shutdown the dependency manager, cleaning up all resources"""
        self._shutdown_requested = True

        # Cancel all cleanup tasks
        for task in self.cleanup_tasks:
            if not task.done():
                task.cancel()

        # Wait for all tasks to complete
        if self.cleanup_tasks:
            await asyncio.gather(*self.cleanup_tasks, return_exceptions=True)

        # Clean up all resources in all trackers
        for name, tracker in self.trackers.items():
            for resource_id in list(tracker.resources.keys()):
                tracker.release(resource_id)

        # Close all connections
        for name in list(self.connections.keys()):
            self.close_connection(name)

        logger.info("Dependency manager shutdown complete")


# Global instance
dependency_manager = DependencyManager()


def get_dependency_manager() -> DependencyManager:
    """Get the global dependency manager instance"""
    return dependency_manager
