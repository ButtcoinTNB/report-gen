import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Union
import uuid
from enum import Enum
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func
from pydantic import UUID4

from ..database import Database, transaction
from ..models.task import Task, TaskStatus, ProcessStage
from ..utils.logger import get_logger
from ..services.report_service import ReportService
from ..services.document_service import DocumentService
from ..db.database import get_db

logger = get_logger(__name__)

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
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.report_service = ReportService(db)
        self.document_service = DocumentService(db)
        self._active_tasks: Dict[UUID4, asyncio.Task] = {}
        self._handlers = {
            TaskType.DOCUMENT_PROCESSING: self._handle_document_processing,
            TaskType.REPORT_GENERATION: self._handle_report_generation,
            TaskType.REPORT_REFINEMENT: self._handle_report_refinement,
            TaskType.REPORT_EXPORT: self._handle_report_export
        }
    
    async def get_task(self, db: AsyncSession, task_id: UUID4) -> Optional[Task]:
        """Get a task by its ID."""
        try:
            result = await db.execute(select(Task).where(Task.id == task_id))
            task = result.scalars().first()
            
            if not task:
                logger.warning(f"Task {task_id} not found")
                return None
                
            return task
        except Exception as e:
            logger.error(f"Error getting task {task_id}: {str(e)}")
            raise TaskError(f"Failed to get task: {str(e)}")
    
    async def create_task(
        self, 
        db: AsyncSession,
        task_type: str, 
        params: Dict[str, Any] = None
    ) -> Task:
        """Create a new task and store it in the database."""
        try:
            task_id = uuid.uuid4()
            created_at = datetime.utcnow()
            expires_at = created_at + datetime.timedelta(days=30)  # Tasks expire after 30 days
            
            task = Task(
                id=task_id,
                type=task_type,
                status=TaskStatus.PENDING,
                stage=ProcessStage.IDLE,
                progress=0,
                message="Task created",
                params=params or {},
                created_at=created_at,
                updated_at=created_at,
                expires_at=expires_at
            )
            
            db.add(task)
            await db.commit()
            await db.refresh(task)
            
            logger.info(f"Created task {task_id} of type {task_type}")
            return task
        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating task: {str(e)}")
            raise TaskError(f"Failed to create task: {str(e)}")
    
    async def update_task(
        self, 
        db: AsyncSession,
        task_id: UUID4, 
        updates: Dict[str, Any]
    ) -> Optional[Task]:
        """Update a task with new values."""
        try:
            # Update the task
            updates["updated_at"] = datetime.utcnow()
            await db.execute(
                update(Task)
                .where(Task.id == task_id)
                .values(**updates)
            )
            await db.commit()
            
            # Fetch the updated task
            return await self.get_task(self.db, task_id)
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating task {task_id}: {str(e)}")
            raise TaskError(f"Failed to update task: {str(e)}")
    
    async def cancel_task(self, db: AsyncSession, task_id: UUID4) -> Optional[Task]:
        """Cancel a running task."""
        try:
            task = await self.get_task(self.db, task_id)
            
            if not task:
                return None
            
            # Can only cancel tasks that are pending or in progress
            if task.status not in [TaskStatus.PENDING, TaskStatus.IN_PROGRESS]:
                logger.warning(f"Cannot cancel task {task_id} with status {task.status}")
                return task
            
            # Cancel the running asyncio task if it exists
            asyncio_task = self._active_tasks.get(task_id)
            if asyncio_task and not asyncio_task.done():
                asyncio_task.cancel()
                self._active_tasks.pop(task_id, None)
            
            # Update the task status
            return await self.update_task(
                self.db,
                task_id, 
                {
                    "status": TaskStatus.CANCELLED,
                    "message": "Task cancelled by user",
                    "progress": task.progress  # Preserve the current progress
                }
            )
        except Exception as e:
            logger.error(f"Error cancelling task {task_id}: {str(e)}")
            raise TaskError(f"Failed to cancel task: {str(e)}")
    
    async def list_tasks(
        self, 
        db: AsyncSession,
        status: Optional[TaskStatus] = None,
        limit: int = 10,
        offset: int = 0
    ) -> List[Task]:
        """List tasks with optional filtering."""
        try:
            query = select(Task).order_by(Task.created_at.desc())
            
            if status:
                query = query.where(Task.status == status)
            
            query = query.limit(limit).offset(offset)
            result = await db.execute(query)
            
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Error listing tasks: {str(e)}")
            raise TaskError(f"Failed to list tasks: {str(e)}")
    
    async def count_tasks(
        self, 
        db: AsyncSession,
        status: Optional[TaskStatus] = None
    ) -> int:
        """Count tasks with optional filtering."""
        try:
            query = select(func.count()).select_from(Task)
            
            if status:
                query = query.where(Task.status == status)
            
            result = await db.execute(query)
            return result.scalar() or 0
        except Exception as e:
            logger.error(f"Error counting tasks: {str(e)}")
            raise TaskError(f"Failed to count tasks: {str(e)}")
    
    async def delete_expired_tasks(
        self, 
        db: AsyncSession,
        cutoff_date: datetime
    ) -> int:
        """Delete tasks that have expired."""
        try:
            # Delete expired tasks
            result = await db.execute(
                delete(Task).where(Task.expires_at < cutoff_date)
            )
            await db.commit()
            
            deleted_count = result.rowcount
            logger.info(f"Deleted {deleted_count} expired tasks")
            
            return deleted_count
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error deleting expired tasks: {str(e)}")
            raise TaskError(f"Failed to delete expired tasks: {str(e)}")
    
    async def execute_task(self, task_id: UUID4) -> None:
        """Execute a task in the background."""
        async with AsyncSession() as db:
            try:
                task = await self.get_task(db, task_id)
                
                if not task:
                    logger.error(f"Cannot execute task {task_id}: Task not found")
                    return
                
                # Mark task as in progress
                await self.update_task(
                    db,
                    task_id, 
                    {
                        "status": TaskStatus.IN_PROGRESS,
                        "message": f"Started {task.type} process",
                        "stage": ProcessStage.EXTRACTION if task.type == "report_generation" else ProcessStage.IDLE
                    }
                )
                
                # Execute the appropriate task handler based on task type
                result = None
                if task.type == "document_processing":
                    result = await self._handle_document_processing(db, task)
                elif task.type == "report_generation":
                    result = await self._handle_report_generation(db, task)
                elif task.type == "report_refinement":
                    result = await self._handle_report_refinement(db, task)
                elif task.type == "report_export":
                    result = await self._handle_report_export(db, task)
                else:
                    # Unknown task type
                    await self.update_task(
                        db,
                        task_id, 
                        {
                            "status": TaskStatus.FAILED,
                            "message": f"Unknown task type: {task.type}",
                            "error": f"Unsupported task type: {task.type}"
                        }
                    )
                    return
                
                # Mark task as completed
                await self.update_task(
                    db,
                    task_id, 
                    {
                        "status": TaskStatus.COMPLETED,
                        "progress": 100,
                        "message": f"Completed {task.type} process",
                        "result": result or {}
                    }
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
                        db,
                        task_id, 
                        {
                            "status": TaskStatus.FAILED,
                            "message": f"Task failed: {str(e)}",
                            "error": str(e)
                        }
                    )
                except Exception as update_error:
                    logger.error(f"Error updating failed task {task_id}: {str(update_error)}")
            finally:
                # Remove the task from active tasks
                self._active_tasks.pop(task_id, None)
    
    async def _handle_document_processing(
        self, 
        db: AsyncSession,
        task: Task
    ) -> Dict[str, Any]:
        """Handle document processing task."""
        file_ids = task.params.get("file_ids", [])
        
        if not file_ids:
            raise ValueError("No file IDs provided for document processing")
        
        # Simulate document processing steps
        await self._update_progress(db, task.id, 10, "Extracting text from documents", ProcessStage.EXTRACTION)
        await asyncio.sleep(2)  # Simulate work
        
        await self._update_progress(db, task.id, 40, "Analyzing document content", ProcessStage.ANALYSIS)
        await asyncio.sleep(3)  # Simulate work
        
        await self._update_progress(db, task.id, 70, "Organizing data", ProcessStage.ANALYSIS)
        await asyncio.sleep(2)  # Simulate work
        
        # Return the result
        return {
            "processed_files": len(file_ids),
            "extracted_pages": len(file_ids) * 5,  # Simulate 5 pages per file
            "file_ids": file_ids
        }
    
    async def _handle_report_generation(
        self, 
        db: AsyncSession,
        task: Task
    ) -> Dict[str, Any]:
        """Handle report generation task."""
        file_ids = task.params.get("file_ids", [])
        
        if not file_ids:
            raise ValueError("No file IDs provided for report generation")
        
        # Simulate report generation steps
        await self._update_progress(db, task.id, 10, "Analyzing documents", ProcessStage.ANALYSIS)
        await asyncio.sleep(2)  # Simulate work
        
        await self._update_progress(db, task.id, 30, "Generating initial report draft", ProcessStage.WRITER)
        await asyncio.sleep(3)  # Simulate work
        
        await self._update_progress(db, task.id, 60, "Reviewing report content", ProcessStage.REVIEWER)
        await asyncio.sleep(2)  # Simulate work
        
        await self._update_progress(db, task.id, 80, "Finalizing report", ProcessStage.FORMATTING)
        await asyncio.sleep(2)  # Simulate work
        
        # Create a mock report ID
        report_id = str(uuid.uuid4())
        
        # Return the result
        return {
            "report_id": report_id,
            "file_count": len(file_ids),
            "word_count": 1200,  # Mock word count
            "page_count": 10  # Mock page count
        }
    
    async def _handle_report_refinement(
        self, 
        db: AsyncSession,
        task: Task
    ) -> Dict[str, Any]:
        """Handle report refinement task."""
        report_id = task.params.get("report_id")
        instructions = task.params.get("instructions")
        
        if not report_id:
            raise ValueError("No report ID provided for refinement")
        
        if not instructions:
            raise ValueError("No refinement instructions provided")
        
        # Simulate refinement steps
        await self._update_progress(db, task.id, 20, "Analyzing refinement instructions", ProcessStage.ANALYSIS)
        await asyncio.sleep(2)  # Simulate work
        
        await self._update_progress(db, task.id, 50, "Applying refinements to report", ProcessStage.REFINEMENT)
        await asyncio.sleep(3)  # Simulate work
        
        await self._update_progress(db, task.id, 80, "Formatting updated report", ProcessStage.FORMATTING)
        await asyncio.sleep(2)  # Simulate work
        
        # Create a mock version ID
        version_id = str(uuid.uuid4())
        
        # Return the result
        return {
            "report_id": report_id,
            "version_id": version_id,
            "changes_applied": True,
            "refinement_count": 1
        }
    
    async def _handle_report_export(
        self, 
        db: AsyncSession,
        task: Task
    ) -> Dict[str, Any]:
        """Handle report export task."""
        report_id = task.params.get("report_id")
        version_id = task.params.get("version_id")
        format = task.params.get("format", "docx")
        
        if not report_id:
            raise ValueError("No report ID provided for export")
        
        # Simulate export steps
        await self._update_progress(db, task.id, 30, f"Preparing report for {format} export", ProcessStage.FORMATTING)
        await asyncio.sleep(2)  # Simulate work
        
        await self._update_progress(db, task.id, 70, "Generating final document", ProcessStage.FINALIZATION)
        await asyncio.sleep(2)  # Simulate work
        
        # Create a mock file URL
        file_url = f"/api/downloads/{uuid.uuid4()}.{format}"
        
        # Return the result
        return {
            "report_id": report_id,
            "version_id": version_id,
            "format": format,
            "file_url": file_url,
            "file_size": 1024 * 1024  # Mock file size (1MB)
        }
    
    async def _update_progress(
        self, 
        db: AsyncSession,
        task_id: UUID4, 
        progress: int, 
        message: str,
        stage: Optional[ProcessStage] = None
    ) -> None:
        """Update a task's progress."""
        updates = {
            "progress": progress,
            "message": message
        }
        
        if stage:
            updates["stage"] = stage
        
        await self.update_task(self.db, task_id, updates)


# Dependency to get task service instance
async def get_task_service(db: AsyncSession = Depends(get_db)) -> TaskService:
    return TaskService(db) 