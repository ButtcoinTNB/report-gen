from typing import Dict, Optional, Any, Callable, Awaitable
import asyncio
from datetime import datetime, timedelta
import threading
from collections import deque
from ..utils.monitoring import monitor_task, logger, CircuitBreaker
from fastapi import HTTPException, status

class TaskManager:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
            return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.active_tasks: Dict[str, asyncio.Task] = {}
            self.task_metadata: Dict[str, Dict[str, Any]] = {}
            self.task_history = deque(maxlen=100)  # Keep last 100 tasks
            self.max_concurrent_tasks = 10
            self.max_task_duration = 3600  # 1 hour
            self.circuit_breaker = CircuitBreaker()
            self.initialized = True
    
    @monitor_task("task_manager_schedule")
    async def schedule_task(
        self,
        task_id: str,
        coroutine: Callable[..., Awaitable[Any]],
        *args,
        **kwargs
    ) -> str:
        """Schedule a task with proper resource management"""
        if len(self.active_tasks) >= self.max_concurrent_tasks:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Maximum concurrent tasks reached"
            )
        
        # Create task metadata
        self.task_metadata[task_id] = {
            'start_time': datetime.now(),
            'status': 'scheduled',
            'error': None
        }
        
        # Create and schedule the task with timeout
        task = asyncio.create_task(self._run_task_with_timeout(
            task_id,
            coroutine,
            *args,
            **kwargs
        ))
        
        self.active_tasks[task_id] = task
        return task_id
    
    async def _run_task_with_timeout(
        self,
        task_id: str,
        coroutine: Callable[..., Awaitable[Any]],
        *args,
        **kwargs
    ):
        """Run a task with timeout and resource cleanup"""
        try:
            # Run the task with timeout
            result = await asyncio.wait_for(
                coroutine(*args, **kwargs),
                timeout=self.max_task_duration
            )
            
            # Update metadata for successful completion
            self.task_metadata[task_id].update({
                'status': 'completed',
                'completion_time': datetime.now(),
                'result': result
            })
            
        except asyncio.TimeoutError:
            logger.error(f"Task {task_id} timed out after {self.max_task_duration} seconds")
            self.task_metadata[task_id].update({
                'status': 'timeout',
                'error': 'Task exceeded maximum duration'
            })
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Task timed out"
            )
            
        except Exception as e:
            logger.exception(f"Task {task_id} failed: {str(e)}")
            self.task_metadata[task_id].update({
                'status': 'failed',
                'error': str(e)
            })
            raise
            
        finally:
            # Cleanup
            if task_id in self.active_tasks:
                del self.active_tasks[task_id]
            
            # Archive task metadata
            if task_id in self.task_metadata:
                self.task_history.append(self.task_metadata[task_id])
                del self.task_metadata[task_id]
    
    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get status of a task"""
        if task_id in self.task_metadata:
            return self.task_metadata[task_id]
        
        # Check history for completed tasks
        for task_data in self.task_history:
            if task_data.get('task_id') == task_id:
                return task_data
                
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found"
        )
    
    async def update_task_status(
        self, 
        task_id: str, 
        status: Optional[str] = None,
        message: Optional[str] = None,
        progress: Optional[float] = None,
        stage: Optional[str] = None,
        time_remaining: Optional[int] = None,
        quality_score: Optional[float] = None,
        iterations: Optional[int] = None,
        error: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update the status of a task"""
        if task_id not in self.task_metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found"
            )
        
        # Update task metadata with provided values
        task_metadata = self.task_metadata[task_id]
        
        if status is not None:
            task_metadata["status"] = status
            
            # Record completion time if task is being completed or failed
            if status in ["completed", "failed", "cancelled"]:
                task_metadata["completion_time"] = datetime.now()
        
        if message is not None:
            task_metadata["message"] = message
        
        if progress is not None:
            task_metadata["progress"] = progress
        
        if stage is not None:
            task_metadata["stage"] = stage
        
        if time_remaining is not None:
            task_metadata["estimated_time_remaining"] = time_remaining
        
        if quality_score is not None:
            task_metadata["quality"] = quality_score
        
        if iterations is not None:
            task_metadata["iterations"] = iterations
        
        if error is not None:
            task_metadata["error"] = error
        
        # Update last modified time
        task_metadata["updated_at"] = datetime.now()
        
        # Log update
        logger.info(f"Task {task_id} status updated: {status or task_metadata.get('status')}")
        
        return task_metadata
    
    async def cancel_task(self, task_id: str) -> None:
        """Cancel a running task"""
        if task_id not in self.active_tasks:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found"
            )
            
        task = self.active_tasks[task_id]
        task.cancel()
        
        try:
            await task
        except asyncio.CancelledError:
            self.task_metadata[task_id].update({
                'status': 'cancelled',
                'completion_time': datetime.now()
            })
        
        # Cleanup
        if task_id in self.active_tasks:
            del self.active_tasks[task_id]
    
    async def cleanup_old_tasks(self):
        """Cleanup tasks older than 24 hours"""
        current_time = datetime.now()
        tasks_to_remove = []
        
        for task_id, metadata in self.task_metadata.items():
            start_time = metadata.get('start_time')
            if start_time and (current_time - start_time) > timedelta(hours=24):
                tasks_to_remove.append(task_id)
        
        for task_id in tasks_to_remove:
            if task_id in self.active_tasks:
                await self.cancel_task(task_id)
            else:
                del self.task_metadata[task_id] 