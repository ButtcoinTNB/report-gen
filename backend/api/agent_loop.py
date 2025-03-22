from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, Request, Header
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Optional, Any, AsyncIterator
from utils.agents_loop import AIAgentLoop
from services.docx_formatter import generate_docx
import uuid
import os
import time
import json
import asyncio
import signal
import psutil
from pathlib import Path
from utils.security import validate_user, get_user_from_request
from ..utils.event_emitter import EventEmitter
from ..utils.task_manager import tasks_cache
from ..utils.error_handler import raise_error, format_error, ErrorHandler

router = APIRouter()
agent_loop = AIAgentLoop()

# Cache for storing in-progress and completed tasks
tasks_cache = {}

# Event subscribers for real-time updates
event_subscribers = {}

# Setup event emitter for task status updates
task_events = EventEmitter()

class AgentLoopRequest(BaseModel):
    report_id: str
    additional_info: Optional[str] = ""

class RefineReportRequest(BaseModel):
    report_id: str
    content: str
    instructions: str
    
class TaskStatusResponse(BaseModel):
    task_id: str
    status: str  # "pending", "processing", "completed", "failed"
    progress: Optional[float] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class FeedbackDict(BaseModel):
    score: float
    suggestions: List[str]

class AgentLoopResponse(BaseModel):
    draft: str
    feedback: FeedbackDict
    iterations: int
    docx_url: Optional[str] = None

class CancelTaskRequest(BaseModel):
    userId: Optional[str] = None
    force: Optional[bool] = False

class TaskInput(BaseModel):
    """Input data for launching a task"""
    insurance_data: Dict[str, Any] = Field(..., description="Insurance data for the report")
    document_ids: List[str] = Field(..., description="List of document IDs to include in the analysis")
    input_type: str = Field("insurance", description="Type of input data")
    user_id: Optional[str] = Field(None, description="User ID for task ownership")
    max_iterations: int = Field(3, description="Maximum number of iterations for the agent loop")
    transaction_id: Optional[str] = Field(None, description="Transaction ID for tracing")

class RefineInput(BaseModel):
    """Input data for refining a report"""
    report_id: str = Field(..., description="ID of the report to refine")
    feedback: str = Field(..., description="User feedback for refinement")
    user_id: Optional[str] = Field(None, description="User ID for task ownership")
    transaction_id: Optional[str] = Field(None, description="Transaction ID for tracing")

class CancelInput(BaseModel):
    """Input data for cancelling a task"""
    userId: Optional[str] = Field(None, description="User ID for validation")
    transactionId: Optional[str] = Field(None, description="Transaction ID for tracing")

@router.post("/generate-report", response_model=AgentLoopResponse)
async def generate_report(
    input_data: TaskInput,
    background_tasks: BackgroundTasks,
    x_request_id: Optional[str] = Header(None)
):
    """
    Launch an agent loop to generate a report
    """
    try:
        task_id = str(uuid.uuid4())
        
        # Validate user if provided
        if input_data.user_id:
            if not await validate_user(input_data.user_id):
                raise_error(
                    "authorization",
                    message="Invalid user ID or unauthorized",
                    detail="The provided user ID is invalid or not authorized for this operation",
                    transaction_id=input_data.transaction_id,
                    request_id=x_request_id
                )
        
        # Initialize task status
        tasks_cache[task_id] = {
            "status": "pending",
            "message": "Task initialized, waiting to start",
            "progress": 0.0,
            "result": None,
            "error": None,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "owner": input_data.user_id,
            "transaction_id": input_data.transaction_id
        }
        
        # Launch background task
        background_tasks.add_task(
            process_report_generation,
            task_id,
            input_data.insurance_data,
            input_data.document_ids,
            input_data.max_iterations,
            input_data.user_id,
            input_data.transaction_id
        )
        
        return {
            "status": "success",
            "message": "Report generation started",
            "task_id": task_id
        }
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        ErrorHandler.handle_exception(
            e,
            error_type="internal",
            message="Failed to start report generation",
            context={"input_data": input_data.dict()},
            transaction_id=input_data.transaction_id,
            request_id=x_request_id
        )

@router.post("/refine-report", response_model=Dict[str, str])
async def refine_report(
    input_data: RefineInput,
    background_tasks: BackgroundTasks,
    x_request_id: Optional[str] = Header(None)
):
    """
    Launch an agent loop to refine an existing report
    """
    try:
        task_id = str(uuid.uuid4())
        
        # Validate user if provided
        if input_data.user_id:
            if not await validate_user(input_data.user_id):
                raise_error(
                    "authorization",
                    message="Invalid user ID or unauthorized",
                    detail="The provided user ID is invalid or not authorized for this operation",
                    transaction_id=input_data.transaction_id,
                    request_id=x_request_id
                )
                
        # Validate report existence
        # This would be a database check in a real application
        if not os.path.exists(f"data/reports/{input_data.report_id}.json"):
            raise_error(
                "not_found",
                message="Report not found",
                detail=f"No report found with ID {input_data.report_id}",
                transaction_id=input_data.transaction_id,
                request_id=x_request_id
            )
        
        # Initialize task status
        tasks_cache[task_id] = {
            "status": "pending",
            "message": "Refinement task initialized, waiting to start",
            "progress": 0.0,
            "result": None,
            "error": None,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "owner": input_data.user_id,
            "transaction_id": input_data.transaction_id
        }
        
        # Launch background task
        background_tasks.add_task(
            process_report_refinement,
            task_id,
            input_data.report_id,
            input_data.feedback,
            input_data.user_id,
            input_data.transaction_id
        )
        
        return {
            "status": "success",
            "message": "Report refinement started",
            "task_id": task_id
        }
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        ErrorHandler.handle_exception(
            e,
            error_type="internal",
            message="Failed to start report refinement",
            context={"input_data": input_data.dict()},
            transaction_id=input_data.transaction_id,
            request_id=x_request_id
        )

@router.get("/task-status/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: str,
    user_id: Optional[str] = Query(None),
    x_request_id: Optional[str] = Header(None)
):
    """
    Get the status of a task
    """
    try:
        # Verify task exists
        if task_id not in tasks_cache:
            raise_error(
                "not_found",
                message="Task not found",
                detail=f"No task found with ID {task_id}",
                request_id=x_request_id
            )
        
        # Verify ownership if user_id is provided
        if user_id and tasks_cache[task_id].get("owner") and tasks_cache[task_id]["owner"] != user_id:
            raise_error(
                "authorization",
                message="Not authorized to access this task",
                detail="You do not have permission to access this task",
                request_id=x_request_id
            )
        
        # Return task status
        status_data = tasks_cache[task_id].copy()
        
        # Don't include internal details in the response
        if "owner" in status_data:
            del status_data["owner"]
        
        return status_data
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        ErrorHandler.handle_exception(
            e, 
            error_type="internal",
            message="Failed to retrieve task status",
            context={"task_id": task_id},
            request_id=x_request_id
        )

@router.post("/cancel-task/{task_id}")
async def cancel_task(
    task_id: str,
    cancel_data: CancelInput = Body(CancelInput()),
    x_request_id: Optional[str] = Header(None)
):
    """
    Cancel an ongoing task
    """
    try:
        # Verify task exists
        if task_id not in tasks_cache:
            raise_error(
                "not_found",
                message="Task not found",
                detail=f"No task found with ID {task_id}",
                transaction_id=cancel_data.transactionId,
                request_id=x_request_id
            )
        
        # Verify task can be cancelled (only pending or processing tasks can be cancelled)
        if tasks_cache[task_id]["status"] not in ["pending", "processing"]:
            raise_error(
                "conflict",
                message="Task cannot be cancelled",
                detail=f"Task is in {tasks_cache[task_id]['status']} state and cannot be cancelled",
                transaction_id=cancel_data.transactionId,
                request_id=x_request_id
            )
        
        # Verify ownership if userId is provided
        if cancel_data.userId and tasks_cache[task_id].get("owner") and tasks_cache[task_id]["owner"] != cancel_data.userId:
            raise_error(
                "authorization",
                message="Not authorized to cancel this task",
                detail="You do not have permission to cancel this task",
                transaction_id=cancel_data.transactionId,
                request_id=x_request_id
            )
        
        # Update task status to cancelled
        tasks_cache[task_id].update({
            "status": "failed",
            "error": "Task cancelled by user",
            "updated_at": datetime.now().isoformat(),
            "transaction_id": cancel_data.transactionId
        })
        
        # Emit cancellation event for subscribers
        task_events.emit(f"task.{task_id}.cancelled", {
            "task_id": task_id,
            "status": "cancelled",
            "message": "Task cancelled by user",
            "transaction_id": cancel_data.transactionId
        })
        
        return {
            "status": "success",
            "message": "Task cancelled successfully",
            "task_id": task_id
        }
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        ErrorHandler.handle_exception(
            e,
            error_type="internal",
            message="Failed to cancel task",
            context={"task_id": task_id, "userId": cancel_data.userId},
            transaction_id=cancel_data.transactionId,
            request_id=x_request_id
        )

@router.get("/subscribe/{task_id}")
async def subscribe_to_task(
    task_id: str,
    user_id: Optional[str] = Query(None),
    x_request_id: Optional[str] = Header(None)
):
    """
    SSE endpoint to subscribe to task status updates
    """
    try:
        # Verify task exists
        if task_id not in tasks_cache:
            raise_error(
                "not_found",
                message="Task not found",
                detail=f"No task found with ID {task_id}",
                request_id=x_request_id
            )
        
        # Verify ownership if user_id is provided
        if user_id and tasks_cache[task_id].get("owner") and tasks_cache[task_id]["owner"] != user_id:
            raise_error(
                "authorization",
                message="Not authorized to access this task",
                detail="You do not have permission to access this task",
                request_id=x_request_id
            )
            
        async def event_generator():
            """Generate SSE events for task status updates"""
            # Send initial status
            yield f"data: {json.dumps(tasks_cache[task_id])}\n\n"
            
            # Setup subscription for task events
            queue = asyncio.Queue()
            
            def on_task_update(data):
                if not queue.full():
                    asyncio.create_task(queue.put(data))
            
            # Subscribe to task events
            task_events.on(f"task.{task_id}.update", on_task_update)
            task_events.on(f"task.{task_id}.complete", on_task_update)
            task_events.on(f"task.{task_id}.error", on_task_update)
            task_events.on(f"task.{task_id}.cancelled", on_task_update)
            
            try:
                # Wait for events
                while True:
                    try:
                        data = await asyncio.wait_for(queue.get(), timeout=30)
                        yield f"data: {json.dumps(data)}\n\n"
                    except asyncio.TimeoutError:
                        # Send keepalive comment after timeout
                        yield ": keepalive\n\n"
            finally:
                # Clean up event listeners
                task_events.off(f"task.{task_id}.update", on_task_update)
                task_events.off(f"task.{task_id}.complete", on_task_update)
                task_events.off(f"task.{task_id}.error", on_task_update)
                task_events.off(f"task.{task_id}.cancelled", on_task_update)
        
        return event_generator()
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        ErrorHandler.handle_exception(
            e,
            error_type="internal", 
            message="Failed to set up subscription",
            context={"task_id": task_id},
            request_id=x_request_id
        )

async def update_task_status(
    task_id: str, 
    status: str, 
    message: str = None, 
    progress: float = None, 
    result: Any = None, 
    error: str = None
):
    """
    Update task status and emit events
    """
    # Skip updates for tasks that have been cancelled
    if task_id in tasks_cache and tasks_cache[task_id]["status"] == "failed" and tasks_cache[task_id].get("error") == "Task cancelled by user":
        return
    
    # Update task status in cache
    if task_id in tasks_cache:
        update_data = {"updated_at": datetime.now().isoformat()}
        
        if status is not None:
            update_data["status"] = status
        
        if message is not None:
            update_data["message"] = message
            
        if progress is not None:
            update_data["progress"] = progress
            
        if result is not None:
            update_data["result"] = result
            
        if error is not None:
            update_data["error"] = error
            
        tasks_cache[task_id].update(update_data)
        
        # Prepare event data
        event_data = tasks_cache[task_id].copy()
        
        # Emit appropriate event
        if status == "completed":
            task_events.emit(f"task.{task_id}.complete", event_data)
        elif status == "failed":
            task_events.emit(f"task.{task_id}.error", event_data)
        else:
            task_events.emit(f"task.{task_id}.update", event_data)

async def process_report_generation(
    task_id: str,
    insurance_data: Dict[str, Any],
    document_ids: List[str],
    max_iterations: int = 3,
    user_id: str = None,
    transaction_id: str = None
):
    """
    Process report generation in the background
    """
    try:
        # Update task status to processing
        await update_task_status(
            task_id, 
            "processing", 
            "Starting report generation", 
            0.05
        )
        
        # Simulate document parsing (10% of progress)
        await asyncio.sleep(2)
        await update_task_status(
            task_id, 
            "processing", 
            "Parsing documents", 
            0.1
        )
        
        # Simulate parsing each document
        for i, doc_id in enumerate(document_ids):
            # Check if task was cancelled
            if tasks_cache[task_id]["status"] == "failed" and tasks_cache[task_id].get("error") == "Task cancelled by user":
                return
                
            await asyncio.sleep(1)
            doc_progress = 0.1 + (i + 1) / len(document_ids) * 0.2
            await update_task_status(
                task_id, 
                "processing", 
                f"Parsing document {i+1}/{len(document_ids)}", 
                doc_progress
            )
        
        # Simulate agent reasoning iterations
        total_iterations = min(max_iterations, 3)  # Cap at 3 iterations for demo
        for iteration in range(total_iterations):
            # Check if task was cancelled
            if tasks_cache[task_id]["status"] == "failed" and tasks_cache[task_id].get("error") == "Task cancelled by user":
                return
                
            # Each iteration takes 30% of the remaining progress
            base_progress = 0.3
            progress_per_iteration = (1.0 - base_progress) / total_iterations
            
            # Simulate iterative thinking
            await asyncio.sleep(2)
            iter_start = base_progress + iteration * progress_per_iteration
            
            # Update for iteration start
            await update_task_status(
                task_id, 
                "processing", 
                f"Starting iteration {iteration+1}/{total_iterations}", 
                iter_start
            )
            
            # Simulate steps within iteration
            steps = ["Analyzing policies", "Comparing coverage", "Drafting section", "Reviewing"]
            for step_idx, step in enumerate(steps):
                # Check if task was cancelled
                if tasks_cache[task_id]["status"] == "failed" and tasks_cache[task_id].get("error") == "Task cancelled by user":
                    return
                    
                await asyncio.sleep(1)
                step_progress = iter_start + (step_idx + 1) / len(steps) * progress_per_iteration
                await update_task_status(
                    task_id, 
                    "processing", 
                    f"Iteration {iteration+1}/{total_iterations}: {step}", 
                    step_progress
                )
        
        # Generate mock result
        report_id = str(uuid.uuid4())
        mock_result = {
            "report_id": report_id,
            "title": "Insurance Coverage Analysis",
            "summary": "This analysis reviews the provided insurance policies and identifies coverage gaps and recommendations.",
            "sections": [
                {
                    "title": "Policy Overview",
                    "content": "Your current insurance portfolio includes coverage for home, auto, and life insurance."
                },
                {
                    "title": "Coverage Analysis",
                    "content": "We've identified potential gaps in your liability coverage and recommend increasing limits."
                },
                {
                    "title": "Recommendations",
                    "content": "Consider adding an umbrella policy to extend liability protection across all your policies."
                }
            ],
            "user_id": user_id
        }
        
        # Save mock result to file (in real app, would save to database)
        os.makedirs("data/reports", exist_ok=True)
        with open(f"data/reports/{report_id}.json", "w") as f:
            json.dump(mock_result, f)
        
        # Update task as completed
        await update_task_status(
            task_id, 
            "completed", 
            "Report generated successfully", 
            1.0, 
            mock_result
        )
        
    except Exception as e:
        error_message = str(e)
        error_context = {
            "task_id": task_id,
            "error_type": type(e).__name__,
            "transaction_id": transaction_id
        }
        
        # Log the error
        print(f"Error in report generation: {error_message}")
        print(f"Context: {error_context}")
        
        # Update task as failed
        await update_task_status(
            task_id, 
            "failed", 
            "Failed to generate report", 
            progress=None, 
            error=error_message
        )

async def process_report_refinement(
    task_id: str,
    report_id: str,
    feedback: str,
    user_id: str = None,
    transaction_id: str = None
):
    """
    Process report refinement in the background
    """
    try:
        # Update task status to processing
        await update_task_status(
            task_id, 
            "processing", 
            "Starting report refinement", 
            0.05
        )
        
        # Check if report exists
        report_path = f"data/reports/{report_id}.json"
        if not os.path.exists(report_path):
            error_message = f"Report with ID {report_id} not found"
            await update_task_status(
                task_id, 
                "failed", 
                "Failed to refine report", 
                progress=None, 
                error=error_message
            )
            return
        
        # Load the report
        with open(report_path, "r") as f:
            report_data = json.load(f)
        
        # Verify ownership if user_id is provided
        if user_id and report_data.get("user_id") and report_data["user_id"] != user_id:
            error_message = "Not authorized to refine this report"
            await update_task_status(
                task_id, 
                "failed", 
                "Failed to refine report", 
                progress=None, 
                error=error_message
            )
            return
        
        # Simulate parsing feedback (20% of progress)
        await asyncio.sleep(2)
        await update_task_status(
            task_id, 
            "processing", 
            "Analyzing feedback", 
            0.2
        )
        
        # Simulate refinement process (60% progress)
        await asyncio.sleep(3)
        await update_task_status(
            task_id, 
            "processing", 
            "Applying refinements", 
            0.6
        )
        
        # Simulate final review (80% progress)
        await asyncio.sleep(2)
        await update_task_status(
            task_id, 
            "processing", 
            "Reviewing changes", 
            0.8
        )
        
        # Update report based on feedback
        # In a real app, this would use LLM to refine content
        report_data["refined"] = True
        report_data["feedback"] = feedback
        report_data["sections"].append({
            "title": "Refinement Notes",
            "content": f"This report was refined based on feedback: {feedback}"
        })
        
        # Save updated report
        with open(report_path, "w") as f:
            json.dump(report_data, f)
        
        # Update task as completed
        await update_task_status(
            task_id, 
            "completed", 
            "Report refined successfully", 
            1.0, 
            report_data
        )
        
    except Exception as e:
        error_message = str(e)
        error_context = {
            "task_id": task_id,
            "report_id": report_id,
            "error_type": type(e).__name__,
            "transaction_id": transaction_id
        }
        
        # Log the error
        print(f"Error in report refinement: {error_message}")
        print(f"Context: {error_context}")
        
        # Update task as failed
        await update_task_status(
            task_id, 
            "failed", 
            "Failed to refine report", 
            progress=None, 
            error=error_message
        ) 