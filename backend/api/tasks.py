from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import Dict, Any, Optional
from pydantic import BaseModel
from ..services.task_manager import task_manager
from ..dependencies import get_settings
import uuid

router = APIRouter(prefix="/tasks", tags=["tasks"])

class TaskStatus(BaseModel):
    task_id: str
    status: str
    message: str
    progress: Optional[float] = None
    current_stage: Optional[str] = None
    time_remaining: Optional[int] = None
    quality_score: Optional[float] = None
    iterations: Optional[int] = None
    error: Optional[str] = None
    
class TaskResponse(BaseModel):
    task_id: str

class TaskUpdateRequest(BaseModel):
    status: Optional[str] = None
    message: Optional[str] = None
    progress: Optional[float] = None
    stage: Optional[str] = None
    time_remaining: Optional[int] = None
    quality_score: Optional[float] = None
    iterations: Optional[int] = None
    error: Optional[str] = None

@router.get("/{task_id}", response_model=TaskStatus)
async def get_task_status(task_id: str) -> TaskStatus:
    """
    Get the status of a running task.
    """
    try:
        status = await task_manager.get_task_status(task_id)
        
        # Ensure proper handling of all fields
        return TaskStatus(
            task_id=task_id,
            status=status.get("status", "unknown"),
            message=status.get("message", ""),
            progress=status.get("progress", 0),
            current_stage=status.get("stage", ""),
            time_remaining=status.get("estimated_time_remaining"),
            quality_score=status.get("quality"),
            iterations=status.get("iterations"),
            error=status.get("error")
        )
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=404,
                detail=f"Task {task_id} not found"
            )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve task status: {str(e)}"
        )

@router.post("/{task_id}/update", response_model=TaskStatus)
async def update_task(task_id: str, update: TaskUpdateRequest) -> TaskStatus:
    """
    Update the status of a running task.
    """
    try:
        update_dict = update.dict(exclude_unset=True)
        
        # Update the task status
        updated_status = await task_manager.update_task_status(
            task_id, 
            **update_dict
        )
        
        # Return the updated task status
        return TaskStatus(
            task_id=task_id,
            status=updated_status.get("status", "unknown"),
            message=updated_status.get("message", ""),
            progress=updated_status.get("progress", 0),
            current_stage=updated_status.get("stage", ""),
            time_remaining=updated_status.get("estimated_time_remaining"),
            quality_score=updated_status.get("quality"),
            iterations=updated_status.get("iterations"),
            error=updated_status.get("error")
        )
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=404,
                detail=f"Task {task_id} not found"
            )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update task: {str(e)}"
        )
    
@router.delete("/{task_id}", response_model=Dict[str, Any])
async def cancel_task(task_id: str) -> Dict[str, Any]:
    """
    Cancel a running task.
    """
    try:
        await task_manager.cancel_task(task_id)
        return {
            "task_id": task_id,
            "status": "cancelled",
            "message": "Task was successfully cancelled"
        }
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=404,
                detail=f"Task {task_id} not found or already completed"
            )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to cancel task: {str(e)}"
        ) 