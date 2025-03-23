"""
Resource manager for tracking and managing system resources
"""

import logging
import time
from pathlib import Path
from typing import Dict, Any, List, Set, Optional
from threading import Lock
import atexit
import psutil
import os
import shutil

# Configure logging
logger = logging.getLogger(__name__)

class ResourceManager:
    """
    Manages system resources and ensures proper cleanup
    """
    
    def __init__(self):
        """Initialize the resource manager"""
        self.resources: Dict[str, Set[str]] = {
            "files": set(),
            "temp_dirs": set(),
            "processes": set(),
            "memory_objects": set()
        }
        self.lock = Lock()
        self.initialized = False
    
    def initialize(self) -> None:
        """
        Initialize the resource manager
        """
        if self.initialized:
            return
            
        logger.info("Initializing resource manager")
        self.initialized = True
        
        # Register cleanup on exit
        atexit.register(self.cleanup)
        
        # Create temporary directory if needed
        temp_dir = Path(__file__).parent.parent / "data" / "temp"
        temp_dir.mkdir(exist_ok=True, parents=True)
        
        # Clean any leftover temporary files from previous runs
        self._clean_temp_dir(temp_dir)
    
    def track_file(self, file_path: str) -> None:
        """
        Track a file for potential cleanup
        
        Args:
            file_path: Path to the file to track
        """
        with self.lock:
            self.resources["files"].add(str(file_path))
    
    def track_temp_dir(self, dir_path: str) -> None:
        """
        Track a temporary directory for cleanup
        
        Args:
            dir_path: Path to the temporary directory
        """
        with self.lock:
            self.resources["temp_dirs"].add(str(dir_path))
    
    def track_process(self, process_id: int) -> None:
        """
        Track a process for potential termination on shutdown
        
        Args:
            process_id: Process ID to track
        """
        with self.lock:
            self.resources["processes"].add(str(process_id))
    
    def track_memory_object(self, object_id: str) -> None:
        """
        Track a memory object for potential cleanup
        
        Args:
            object_id: ID of the memory object to track
        """
        with self.lock:
            self.resources["memory_objects"].add(object_id)
    
    def release_file(self, file_path: str) -> None:
        """
        Stop tracking a file
        
        Args:
            file_path: Path to the file to release
        """
        with self.lock:
            self.resources["files"].discard(str(file_path))
    
    def release_temp_dir(self, dir_path: str) -> None:
        """
        Stop tracking a temporary directory
        
        Args:
            dir_path: Path to the temporary directory to release
        """
        with self.lock:
            self.resources["temp_dirs"].discard(str(dir_path))
    
    def release_process(self, process_id: int) -> None:
        """
        Stop tracking a process
        
        Args:
            process_id: Process ID to release
        """
        with self.lock:
            self.resources["processes"].discard(str(process_id))
    
    def release_memory_object(self, object_id: str) -> None:
        """
        Stop tracking a memory object
        
        Args:
            object_id: ID of the memory object to release
        """
        with self.lock:
            self.resources["memory_objects"].discard(object_id)
    
    def cleanup(self) -> None:
        """
        Clean up all tracked resources
        """
        if not self.initialized:
            return
            
        logger.info("Cleaning up resources")
        
        with self.lock:
            # Clean up temporary directories
            for dir_path in self.resources["temp_dirs"]:
                try:
                    if Path(dir_path).exists():
                        shutil.rmtree(dir_path)
                        logger.debug(f"Removed temporary directory: {dir_path}")
                except Exception as e:
                    logger.error(f"Failed to remove temporary directory {dir_path}: {str(e)}")
            
            # Terminate tracked processes
            for pid_str in self.resources["processes"]:
                try:
                    pid = int(pid_str)
                    if psutil.pid_exists(pid):
                        process = psutil.Process(pid)
                        process.terminate()
                        logger.debug(f"Terminated process: {pid}")
                except Exception as e:
                    logger.error(f"Failed to terminate process {pid_str}: {str(e)}")
            
            # Clear the tracking sets
            for resource_type in self.resources:
                self.resources[resource_type].clear()
        
        logger.info("Resource cleanup complete")
    
    def get_resource_usage(self) -> Dict[str, Any]:
        """
        Get current resource usage statistics
        
        Returns:
            Dictionary containing resource usage statistics
        """
        try:
            # Get system-wide CPU and memory usage
            cpu_percent = psutil.cpu_percent()
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            
            # Get process-specific information
            process = psutil.Process(os.getpid())
            process_cpu = process.cpu_percent()
            process_memory = process.memory_info().rss / (1024 * 1024)  # MB
            
            # Count tracked resources
            with self.lock:
                tracked_resources = {
                    resource_type: len(resources)
                    for resource_type, resources in self.resources.items()
                }
            
            return {
                "system": {
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory.percent,
                    "memory_available_mb": memory.available / (1024 * 1024),
                    "disk_percent": disk.percent,
                    "disk_free_gb": disk.free / (1024 * 1024 * 1024)
                },
                "process": {
                    "cpu_percent": process_cpu,
                    "memory_mb": process_memory,
                    "uptime": time.time() - process.create_time()
                },
                "tracked_resources": tracked_resources
            }
        except Exception as e:
            logger.error(f"Failed to get resource usage: {str(e)}")
            return {"error": str(e)}
    
    def _clean_temp_dir(self, temp_dir: Path) -> None:
        """
        Clean up files in the temporary directory
        
        Args:
            temp_dir: Path to the temporary directory
        """
        try:
            if temp_dir.exists():
                # Remove files older than 24 hours
                cutoff_time = time.time() - (24 * 60 * 60)
                
                for item in temp_dir.iterdir():
                    try:
                        if item.is_file() and item.stat().st_mtime < cutoff_time:
                            item.unlink()
                            logger.debug(f"Removed old temporary file: {item}")
                        elif item.is_dir() and item.stat().st_mtime < cutoff_time:
                            shutil.rmtree(item)
                            logger.debug(f"Removed old temporary directory: {item}")
                    except Exception as e:
                        logger.error(f"Failed to remove {item}: {str(e)}")
        except Exception as e:
            logger.error(f"Failed to clean temporary directory: {str(e)}")

# Create singleton instance
resource_manager = ResourceManager() 