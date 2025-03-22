import sqlite3
import logging
import json
import time
import asyncio
import os
from typing import Dict, Any, List, Optional, Union, Tuple
from datetime import datetime, timedelta
from contextlib import contextmanager
import threading
from .dependency_manager import get_dependency_manager

# Configure logger
logger = logging.getLogger(__name__)

# Thread local storage for database connections
_local = threading.local()

class DBConnector:
    """
    SQLite database connector with TTL-based caching support
    
    This class provides connection management and simple caching for database
    operations, automatically expiring cache entries by TTL.
    """
    
    def __init__(self, 
                 db_path: str = "data/application.db", 
                 cache_ttl: int = 30, 
                 max_cache_size: int = 1000):
        """
        Initialize the database connector
        
        Args:
            db_path: Path to the SQLite database file
            cache_ttl: Default cache TTL in minutes
            max_cache_size: Maximum number of items to keep in cache
        """
        self.db_path = db_path
        self.cache_ttl = cache_ttl
        self.max_cache_size = max_cache_size
        self._cache: Dict[str, Any] = {}
        self._cache_timestamps: Dict[str, float] = {}
        self._cache_lock = asyncio.Lock()
        self._cleanup_task = None
        self._shutdown_requested = False
        
        # Create directory for database if it doesn't exist
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # Initialize the database
        self._init_db()
        
        # Register with dependency manager
        get_dependency_manager().register_connection(
            "db_connection", 
            self, 
            "close"
        )
        
        # Start cleanup task
        self._start_cleanup_task()
    
    def _init_db(self):
        """Initialize the database schema"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Create tasks table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                type TEXT NOT NULL,
                data TEXT NOT NULL,
                owner_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP
            )
            ''')
            
            # Create reports table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS reports (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata TEXT,
                owner_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            # Create documents table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                file_path TEXT NOT NULL,
                mime_type TEXT NOT NULL,
                size INTEGER NOT NULL,
                metadata TEXT,
                owner_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            # Create report_documents join table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS report_documents (
                report_id TEXT NOT NULL,
                document_id TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (report_id, document_id),
                FOREIGN KEY (report_id) REFERENCES reports (id) ON DELETE CASCADE,
                FOREIGN KEY (document_id) REFERENCES documents (id) ON DELETE CASCADE
            )
            ''')
            
            # Create indexes
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks (status)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_tasks_owner ON tasks (owner_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_reports_owner ON reports (owner_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_documents_owner ON documents (owner_id)')
            
            conn.commit()
    
    @contextmanager
    def _get_connection(self):
        """Get a database connection from the thread-local pool"""
        # Create thread-local connection if it doesn't exist
        if not hasattr(_local, 'connection'):
            _local.connection = sqlite3.connect(
                self.db_path,
                detect_types=sqlite3.PARSE_DECLTYPES,
                isolation_level=None  # autocommit mode
            )
            _local.connection.row_factory = sqlite3.Row
        
        try:
            yield _local.connection
        except Exception as e:
            # Log the error
            logger.error(f"Database error: {e}")
            # Close the connection if there was an error
            if hasattr(_local, 'connection'):
                _local.connection.close()
                delattr(_local, 'connection')
            raise
    
    def _start_cleanup_task(self):
        """Start the background cache cleanup task"""
        async def cleanup_loop():
            while not self._shutdown_requested:
                try:
                    await self._cleanup_cache()
                    await asyncio.sleep(60)  # Run every minute
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Error in cache cleanup: {e}")
                    await asyncio.sleep(60)  # Wait before retrying
        
        self._cleanup_task = asyncio.create_task(cleanup_loop())
    
    async def _cleanup_cache(self):
        """Clean up expired cache entries"""
        now = time.time()
        expired_keys = []
        
        # Find expired items
        async with self._cache_lock:
            for key, timestamp in self._cache_timestamps.items():
                ttl_seconds = self.cache_ttl * 60
                if now - timestamp > ttl_seconds:
                    expired_keys.append(key)
            
            # Remove expired items
            for key in expired_keys:
                if key in self._cache:
                    del self._cache[key]
                if key in self._cache_timestamps:
                    del self._cache_timestamps[key]
        
        # Also clean up the database
        self._cleanup_expired_tasks()
    
    def _cleanup_expired_tasks(self):
        """Clean up expired tasks from the database"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Delete expired tasks
                cursor.execute('''
                DELETE FROM tasks 
                WHERE expires_at IS NOT NULL AND expires_at < datetime('now')
                ''')
                
                if cursor.rowcount > 0:
                    logger.info(f"Cleaned up {cursor.rowcount} expired tasks from database")
                    
        except Exception as e:
            logger.error(f"Error cleaning up expired tasks: {e}")
    
    async def get_from_cache(self, key: str) -> Optional[Any]:
        """
        Get a value from the cache if it exists and is not expired
        
        Args:
            key: Cache key
            
        Returns:
            Optional[Any]: The cached value or None if not found or expired
        """
        async with self._cache_lock:
            if key in self._cache and key in self._cache_timestamps:
                # Check TTL
                now = time.time()
                timestamp = self._cache_timestamps[key]
                ttl_seconds = self.cache_ttl * 60
                
                if now - timestamp <= ttl_seconds:
                    # Update access time
                    self._cache_timestamps[key] = now
                    return self._cache[key]
                
                # Expired, so remove
                del self._cache[key]
                del self._cache_timestamps[key]
                
        return None
    
    async def set_in_cache(self, key: str, value: Any, ttl_minutes: Optional[int] = None) -> None:
        """
        Store a value in the cache with TTL
        
        Args:
            key: Cache key
            value: Value to store
            ttl_minutes: Optional custom TTL in minutes
        """
        async with self._cache_lock:
            # Check if cache is full
            if len(self._cache) >= self.max_cache_size:
                # Evict oldest items
                items = sorted(self._cache_timestamps.items(), key=lambda x: x[1])
                items_to_remove = len(self._cache) - self.max_cache_size + 1
                
                for i in range(min(items_to_remove, len(items))):
                    evict_key = items[i][0]
                    if evict_key in self._cache:
                        del self._cache[evict_key]
                    if evict_key in self._cache_timestamps:
                        del self._cache_timestamps[evict_key]
            
            # Store the new item
            self._cache[key] = value
            self._cache_timestamps[key] = time.time()
    
    async def invalidate_cache(self, key: str) -> None:
        """
        Remove a key from the cache
        
        Args:
            key: Cache key to invalidate
        """
        async with self._cache_lock:
            if key in self._cache:
                del self._cache[key]
            if key in self._cache_timestamps:
                del self._cache_timestamps[key]
    
    async def save_task(self, 
                        task_id: str, 
                        status: str, 
                        task_type: str,
                        data: Dict[str, Any], 
                        owner_id: Optional[str] = None, 
                        ttl_hours: Optional[int] = None) -> bool:
        """
        Save a task to the database
        
        Args:
            task_id: Task ID
            status: Task status
            task_type: Type of task
            data: Task data
            owner_id: Optional owner ID
            ttl_hours: Optional TTL in hours
            
        Returns:
            bool: True if successful
        """
        try:
            # Prepare expires_at if ttl_hours is provided
            expires_at = None
            if ttl_hours is not None:
                expires_at = (datetime.now() + timedelta(hours=ttl_hours)).isoformat()
            
            # Serialize data
            data_json = json.dumps(data)
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if task already exists
                cursor.execute('SELECT id FROM tasks WHERE id = ?', (task_id,))
                if cursor.fetchone():
                    # Update existing task
                    cursor.execute('''
                    UPDATE tasks 
                    SET status = ?, type = ?, data = ?, owner_id = ?, 
                        updated_at = datetime('now'), expires_at = ?
                    WHERE id = ?
                    ''', (status, task_type, data_json, owner_id, expires_at, task_id))
                else:
                    # Insert new task
                    cursor.execute('''
                    INSERT INTO tasks (id, status, type, data, owner_id, expires_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ''', (task_id, status, task_type, data_json, owner_id, expires_at))
                
                # Invalidate cache
                cache_key = f"task:{task_id}"
                await self.invalidate_cache(cache_key)
                
                return True
                
        except Exception as e:
            logger.error(f"Error saving task {task_id}: {e}")
            return False
    
    async def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a task from the database
        
        Args:
            task_id: Task ID
            
        Returns:
            Optional[Dict[str, Any]]: Task data or None if not found
        """
        cache_key = f"task:{task_id}"
        
        # Try cache first
        cached = await self.get_from_cache(cache_key)
        if cached is not None:
            return cached
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                SELECT id, status, type, data, owner_id, 
                       created_at, updated_at, expires_at
                FROM tasks 
                WHERE id = ?
                ''', (task_id,))
                
                row = cursor.fetchone()
                if not row:
                    return None
                
                # Parse JSON data
                data = json.loads(row['data'])
                
                # Create result
                result = {
                    'id': row['id'],
                    'status': row['status'],
                    'type': row['type'],
                    'data': data,
                    'owner_id': row['owner_id'],
                    'created_at': row['created_at'],
                    'updated_at': row['updated_at'],
                    'expires_at': row['expires_at']
                }
                
                # Cache the result
                await self.set_in_cache(cache_key, result)
                
                return result
                
        except Exception as e:
            logger.error(f"Error getting task {task_id}: {e}")
            return None
    
    async def delete_task(self, task_id: str) -> bool:
        """
        Delete a task from the database
        
        Args:
            task_id: Task ID
            
        Returns:
            bool: True if successful
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
                
                # Invalidate cache
                cache_key = f"task:{task_id}"
                await self.invalidate_cache(cache_key)
                
                return cursor.rowcount > 0
                
        except Exception as e:
            logger.error(f"Error deleting task {task_id}: {e}")
            return False
    
    async def save_report(self, 
                          report_id: str, 
                          title: str, 
                          content: str, 
                          metadata: Optional[Dict[str, Any]] = None, 
                          owner_id: Optional[str] = None) -> bool:
        """
        Save a report to the database
        
        Args:
            report_id: Report ID
            title: Report title
            content: Report content
            metadata: Optional metadata
            owner_id: Optional owner ID
            
        Returns:
            bool: True if successful
        """
        try:
            # Serialize metadata
            metadata_json = json.dumps(metadata) if metadata else None
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if report already exists
                cursor.execute('SELECT id FROM reports WHERE id = ?', (report_id,))
                if cursor.fetchone():
                    # Update existing report
                    cursor.execute('''
                    UPDATE reports 
                    SET title = ?, content = ?, metadata = ?, owner_id = ?, 
                        updated_at = datetime('now')
                    WHERE id = ?
                    ''', (title, content, metadata_json, owner_id, report_id))
                else:
                    # Insert new report
                    cursor.execute('''
                    INSERT INTO reports (id, title, content, metadata, owner_id)
                    VALUES (?, ?, ?, ?, ?)
                    ''', (report_id, title, content, metadata_json, owner_id))
                
                # Invalidate cache
                cache_key = f"report:{report_id}"
                await self.invalidate_cache(cache_key)
                
                return True
                
        except Exception as e:
            logger.error(f"Error saving report {report_id}: {e}")
            return False
    
    async def get_report(self, report_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a report from the database
        
        Args:
            report_id: Report ID
            
        Returns:
            Optional[Dict[str, Any]]: Report data or None if not found
        """
        cache_key = f"report:{report_id}"
        
        # Try cache first
        cached = await self.get_from_cache(cache_key)
        if cached is not None:
            return cached
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                SELECT id, title, content, metadata, owner_id, created_at, updated_at
                FROM reports 
                WHERE id = ?
                ''', (report_id,))
                
                row = cursor.fetchone()
                if not row:
                    return None
                
                # Parse JSON metadata
                metadata = json.loads(row['metadata']) if row['metadata'] else {}
                
                # Create result
                result = {
                    'id': row['id'],
                    'title': row['title'],
                    'content': row['content'],
                    'metadata': metadata,
                    'owner_id': row['owner_id'],
                    'created_at': row['created_at'],
                    'updated_at': row['updated_at']
                }
                
                # Cache the result
                await self.set_in_cache(cache_key, result)
                
                return result
                
        except Exception as e:
            logger.error(f"Error getting report {report_id}: {e}")
            return None
    
    async def close(self):
        """Close all connections and stop background tasks"""
        self._shutdown_requested = True
        
        # Cancel cleanup task
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Close thread-local connections
        if hasattr(_local, 'connection'):
            try:
                _local.connection.close()
            except Exception as e:
                logger.error(f"Error closing database connection: {e}")
            finally:
                delattr(_local, 'connection')

# Global instance
db_connector = DBConnector()

def get_db_connector():
    """Get the global database connector instance"""
    return db_connector 