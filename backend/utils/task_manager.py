from typing import Dict, Any, Optional, List, Set
import uuid
import time
import asyncio
import os
import logging
from datetime import datetime, timedelta
import json

from .dependency_manager import get_dependency_manager, ResourceTracker

# Configure logging
logger = logging.getLogger(__name__)

# Cache for task statuses with TTL
class TaskCache:
    """A cache for task statuses with time-to-live (TTL) functionality"""
    
    def __init__(self, ttl_minutes: int = 60):
        """
        Initialize the task cache
        
        Args:
            ttl_minutes: Default time-to-live for cached tasks in minutes
        """
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._default_ttl = ttl_minutes
        
        # Register with dependency manager for cleanup
        self._resource_tracker = get_dependency_manager().register_tracker(
            "task_cache", 
            lambda _: None,  # No-op cleanup function
            "task"
        )
        
        # Start cleanup task
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        self._shutdown_requested = False
    
    def __getitem__(self, task_id: str) -> Dict[str, Any]:
        """Get a task by ID (raises KeyError if not found)"""
        if task_id not in self._cache:
            raise KeyError(f"Task with ID {task_id} not found")
        
        # Update last accessed time
        self._cache[task_id]["_last_accessed"] = datetime.now()
        return self._cache[task_id]
    
    def __setitem__(self, task_id: str, value: Dict[str, Any]):
        """Set a task by ID"""
        # Add metadata fields if not present
        if "_created_at" not in value:
            value["_created_at"] = datetime.now()
        
        if "_ttl_minutes" not in value:
            value["_ttl_minutes"] = self._default_ttl
            
        value["_last_accessed"] = datetime.now()
        
        # Store in cache
        self._cache[task_id] = value
        
        # Register with resource tracker
        task_type = value.get("type", "unknown")
        self._resource_tracker.register(
            task_id,
            {
                "task_id": task_id,
                "type": task_type,
                "created_at": value["_created_at"].isoformat(),
                "owner": value.get("owner"),
                "status": value.get("status", "unknown")
            }
        )
    
    def __delitem__(self, task_id: str):
        """Delete a task by ID"""
        if task_id in self._cache:
            # Clean up any associated resources
            self._cleanup_task_resources(task_id)
            del self._cache[task_id]
    
    def __contains__(self, task_id: str) -> bool:
        """Check if a task ID exists in the cache"""
        if task_id in self._cache:
            # Refresh last accessed time
            self._cache[task_id]["_last_accessed"] = datetime.now()
            return True
        return False
    
    def get(self, task_id: str, default=None) -> Optional[Dict[str, Any]]:
        """Get a task by ID with a default value if not found"""
        try:
            return self[task_id]
        except KeyError:
            return default
    
    def update(self, task_id: str, data: Dict[str, Any]) -> bool:
        """Update a task with new data"""
        if task_id not in self._cache:
            return False
        
        # Update the task data
        self._cache[task_id].update(data)
        self._cache[task_id]["_last_accessed"] = datetime.now()
        return True
    
    def items(self):
        """Get all items in the cache"""
        return self._cache.items()
    
    def _cleanup_task_resources(self, task_id: str):
        """Clean up resources associated with a task"""
        if task_id not in self._cache:
            return
        
        task = self._cache[task_id]
        
        # Close any open file handles
        for file_key in ["input_file", "output_file", "temp_files"]:
            if file_key in task and task[file_key]:
                files = task[file_key] if isinstance(task[file_key], list) else [task[file_key]]
                for file in files:
                    try:
                        if hasattr(file, "close") and callable(file.close):
                            file.close()
                    except Exception as e:
                        logger.error(f"Error closing file for task {task_id}: {e}")
        
        # Clean up temporary files
        if "resource_paths" in task and task["resource_paths"]:
            for path in task["resource_paths"]:
                try:
                    if os.path.exists(path):
                        if os.path.isdir(path):
                            import shutil
                            shutil.rmtree(path)
                        else:
                            os.remove(path)
                        logger.debug(f"Cleaned up resource: {path}")
                except Exception as e:
                    logger.error(f"Error cleaning up resource {path} for task {task_id}: {e}")
        
        # Cancel any associated asyncio tasks
        if "asyncio_tasks" in task and task["asyncio_tasks"]:
            for async_task in task["asyncio_tasks"]:
                try:
                    if not async_task.done():
                        async_task.cancel()
                except Exception as e:
                    logger.error(f"Error cancelling asyncio task for task {task_id}: {e}")
    
    async def _cleanup_loop(self):
        """Background task to clean up expired items"""
        while not self._shutdown_requested:
            try:
                now = datetime.now()
                expired_ids = []
                
                # Find expired items
                for task_id, task in self._cache.items():
                    ttl = timedelta(minutes=task.get("_ttl_minutes", self._default_ttl))
                    last_accessed = task.get("_last_accessed", task.get("_created_at", now))
                    
                    # Special handling for completed or failed tasks
                    if task.get("status") in ["completed", "failed"]:
                        # Use a shorter TTL for completed/failed tasks
                        completed_ttl = timedelta(minutes=min(30, self._default_ttl))
                        if now - last_accessed > completed_ttl:
                            expired_ids.append(task_id)
                    # Default TTL for other tasks
                    elif now - last_accessed > ttl:
                        expired_ids.append(task_id)
                
                # Clean up expired items
                for task_id in expired_ids:
                    self._cleanup_task_resources(task_id)
                    del self._cache[task_id]
                    logger.info(f"Removed expired task {task_id} from cache")
                
                # Persist task data to disk periodically
                await self._persist_tasks()
                
                # Wait before next cleanup
                await asyncio.sleep(60)  # Check every minute
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in task cache cleanup: {e}")
                await asyncio.sleep(60)  # Wait before retrying
    
    async def _persist_tasks(self):
        """Persist tasks to disk for recovery"""
        try:
            # Don't persist if there are no tasks or very few tasks
            if len(self._cache) < 5:
                return
                
            # Create directory if it doesn't exist
            os.makedirs("data/tasks", exist_ok=True)
            
            # Prepare serializable data
            serializable_tasks = {}
            for task_id, task in self._cache.items():
                # Skip internal tasks or temporary tasks
                if task.get("_internal", False) or task.get("_temporary", False):
                    continue
                    
                # Create a serializable copy without non-serializable items
                task_copy = {}
                for k, v in task.items():
                    # Skip keys starting with underscore and non-serializable values
                    if not k.startswith("_") and (isinstance(v, (str, int, float, bool, list, dict)) or v is None):
                        task_copy[k] = v
                        
                # Add metadata as proper fields
                task_copy["_created_at"] = task.get("_created_at", datetime.now()).isoformat()
                task_copy["_last_accessed"] = task.get("_last_accessed", datetime.now()).isoformat()
                
                serializable_tasks[task_id] = task_copy
            
            # Only write if we have valid tasks
            if serializable_tasks:
                # Write to temp file first, then rename for atomic write
                temp_path = "data/tasks/tasks_cache.json.tmp"
                final_path = "data/tasks/tasks_cache.json"
                
                with open(temp_path, "w") as f:
                    json.dump(serializable_tasks, f)
                    
                # Atomic rename
                os.replace(temp_path, final_path)
                
                logger.debug(f"Persisted {len(serializable_tasks)} tasks to disk")
        except Exception as e:
            logger.error(f"Error persisting tasks to disk: {e}")
    
    async def load_from_disk(self):
        """Load tasks from disk on startup"""
        try:
            path = "data/tasks/tasks_cache.json"
            if not os.path.exists(path):
                return
                
            with open(path, "r") as f:
                serialized_tasks = json.load(f)
            
            loaded_count = 0
            for task_id, task_data in serialized_tasks.items():
                # Skip already loaded tasks
                if task_id in self._cache:
                    continue
                    
                # Convert ISO timestamps back to datetime
                for key in ["_created_at", "_last_accessed"]:
                    if key in task_data:
                        try:
                            task_data[key] = datetime.fromisoformat(task_data[key])
                        except:
                            task_data[key] = datetime.now()
                
                # Add to cache
                self._cache[task_id] = task_data
                loaded_count += 1
            
            if loaded_count > 0:
                logger.info(f"Loaded {loaded_count} tasks from disk")
        
        except Exception as e:
            logger.error(f"Error loading tasks from disk: {e}")
    
    async def shutdown(self):
        """Shutdown the task cache and clean up resources"""
        self._shutdown_requested = True
        
        # Cancel cleanup task
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Persist tasks one last time
        await self._persist_tasks()
        
        # Clean up all tasks
        for task_id in list(self._cache.keys()):
            self._cleanup_task_resources(task_id)
        
        logger.info("Task cache shutdown complete")

# Global instance
tasks_cache = TaskCache()

# Initialize cache on startup
async def initialize_task_cache():
    """Initialize the task cache on application startup"""
    await tasks_cache.load_from_disk()
    logger.info("Task cache initialized")

# Shutdown cache on application shutdown
async def shutdown_task_cache():
    """Shutdown the task cache on application shutdown"""
    await tasks_cache.shutdown()
    logger.info("Task cache shutdown") 