from datetime import datetime, timedelta, UTC
from typing import Any, Dict, Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Path,
    Query,
    status,
)
from pydantic import UUID4, BaseModel

from models.task import (
    TaskList,
    TaskRequest,
    TaskStatus,
    TaskStatusResponse,
    TaskUpdateRequest,
)
from services.task_service import TaskService, get_task_service
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/tasks", tags=["tasks"], responses={404: {"description": "Task not found"}}
)


# Define a local TaskStatusResponse for the API with additional fields
class TaskApiResponse(BaseModel):
    task_id: str
    status: str
    progress: Optional[float] = None
    stage: Optional[str] = None
    message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    estimated_time_remaining: Optional[int] = None
    quality: Optional[float] = None
    iterations: Optional[int] = None
    can_proceed: bool = True


@router.post("", response_model=TaskStatusResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_request: TaskRequest,
    task_service: TaskService = Depends(get_task_service)
):
    """
    Create a new task.
    """
    try:
        task = await task_service.create_task(
            task_type=task_request.stage,
            params=task_request.metadata or {}
        )
        return TaskStatusResponse(
            task_id=str(task.id),
            status=task.status,
            progress=task.progress,
            stage=task.stage,
            message=task.message,
            result=task.result,
            error=task.error,
            estimated_time_remaining=task.estimated_time_remaining,
            quality=task.quality,
            iterations=task.iterations,
            can_proceed=task.can_proceed
        )
    except Exception as e:
        logger.exception("Error creating task")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create task: {str(e)}",
        )


@router.get("/{task_id}", response_model=TaskStatusResponse)
async def get_task(
    task_id: UUID4 = Path(..., description="The ID of the task to get"),
    task_service: TaskService = Depends(get_task_service)
):
    """
    Get task status by ID.
    """
    try:
        task = await task_service.get_task(task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found"
            )
        return TaskStatusResponse(
            task_id=str(task.id),
            status=task.status,
            progress=task.progress,
            stage=task.stage,
            message=task.message,
            result=task.result,
            error=task.error,
            estimated_time_remaining=task.estimated_time_remaining,
            quality=task.quality,
            iterations=task.iterations,
            can_proceed=task.can_proceed
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error getting task {task_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get task: {str(e)}",
        )


@router.get("/{task_id}/status", response_model=TaskApiResponse)
async def get_task_status(
    task_id: UUID4 = Path(..., description="The ID of the task to get status for"),
    task_service: TaskService = Depends(get_task_service),
):
    """
    Get the current status of a task by its ID.
    """
    try:
        task = await task_service.get_task(task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found"
            )
        return task
    except Exception as e:
        logger.error(f"Error getting task {task_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


class BackgroundTaskRequest(BaseModel):
    """Request model for creating a background task."""
    task_type: str
    params: Dict[str, Any] = {}


@router.post("/", response_model=TaskStatusResponse)
async def create_background_task(
    background_tasks: BackgroundTasks,
    request: BackgroundTaskRequest,
    task_service: TaskService = Depends(get_task_service),
):
    """
    Create a new task and start executing it in the background.
    """
    try:
        # Create the task
        task = await task_service.create_task(request.task_type, request.params)

        # Start executing the task in the background
        background_tasks.add_task(task_service.execute_task, task.id)

        return TaskStatusResponse(
            task_id=str(task.id),
            status=task.status,
            progress=task.progress,
            stage=task.stage,
            message=task.message,
            result=task.result,
            error=task.error,
            estimated_time_remaining=task.estimated_time_remaining,
            quality=task.quality,
            iterations=task.iterations,
            can_proceed=task.can_proceed
        )
    except Exception as e:
        logger.error(f"Error creating task: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/{task_id}/start", response_model=TaskStatusResponse)
async def start_task(
    background_tasks: BackgroundTasks,
    task_id: UUID4 = Path(..., description="The ID of the task to start"),
    task_service: TaskService = Depends(get_task_service),
):
    """
    Start a task.
    """
    try:
        task = await task_service.get_task(task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found"
            )

        # Add task execution to background tasks
        background_tasks.add_task(task_service.execute_task, task_id)
        
        # Update task status to in progress
        task = await task_service.update_task(
            task_id,
            {
                "status": TaskStatus.IN_PROGRESS,
                "message": "Task started",
            }
        )
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found"
            )
        return TaskStatusResponse(
            task_id=str(task.id),
            status=task.status,
            progress=task.progress,
            stage=task.stage,
            message=task.message,
            result=task.result,
            error=task.error,
            estimated_time_remaining=task.estimated_time_remaining,
            quality=task.quality,
            iterations=task.iterations,
            can_proceed=task.can_proceed
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error starting task {task_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start task: {str(e)}",
        )


@router.post("/{task_id}/update", response_model=TaskStatusResponse)
async def update_task(
    update: TaskUpdateRequest,
    task_id: UUID4 = Path(..., description="The ID of the task to update"),
    task_service: TaskService = Depends(get_task_service),
):
    """
    Update task status.
    """
    try:
        task = await task_service.update_task(task_id, update.model_dump())
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found"
            )
        return TaskStatusResponse(
            task_id=str(task.id),
            status=task.status,
            progress=task.progress,
            stage=task.stage,
            message=task.message,
            result=task.result,
            error=task.error,
            estimated_time_remaining=task.estimated_time_remaining,
            quality=task.quality,
            iterations=task.iterations,
            can_proceed=task.can_proceed
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error updating task {task_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update task: {str(e)}",
        )


@router.post("/{task_id}/complete", response_model=TaskStatusResponse)
async def complete_task(
    task_id: UUID4 = Path(..., description="The ID of the task to complete"),
    task_service: TaskService = Depends(get_task_service),
    report_id: Optional[UUID4] = None,
):
    """
    Mark a task as completed.
    """
    try:
        task = await task_service.update_task(
            task_id,
            {
                "status": TaskStatus.COMPLETED,
                "progress": 100,
                "message": "Task completed",
                "result": {"report_id": str(report_id)} if report_id else None
            }
        )
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found"
            )
        return TaskStatusResponse(
            task_id=str(task.id),
            status=task.status,
            progress=task.progress,
            stage=task.stage,
            message=task.message,
            result=task.result,
            error=task.error,
            estimated_time_remaining=task.estimated_time_remaining,
            quality=task.quality,
            iterations=task.iterations,
            can_proceed=task.can_proceed
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error completing task {task_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to complete task: {str(e)}",
        )


@router.post("/{task_id}/fail", response_model=TaskStatusResponse)
async def fail_task(
    task_id: UUID4 = Path(..., description="The ID of the task to fail"),
    task_service: TaskService = Depends(get_task_service),
    error: str = Query(..., description="Error message for the failed task"),
):
    """
    Mark a task as failed.
    """
    try:
        task = await task_service.update_task(
            task_id,
            {
                "status": TaskStatus.FAILED,
                "message": "Task failed",
                "error": error
            }
        )
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found"
            )
        return TaskStatusResponse(
            task_id=str(task.id),
            status=task.status,
            progress=task.progress,
            stage=task.stage,
            message=task.message,
            result=task.result,
            error=task.error,
            estimated_time_remaining=task.estimated_time_remaining,
            quality=task.quality,
            iterations=task.iterations,
            can_proceed=task.can_proceed
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error failing task {task_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fail task: {str(e)}",
        )


@router.get("", response_model=TaskList)
async def list_tasks(
    status: Optional[str] = Query(None, description="Filter tasks by status"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of tasks to return"),
    offset: int = Query(0, ge=0, description="Number of tasks to skip"),
    task_service: TaskService = Depends(get_task_service),
):
    """
    List tasks with optional filtering.
    """
    try:
        tasks = await task_service.list_tasks(status=status, limit=limit, offset=offset)
        total = await task_service.count_tasks(status=status)
        return TaskList(tasks=tasks, total=total)
    except Exception as e:
        logger.error(f"Error listing tasks: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list tasks: {str(e)}",
        )


@router.post("/clean", response_model=int)
async def clean_old_tasks(
    max_age_hours: int = Query(24, ge=1, description="Delete tasks older than this many hours"),
    task_service: TaskService = Depends(get_task_service)
):
    """
    Clean up old tasks.
    """
    try:
        cutoff_date = datetime.now(UTC) - timedelta(hours=max_age_hours)
        deleted_count = await task_service.delete_expired_tasks(cutoff_date)
        return deleted_count
    except Exception as e:
        logger.error(f"Error cleaning old tasks: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clean old tasks: {str(e)}",
        )


class TaskCreate(BaseModel):
    type: str
    params: Dict[str, Any]


@router.delete("/expired", response_model=int)
async def cleanup_expired_tasks(
    days: int = Query(30, ge=1, description="Delete tasks older than this many days"),
    task_service: TaskService = Depends(get_task_service),
):
    """
    Delete expired tasks (admin only).
    """
    try:
        # Calculate the cutoff date
        cutoff_date = datetime.now(UTC) - timedelta(days=days)

        # Delete expired tasks
        deleted_count = await task_service.delete_expired_tasks(cutoff_date)

        return deleted_count
    except Exception as e:
        logger.error(f"Error cleaning up expired tasks: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/{task_id}/result", response_model=Dict[str, Any])
async def get_task_result(
    task_id: UUID4 = Path(..., description="The ID of the task to get the result for"),
    task_service: TaskService = Depends(get_task_service),
):
    """
    Get the result of a completed task.
    """
    try:
        task = await task_service.get_task(task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found"
            )

        if task.status != TaskStatus.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Task {task_id} is not completed"
            )

        if not task.result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No result found for task {task_id}"
            )

        return task.result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting result for task {task_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
