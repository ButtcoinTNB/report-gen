from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from database import AsyncSession, get_db
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Path,
    Query,
    status,
)
from models.task import (
    TaskList,
    TaskRequest,
    TaskStatus,
    TaskStatusResponse,
    TaskUpdateRequest,
)
from pydantic import UUID4, BaseModel
from services.task_manager import TaskManager, TaskNotFoundException
from services.task_service import TaskService
from services.task_service import get_task_service as get_service
from utils.logger import get_logger
from utils.validation import validate_object_id

logger = get_logger(__name__)

router = APIRouter(
    prefix="/tasks", tags=["tasks"], responses={404: {"description": "Task not found"}}
)


# Dependency for task service - Use imported get_service instead
# async def get_task_service(db: Database = Depends(get_db)):
#     return TaskService(db)


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
async def create_task(task_request: TaskRequest):
    """
    Create a new task.
    """
    try:
        task = TaskManager.create_task(
            stage=task_request.stage, metadata=task_request.metadata
        )
        return task
    except Exception as e:
        logger.exception("Error creating task")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create task: {str(e)}",
        )


@router.get("/{task_id}", response_model=TaskStatusResponse)
async def get_task(task_id: str):
    """
    Get task status by ID.
    """
    try:
        validate_object_id(task_id)
        task = TaskManager.get_task(task_id)
        return task
    except TaskNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Task {task_id} not found"
        )
    except Exception as e:
        logger.exception(f"Error getting task {task_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get task: {str(e)}",
        )


@router.get("/{task_id}/status", response_model=TaskApiResponse)
async def get_task_status(
    task_id: UUID4 = Path(..., description="The ID of the task to get status for"),
    task_service: TaskService = Depends(get_service),
    db: AsyncSession = Depends(get_db),
):
    """
    Get the current status of a task by its ID.
    """
    try:
        task = await task_service.get_task(db, task_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        return task
    except Exception as e:
        logger.error(f"Error getting task {task_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{task_id}/start", response_model=TaskStatusResponse)
async def start_task(task_id: str, background_tasks: BackgroundTasks):
    """
    Start a task.
    """
    try:
        validate_object_id(task_id)
        task = TaskManager.start_task(task_id)

        # Here we would typically add the actual task processing to background_tasks
        # For demonstration purposes, we'll just log it
        logger.info(f"Started task {task_id}")

        return task
    except TaskNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Task {task_id} not found"
        )
    except Exception as e:
        logger.exception(f"Error starting task {task_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start task: {str(e)}",
        )


@router.post("/{task_id}/update", response_model=TaskStatusResponse)
async def update_task(task_id: str, update: TaskUpdateRequest):
    """
    Update task status.
    """
    try:
        validate_object_id(task_id)
        task = TaskManager.update_task_status(task_id, update)
        return task
    except TaskNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Task {task_id} not found"
        )
    except Exception as e:
        logger.exception(f"Error updating task {task_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update task: {str(e)}",
        )


@router.post("/{task_id}/complete", response_model=TaskStatusResponse)
async def complete_task(task_id: str, report_id: Optional[str] = None):
    """
    Mark a task as completed.
    """
    try:
        validate_object_id(task_id)
        if report_id:
            validate_object_id(report_id)

        task = TaskManager.complete_task(task_id, report_id)
        return task
    except TaskNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Task {task_id} not found"
        )
    except Exception as e:
        logger.exception(f"Error completing task {task_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to complete task: {str(e)}",
        )


@router.post("/{task_id}/fail", response_model=TaskStatusResponse)
async def fail_task(task_id: str, error: str):
    """
    Mark a task as failed.
    """
    try:
        validate_object_id(task_id)
        task = TaskManager.fail_task(task_id, error)
        return task
    except TaskNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Task {task_id} not found"
        )
    except Exception as e:
        logger.exception(f"Error failing task {task_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to mark task as failed: {str(e)}",
        )


@router.post("/{task_id}/cancel", response_model=TaskStatusResponse)
async def cancel_task(
    task_id: UUID4 = Path(..., description="The ID of the task to cancel"),
    task_service: TaskService = Depends(get_service),
    db: AsyncSession = Depends(get_db),
):
    """
    Cancel a running task by its ID.
    """
    try:
        task = await task_service.cancel_task(db, task_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        return task
    except Exception as e:
        logger.error(f"Error cancelling task {task_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=TaskList)
async def list_tasks(
    status: Optional[str] = Query(None, description="Filter tasks by status"),
    limit: int = Query(
        10, ge=1, le=100, description="Maximum number of tasks to return"
    ),
    offset: int = Query(0, ge=0, description="Number of tasks to skip"),
    task_service: TaskService = Depends(get_service),
    db: AsyncSession = Depends(get_db),
):
    """
    List all tasks with optional filtering by status.
    """
    try:
        tasks = await task_service.list_tasks(
            db, status=status, limit=limit, offset=offset
        )
        total = await task_service.count_tasks(db, status=status)
        return TaskList(tasks=tasks, total=total)
    except Exception as e:
        logger.error(f"Error listing tasks: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clean", response_model=int)
async def clean_old_tasks(max_age_hours: int = 24):
    """
    Clean up old tasks.
    """
    try:
        count = TaskManager.clean_old_tasks(max_age_hours)
        return count
    except Exception as e:
        logger.exception("Error cleaning old tasks")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clean old tasks: {str(e)}",
        )


class TaskCreate(BaseModel):
    type: str
    params: Dict[str, Any]


@router.post("/", response_model=TaskApiResponse)
async def create_background_task(
    background_tasks: BackgroundTasks,
    task_type: str = Query(..., description="Type of task to create"),
    params: dict = Query({}, description="Parameters for the task"),
    task_service: TaskService = Depends(get_service),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new task and start executing it in the background.
    """
    try:
        # Create the task
        task = await task_service.create_task(db, task_type, params)

        # Start executing the task in the background
        background_tasks.add_task(task_service.execute_task, task.id)

        return TaskApiResponse(
            task_id=task.id,
            status=task.status,
            progress=task.progress,
            stage=task.stage,
            message=task.message,
            can_proceed=task.can_proceed,
        )
    except Exception as e:
        logger.error(f"Error creating task: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/expired", response_model=int)
async def cleanup_expired_tasks(
    days: int = Query(30, ge=1, description="Delete tasks older than this many days"),
    task_service: TaskService = Depends(get_service),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete expired tasks (admin only).
    """
    try:
        # Calculate the cutoff date
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # Delete expired tasks
        deleted_count = await task_service.delete_expired_tasks(db, cutoff_date)

        return deleted_count
    except Exception as e:
        logger.error(f"Error cleaning up expired tasks: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{task_id}/result", response_model=dict)
async def get_task_result(
    task_id: UUID4 = Path(..., description="The ID of the task to get the result for"),
    task_service: TaskService = Depends(get_service),
    db: AsyncSession = Depends(get_db),
):
    """
    Get the result of a completed task.
    """
    try:
        task = await task_service.get_task(db, task_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

        if task.status != TaskStatus.COMPLETED:
            raise HTTPException(
                status_code=400, detail=f"Task {task_id} is not completed"
            )

        if not task.result:
            raise HTTPException(
                status_code=404, detail=f"No result found for task {task_id}"
            )

        return task.result
    except Exception as e:
        logger.error(f"Error getting result for task {task_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
