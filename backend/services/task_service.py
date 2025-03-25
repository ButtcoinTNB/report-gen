import asyncio
import uuid
from datetime import datetime, timedelta, UTC
from enum import Enum
from typing import Any, Dict, List, Optional, Callable, TypeVar, Generic, cast

from fastapi import Depends
from pydantic import UUID4
from postgrest._async.client import AsyncPostgrestClient

from database import get_db
from models.task import ProcessStage, Task, TaskStatus
from utils.logger import get_logger

logger = get_logger(__name__)

T = TypeVar('T', bound=Dict[str, Any])

class TaskType(str, Enum):
    DOCUMENT_PROCESSING = "document_processing"
    REPORT_GENERATION = "report_generation"
    REPORT_REFINEMENT = "report_refinement"
    REPORT_EXPORT = "report_export"


class TaskError(Exception):
    """Exception raised for errors in task operations."""
    pass


class TaskNotFoundError(TaskError):
    """Exception raised when a task is not found."""
    pass


class TaskService:
    """Service for managing long-running tasks with state tracking."""

    def __init__(self, db_client: AsyncPostgrestClient):
        self.db = db_client
        self._active_tasks: Dict[UUID4, asyncio.Task] = {}
        self._handlers = {
            TaskType.DOCUMENT_PROCESSING: self._handle_document_processing,
            TaskType.REPORT_GENERATION: self._handle_report_generation,
            TaskType.REPORT_REFINEMENT: self._handle_report_refinement,
            TaskType.REPORT_EXPORT: self._handle_report_export,
        }

    async def get_task(self, task_id: UUID4) -> Optional[Task[Dict[str, Any]]]:
        """Get a task by its ID."""
        try:
            response = await self.db.select("*").eq("id", str(task_id)).execute()
            if not response.data:
                logger.warning(f"Task {task_id} not found")
                return None
            return Task[Dict[str, Any]].model_validate(response.data[0])
        except Exception as e:
            logger.error(f"Error getting task {task_id}: {str(e)}")
            raise TaskError(f"Failed to get task: {str(e)}")

    async def create_task(self, task_type: str, params: Optional[Dict[str, Any]] = None) -> Task[Dict[str, Any]]:
        """Create a new task and store it in the database."""
        try:
            task_id = uuid.uuid4()
            created_at = datetime.now(UTC)
            expires_at = created_at + timedelta(days=30)  # Tasks expire after 30 days

            task_data = {
                "id": str(task_id),
                "type": task_type,
                "status": TaskStatus.PENDING,
                "stage": ProcessStage.IDLE,
                "progress": 0,
                "message": "Task created",
                "params": params or {},
                "created_at": created_at.isoformat(),
                "updated_at": created_at.isoformat(),
                "expires_at": expires_at.isoformat()
            }

            response = await self.db.insert(task_data).execute()
            if not response.data:
                raise TaskError("Failed to create task: No data returned")
            
            logger.info(f"Created task {task_id} of type {task_type}")
            return Task[Dict[str, Any]].model_validate(response.data[0])
        except Exception as e:
            logger.error(f"Error creating task: {str(e)}")
            raise TaskError(f"Failed to create task: {str(e)}")

    async def update_task(self, task_id: UUID4, updates: Dict[str, Any]) -> Optional[Task[Dict[str, Any]]]:
        """Update a task with new values."""
        try:
            updates["updated_at"] = datetime.now(UTC).isoformat()
            response = await self.db.update(updates).eq("id", str(task_id)).execute()
            if not response.data:
                return None
            return Task[Dict[str, Any]].model_validate(response.data[0])
        except Exception as e:
            logger.error(f"Error updating task {task_id}: {str(e)}")
            raise TaskError(f"Failed to update task: {str(e)}")

    async def cancel_task(self, task_id: UUID4) -> Optional[Task[Dict[str, Any]]]:
        """Cancel a running task."""
        try:
            task = await self.get_task(task_id)

            if not task:
                return None

            # Can only cancel tasks that are pending or in progress
            if task.status not in [TaskStatus.PENDING, TaskStatus.IN_PROGRESS]:
                logger.warning(
                    f"Cannot cancel task {task_id} with status {task.status}"
                )
                return task

            # Cancel the running asyncio task if it exists
            asyncio_task = self._active_tasks.get(task_id)
            if asyncio_task and not asyncio_task.done():
                asyncio_task.cancel()
                self._active_tasks.pop(task_id, None)

            # Update the task status
            return await self.update_task(
                task_id,
                {
                    "status": TaskStatus.CANCELLED,
                    "message": "Task cancelled by user",
                    "progress": task.progress,  # Preserve the current progress
                },
            )
        except Exception as e:
            logger.error(f"Error cancelling task {task_id}: {str(e)}")
            raise TaskError(f"Failed to cancel task: {str(e)}")

    async def list_tasks(
        self,
        status: Optional[str] = None,
        limit: int = 10,
        offset: int = 0,
    ) -> List[Task[Dict[str, Any]]]:
        """List tasks with optional filtering."""
        try:
            query = self.db.select("*").order("created_at", desc=True).limit(limit).offset(offset)
            
            if status:
                query = query.eq("status", status)
            
            response = await query.execute()
            return [Task[Dict[str, Any]].model_validate(task_data) for task_data in response.data]
        except Exception as e:
            logger.error(f"Error listing tasks: {str(e)}")
            raise TaskError(f"Failed to list tasks: {str(e)}")

    async def count_tasks(self, status: Optional[str] = None) -> int:
        """Count tasks with optional filtering."""
        try:
            query = self.db.select("count")
            if status:
                query = query.eq("status", status)
            
            response = await query.execute()
            return response.count or 0
        except Exception as e:
            logger.error(f"Error counting tasks: {str(e)}")
            raise TaskError(f"Failed to count tasks: {str(e)}")

    async def delete_expired_tasks(self, cutoff_date: datetime) -> int:
        """Delete tasks that have expired."""
        try:
            response = await self.db.delete().lt("expires_at", cutoff_date.isoformat()).execute()
            return len(response.data) if response.data else 0
        except Exception as e:
            logger.error(f"Error deleting expired tasks: {str(e)}")
            raise TaskError(f"Failed to delete expired tasks: {str(e)}")

    async def execute_task(self, task_id: UUID4) -> None:
        """Execute a task in the background."""
        try:
            task = await self.get_task(task_id)

            if not task:
                logger.error(f"Cannot execute task {task_id}: Task not found")
                return

            # Mark task as in progress
            await self.update_task(
                task_id,
                {
                    "status": TaskStatus.IN_PROGRESS,
                    "message": f"Started {task.type} process",
                    "stage": (
                        ProcessStage.EXTRACTION
                        if task.type == "report_generation"
                        else ProcessStage.IDLE
                    ),
                },
            )

            # Execute the appropriate task handler based on task type
            result = None
            if task.type == "document_processing":
                result = await self._handle_document_processing(task)
            elif task.type == "report_generation":
                result = await self._handle_report_generation(task)
            elif task.type == "report_refinement":
                result = await self._handle_report_refinement(task)
            elif task.type == "report_export":
                result = await self._handle_report_export(task)
            else:
                # Unknown task type
                await self.update_task(
                    task_id,
                    {
                        "status": TaskStatus.FAILED,
                        "message": f"Unknown task type: {task.type}",
                        "error": f"Unsupported task type: {task.type}",
                    },
                )
                return

            # Mark task as completed
            await self.update_task(
                task_id,
                {
                    "status": TaskStatus.COMPLETED,
                    "progress": 100,
                    "message": f"Completed {task.type} process",
                    "result": result or {},
                },
            )

        except asyncio.CancelledError:
            # Task was cancelled
            logger.info(f"Task {task_id} was cancelled")
            # We don't need to update the DB as cancel_task already did that
        except Exception as e:
            # Task failed with an error
            logger.error(f"Error executing task {task_id}: {str(e)}")
            try:
                await self.update_task(
                    task_id,
                    {
                        "status": TaskStatus.FAILED,
                        "message": f"Task failed: {str(e)}",
                        "error": str(e),
                    },
                )
            except Exception as update_error:
                logger.error(
                    f"Error updating failed task {task_id}: {str(update_error)}"
                )
        finally:
            # Remove the task from active tasks
            self._active_tasks.pop(task_id, None)

    async def _handle_document_processing(self, task: Task[Dict[str, Any]]) -> Dict[str, Any]:
        """Handle document processing task."""
        # Simulate document processing steps
        await self._update_progress(task.id, 10, "Extracting text from documents", ProcessStage.EXTRACTION)
        await asyncio.sleep(2)  # Simulate work

        await self._update_progress(task.id, 40, "Analyzing document content", ProcessStage.ANALYSIS)
        await asyncio.sleep(3)  # Simulate work

        await self._update_progress(task.id, 70, "Organizing data", ProcessStage.ANALYSIS)
        await asyncio.sleep(2)  # Simulate work

        return {"status": "success", "processed_documents": 1}

    async def _handle_report_generation(self, task: Task[Dict[str, Any]]) -> Dict[str, Any]:
        """Handle report generation task."""
        # Simulate report generation steps
        await self._update_progress(task.id, 10, "Analyzing documents", ProcessStage.ANALYSIS)
        await asyncio.sleep(2)  # Simulate work

        await self._update_progress(task.id, 30, "Generating initial report draft", ProcessStage.WRITER)
        await asyncio.sleep(3)  # Simulate work

        await self._update_progress(task.id, 60, "Reviewing report content", ProcessStage.REVIEWER)
        await asyncio.sleep(2)  # Simulate work

        await self._update_progress(task.id, 80, "Finalizing report", ProcessStage.FORMATTING)
        await asyncio.sleep(2)  # Simulate work

        return {"status": "success", "report_id": str(uuid.uuid4())}

    async def _handle_report_refinement(self, task: Task[Dict[str, Any]]) -> Dict[str, Any]:
        """Handle report refinement task."""
        # Simulate refinement steps
        await self._update_progress(task.id, 20, "Analyzing refinement instructions", ProcessStage.ANALYSIS)
        await asyncio.sleep(2)  # Simulate work

        await self._update_progress(task.id, 50, "Applying refinements to report", ProcessStage.REFINEMENT)
        await asyncio.sleep(3)  # Simulate work

        await self._update_progress(task.id, 80, "Formatting updated report", ProcessStage.FORMATTING)
        await asyncio.sleep(2)  # Simulate work

        return {"status": "success", "refinements_applied": True}

    async def _handle_report_export(self, task: Task[Dict[str, Any]]) -> Dict[str, Any]:
        """Handle report export task."""
        # Simulate export steps
        await self._update_progress(task.id, 30, "Preparing report for export", ProcessStage.FORMATTING)
        await asyncio.sleep(2)  # Simulate work

        await self._update_progress(task.id, 70, "Generating final document", ProcessStage.FINALIZATION)
        await asyncio.sleep(2)  # Simulate work

        return {"status": "success", "export_url": f"https://example.com/reports/{task.id}"}

    async def _update_progress(
        self,
        task_id: UUID4,
        progress: int,
        message: str,
        stage: Optional[ProcessStage] = None,
    ) -> None:
        """Update task progress."""
        updates = {"progress": progress, "message": message}
        if stage:
            updates["stage"] = stage

        await self.update_task(task_id, updates)


async def get_task_service(db: Callable[[str], AsyncPostgrestClient] = Depends(get_db)) -> TaskService:
    """Get a TaskService instance."""
    return TaskService(db("tasks"))  # Use the tasks table
