import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from models.task import ProcessStage, TaskStatus, TaskStatusResponse, TaskUpdateRequest

logger = logging.getLogger(__name__)


class TaskNotFoundException(Exception):
    """Exception raised when a task is not found."""

    pass


class TaskManager:
    """
    Service for managing tasks across the system.
    Maintains task state in memory with methods to persist to database if needed.
    """

    # In-memory task store - in production this should be in a database
    _tasks: Dict[str, TaskStatusResponse] = {}

    @classmethod
    def create_task(
        cls, stage: ProcessStage, metadata: Optional[Dict[str, Any]] = None
    ) -> TaskStatusResponse:
        """
        Create a new task.

        Args:
            stage: The initial stage of the task
            metadata: Optional metadata to store with the task

        Returns:
            The created task
        """
        task_id = str(uuid.uuid4())
        now = datetime.now()

        task = TaskStatusResponse(
            task_id=task_id,
            status=TaskStatus.PENDING.value,
            stage=stage,
            progress=0,
            message=f"Task created, ready to start {stage.value} process",
            can_proceed=True,
            created_at=now,
            updated_at=now,
            metadata=metadata,
        )

        cls._tasks[task_id] = task
        logger.info(f"Created task {task_id} in stage {stage.value}")

        return task

    @classmethod
    def get_task(cls, task_id: str) -> TaskStatusResponse:
        """
        Get a task by ID.

        Args:
            task_id: The task ID

        Returns:
            The task

        Raises:
            TaskNotFoundException: If the task is not found
        """
        task = cls._tasks.get(task_id)
        if not task:
            raise TaskNotFoundException(f"Task {task_id} not found")

        return task

    @classmethod
    def update_task_status(
        cls, task_id: str, update: TaskUpdateRequest
    ) -> TaskStatusResponse:
        """
        Update a task's status.

        Args:
            task_id: The task ID
            update: The update data

        Returns:
            The updated task

        Raises:
            TaskNotFoundException: If the task is not found
        """
        task = cls.get_task(task_id)

        # Update task with non-None values from update
        update_data = update.dict(exclude_unset=True, exclude_none=True)

        # Handle update
        for key, value in update_data.items():
            setattr(task, key, value)

        # Always update the updated_at timestamp
        task.updated_at = datetime.now()

        # Handle task completion automatically if progress reaches 100%
        if task.progress >= 100 and task.status == TaskStatus.IN_PROGRESS.value:
            task.progress = 100
            task.status = TaskStatus.COMPLETED.value
            task.can_proceed = True
            task.message = f"{task.stage.value.capitalize()} process completed"

        # Save the updated task
        cls._tasks[task_id] = task

        logger.info(f"Updated task {task_id}: {update_data}")
        return task

    @classmethod
    def start_task(cls, task_id: str) -> TaskStatusResponse:
        """
        Start a task.

        Args:
            task_id: The task ID

        Returns:
            The updated task

        Raises:
            TaskNotFoundException: If the task is not found
        """
        task = cls.get_task(task_id)

        # Only start pending tasks
        if task.status != TaskStatus.PENDING.value:
            logger.warning(
                f"Attempted to start task {task_id} which is not in PENDING state (current: {task.status})"
            )
            return task

        # Update task
        update = TaskUpdateRequest(
            status=TaskStatus.IN_PROGRESS.value,
            progress=0,
            message=f"Starting {task.stage.value} process",
            can_proceed=False,
        )

        return cls.update_task_status(task_id, update)

    @classmethod
    def complete_task(
        cls, task_id: str, report_id: Optional[str] = None
    ) -> TaskStatusResponse:
        """
        Mark a task as completed.

        Args:
            task_id: The task ID
            report_id: Optional report ID to associate with the task

        Returns:
            The updated task

        Raises:
            TaskNotFoundException: If the task is not found
        """
        task = cls.get_task(task_id)

        # Update task
        update = TaskUpdateRequest(
            status=TaskStatus.COMPLETED.value,
            progress=100,
            message=f"{task.stage.value.capitalize()} process completed",
            can_proceed=True,
        )

        if report_id:
            update.report_id = report_id

        return cls.update_task_status(task_id, update)

    @classmethod
    def fail_task(cls, task_id: str, error: str) -> TaskStatusResponse:
        """
        Mark a task as failed.
        
        Args:
            task_id: The task ID
            error: Error message
            
        Returns:
            The updated task
            
        Raises:
            TaskNotFoundException: If the task is not found
        """
        # Check if task exists (will raise TaskNotFoundException if not found)
        cls.get_task(task_id)
        
        # Update task
        update = TaskUpdateRequest(
            status=TaskStatus.FAILED.value,
            message=f"Process failed: {error}",
            error=error,
            can_proceed=True,
        )
        
        return cls.update_task_status(task_id, update)
    
    @classmethod
    def cancel_task(cls, task_id: str) -> TaskStatusResponse:
        """
        Cancel a task.
        
        Args:
            task_id: The task ID
            
        Returns:
            The updated task
            
        Raises:
            TaskNotFoundException: If the task is not found
        """
        # Check if task exists (will raise TaskNotFoundException if not found)
        cls.get_task(task_id)
        
        # Update task
        update = TaskUpdateRequest(
            status=TaskStatus.CANCELLED.value,
            message="Process cancelled by user",
            can_proceed=True,
        )
        
        return cls.update_task_status(task_id, update)

    @classmethod
    def list_tasks(cls, limit: int = 100, offset: int = 0) -> List[TaskStatusResponse]:
        """
        List all tasks.

        Args:
            limit: Maximum number of tasks to return
            offset: Offset for pagination

        Returns:
            List of tasks
        """
        tasks = list(cls._tasks.values())
        tasks.sort(key=lambda t: t.created_at, reverse=True)

        return tasks[offset : offset + limit]

    @classmethod
    def clean_old_tasks(cls, max_age_hours: int = 24) -> int:
        """
        Remove tasks older than the specified age.

        Args:
            max_age_hours: Maximum age of tasks in hours

        Returns:
            Number of tasks removed
        """
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        task_ids_to_remove = []

        for task_id, task in cls._tasks.items():
            if task.created_at < cutoff_time:
                task_ids_to_remove.append(task_id)

        for task_id in task_ids_to_remove:
            del cls._tasks[task_id]

        logger.info(f"Cleaned up {len(task_ids_to_remove)} old tasks")
        return len(task_ids_to_remove)
