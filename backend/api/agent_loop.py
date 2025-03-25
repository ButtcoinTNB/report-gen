import asyncio
import os
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, AsyncIterator, cast
import logging
import json

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Header,
    HTTPException,
    Query,
    Request,
    Response,
)
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from utils.event_emitter import EventEmitter
from utils.metrics import MetricsCollector
from utils.agents_loop import AIAgentLoop
from utils.error_handler import ErrorResponse, raise_error
from utils.security import validate_user
from services.docx_formatter import generate_docx_async, get_document_metrics
from main import app  # Import FastAPI app instance

router = APIRouter()
logger = logging.getLogger(__name__)

# Type aliases for better readability
TaskData = Dict[str, Any]
EventData = Dict[str, Union[str, float, Dict[str, Any], None]]

# Initialize global state
tasks_cache: Dict[str, TaskData] = {}
event_subscribers: Dict[str, Dict[str, asyncio.Queue[EventData]]] = {}

# Initialize metrics collector
metrics_collector = MetricsCollector(
    metrics_file=Path(__file__).parent.parent / "data" / "metrics.json"
)

# Initialize AI agent loop
agent_loop = AIAgentLoop()

# Setup event emitter for task status updates
task_events = EventEmitter()

# Path for storing performance metrics
METRICS_LOG_PATH = Path(__file__).parent.parent / "logs" / "performance_metrics.log"
METRICS_LOG_PATH.parent.mkdir(exist_ok=True, parents=True)

# Configure metrics logger
metrics_logger = logging.getLogger("performance_metrics")
metrics_logger.setLevel(logging.INFO)
# Add file handler for metrics
file_handler = logging.FileHandler(METRICS_LOG_PATH)
file_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
)
metrics_logger.addHandler(file_handler)


# Helper function
def format_insurance_data(
    insurance_data: Dict[str, Any], document_ids: List[str]
) -> str:
    """
    Format insurance data and document IDs into a structured string for AI processing
    """
    formatted_content = "Insurance Report Request:\n\n"

    # Add insurance data in a structured format
    formatted_content += "Insurance Information:\n"
    for key, value in insurance_data.items():
        if isinstance(value, dict):
            formatted_content += f"- {key}:\n"
            for sub_key, sub_value in cast(Dict[str, Any], value).items():
                formatted_content += f"  - {sub_key}: {sub_value}\n"
        else:
            formatted_content += f"- {key}: {value}\n"

    # Add document IDs
    formatted_content += "\nDocument IDs for Analysis:\n"
    for doc_id in document_ids:
        formatted_content += f"- {doc_id}\n"

    return formatted_content


class AgentLoopRequest(BaseModel):
    report_id: str
    additional_info: Optional[str] = ""
    template_type: str = "standard"
    writer_system_prompt: Optional[str] = None
    reviewer_system_prompt: Optional[str] = None


class RefineReportRequest(BaseModel):
    report_id: str
    content: str
    instructions: str


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str  # "pending", "processing", "completed", "failed"
    progress: float = 0.0
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    message: str = ""
    stage: Optional[str] = None
    estimated_time_remaining: Optional[float] = None


class FeedbackDict(BaseModel):
    score: float
    suggestions: List[str]


class AgentLoopResponse(BaseModel):
    draft: str
    feedback: FeedbackDict
    iterations: int
    docx_url: Optional[str] = None
    status: str = "success"
    message: str = "Report generation completed"


class CancelTaskRequest(BaseModel):
    userId: Optional[str] = None
    force: Optional[bool] = False


class TaskInput(BaseModel):
    """Input data for launching a task"""

    insurance_data: Dict[str, Any] = Field(
        ..., description="Insurance data for the report"
    )
    document_ids: List[str] = Field(
        ..., description="List of document IDs to include in the analysis"
    )
    input_type: str = Field("insurance", description="Type of input data")
    user_id: Optional[str] = Field(None, description="User ID for task ownership")
    max_iterations: int = Field(
        3, description="Maximum number of iterations for the agent loop"
    )
    transaction_id: Optional[str] = Field(
        None, description="Transaction ID for tracing"
    )
    template_type: str = Field("standard", description="Type of template to use")


class RefineInput(BaseModel):
    """Input data for refining a report"""

    report_id: str = Field(..., description="ID of the report to refine")
    feedback: str = Field(..., description="User feedback for refinement")
    user_id: Optional[str] = Field(None, description="User ID for task ownership")
    transaction_id: Optional[str] = Field(
        None, description="Transaction ID for tracing"
    )


class CancelInput(BaseModel):
    """Input data for cancelling a task"""

    userId: Optional[str] = Field(None, description="User ID for validation")
    transactionId: Optional[str] = Field(None, description="Transaction ID for tracing")


@router.post("/generate-report", response_model=AgentLoopResponse)
async def generate_report(
    input_data: TaskInput,
    background_tasks: BackgroundTasks,
    request: Request,
    x_request_id: Optional[str] = Header(None),
):
    """
    Launch an agent loop to generate a report
    """
    try:
        task_id = str(uuid.uuid4())

        # Validate user if provided
        if input_data.user_id:
            user = validate_user(request)  # This returns Dict[str, Any] | None
            if not user or str(user.get("id", "")) != input_data.user_id:
                raise_error(
                    "authorization",
                    message="Invalid user ID or unauthorized",
                    detail="The provided user ID is invalid or not authorized for this operation",
                    transaction_id=input_data.transaction_id,
                    request_id=x_request_id,
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
            "transaction_id": input_data.transaction_id,
        }

        # Launch background task
        background_tasks.add_task(
            process_report_generation,
            task_id,
            input_data.insurance_data,
            input_data.document_ids,
            input_data.max_iterations,
            input_data.user_id,
            input_data.transaction_id,
        )

        return {
            "status": "success",
            "message": "Report generation started",
            "task_id": task_id,
        }
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        ErrorResponse.handle_exception(
            e,
            error_type="internal",
            message="Failed to start report generation",
            context={"input_data": input_data.model_dump()},
            transaction_id=input_data.transaction_id,
            request_id=x_request_id,
        )


@router.post("/refine-report", response_model=Dict[str, str])
async def refine_report(
    input_data: RefineInput,
    background_tasks: BackgroundTasks,
    request: Request,
    x_request_id: Optional[str] = Header(None),
):
    """
    Launch an agent loop to refine an existing report
    """
    try:
        task_id = str(uuid.uuid4())

        # Validate user if provided
        if input_data.user_id:
            user = validate_user(request)  # This returns Dict[str, Any] | None
            if not user or str(user.get("id", "")) != input_data.user_id:
                raise_error(
                    "authorization",
                    message="Invalid user ID or unauthorized",
                    detail="The provided user ID is invalid or not authorized for this operation",
                    transaction_id=input_data.transaction_id,
                    request_id=x_request_id,
                )

        # Validate report existence
        # This would be a database check in a real application
        if not os.path.exists(f"data/reports/{input_data.report_id}.json"):
            raise_error(
                "not_found",
                message="Report not found",
                detail=f"No report found with ID {input_data.report_id}",
                transaction_id=input_data.transaction_id,
                request_id=x_request_id,
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
            "transaction_id": input_data.transaction_id,
        }

        # Launch background task
        background_tasks.add_task(
            process_report_refinement,
            task_id,
            input_data.report_id,
            input_data.feedback,
            input_data.user_id,
            input_data.transaction_id,
        )

        return {
            "status": "success",
            "message": "Report refinement started",
            "task_id": task_id,
        }
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        ErrorResponse.handle_exception(
            e,
            error_type="internal",
            message="Failed to start report refinement",
            context={"input_data": input_data.model_dump()},
            transaction_id=input_data.transaction_id,
            request_id=x_request_id,
        )


@router.get("/task-status/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: str,
    user_id: Optional[str] = Query(None),
    x_request_id: Optional[str] = Header(None),
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
                request_id=x_request_id,
            )

        # Verify ownership if user_id is provided
        if (
            user_id
            and tasks_cache[task_id].get("owner")
            and tasks_cache[task_id]["owner"] != user_id
        ):
            raise_error(
                "authorization",
                message="Not authorized to access this task",
                detail="You do not have permission to access this task",
                request_id=x_request_id,
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
        ErrorResponse.handle_exception(
            e,
            error_type="internal",
            message="Failed to retrieve task status",
            context={"task_id": task_id},
            request_id=x_request_id,
        )


@router.post("/cancel-task/{task_id}")
async def cancel_task(task_id: str):
    """Cancel a running task by its ID"""
    if task_id in tasks_cache:
        # Mark the task as cancelled in the AIAgentLoop
        if hasattr(tasks_cache[task_id]["agent"], "cancel_processing"):
            tasks_cache[task_id]["agent"].cancel_processing()

        # Immediately update task status
        tasks_cache[task_id]["status"] = "cancelled"
        tasks_cache[task_id]["message"] = "Task cancelled by user"

        # Notify all subscribers about the cancellation
        await update_task_status(
            task_id=task_id,
            status="cancelled",
            message="Task cancelled by user",
            progress=0.0,
        )

        logger.info(f"Task {task_id} cancelled by user request")
        return {"success": True, "message": "Task cancelled"}
    return {"success": False, "message": "Task not found"}


@router.get("/subscribe/{task_id}")
async def subscribe_to_task(task_id: str, request: Request) -> Response:
    """Subscribe to task progress updates via server-sent events."""
    if task_id not in tasks_cache:
        return JSONResponse({"error": "Task not found"}, status_code=404)

    async def event_generator() -> AsyncIterator[Dict[str, str]]:
        subscriber_id = str(uuid.uuid4())
        if "subscribers" not in tasks_cache[task_id]:
            tasks_cache[task_id]["subscribers"] = {}

        # Create a queue for this subscriber
        queue = asyncio.Queue[EventData]()
        tasks_cache[task_id]["subscribers"][subscriber_id] = queue

        logger.info(f"New subscriber {subscriber_id} for task {task_id}")

        try:
            # Send initial state
            status = tasks_cache[task_id]["status"]
            progress = tasks_cache[task_id]["progress"]
            message = tasks_cache[task_id]["message"]
            result = tasks_cache[task_id].get("result", None)
            error = tasks_cache[task_id].get("error", None)
            stage = tasks_cache[task_id].get("stage", None)
            estimated_time_remaining = tasks_cache[task_id].get(
                "estimatedTimeRemaining", None
            )

            # Convert to floats for JSON serialization
            if estimated_time_remaining is not None:
                estimated_time_remaining = float(estimated_time_remaining)

            data: EventData = {
                "task_id": task_id,
                "status": status,
                "progress": progress,
                "message": message,
                "result": result,
                "error": error,
            }

            # Add stage and estimated time if available
            if stage:
                data["stage"] = stage
            if estimated_time_remaining is not None:
                data["estimatedTimeRemaining"] = estimated_time_remaining

            yield format_sse(data)

            # Send periodic keepalive pings to prevent connection timeout
            keepalive_task = asyncio.create_task(send_keepalive_pings(queue))

            try:
                # Process updates from the queue
                while True:
                    update = await queue.get()
                    # Check if we received a signal to stop
                    if update.get("type") == "stop":
                        break
                    yield format_sse(update)
            finally:
                # Cancel the keepalive task when the loop exits
                keepalive_task.cancel()

        except asyncio.CancelledError:
            logger.info(f"Subscriber {subscriber_id} connection closed")
        finally:
            # Clean up the subscriber
            if task_id in tasks_cache and "subscribers" in tasks_cache[task_id]:
                if subscriber_id in tasks_cache[task_id]["subscribers"]:
                    del tasks_cache[task_id]["subscribers"][subscriber_id]
                    logger.info(
                        f"Removed subscriber {subscriber_id} for task {task_id}"
                    )

    return EventSourceResponse(event_generator())


async def send_keepalive_pings(queue: asyncio.Queue[EventData]) -> None:
    """Send periodic pings to keep the connection alive"""
    try:
        while True:
            # Send a ping every 30 seconds
            await asyncio.sleep(30)
            await queue.put({"type": "ping", "time": time.time()})
    except asyncio.CancelledError:
        pass


def format_sse(data: EventData) -> Dict[str, str]:
    """Format a Server-Sent Events message"""
    json_data = json.dumps(data)
    return {"event": "update", "data": json_data}


async def update_task_status(
    task_id: str,
    status: str,
    message: str,
    progress: float,
    result: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None,
    stage: Optional[str] = None,
    estimated_time_remaining: Optional[float] = None,
) -> None:
    """Update task status and notify all subscribers"""
    if task_id in tasks_cache:
        # Update task status
        tasks_cache[task_id]["status"] = status
        tasks_cache[task_id]["progress"] = progress
        tasks_cache[task_id]["message"] = message

        if result is not None:
            tasks_cache[task_id]["result"] = result
        if error is not None:
            tasks_cache[task_id]["error"] = error
        if stage is not None:
            tasks_cache[task_id]["stage"] = stage
        if estimated_time_remaining is not None:
            tasks_cache[task_id]["estimatedTimeRemaining"] = estimated_time_remaining

        # Prepare data for subscribers
        data: EventData = {
            "task_id": task_id,
            "status": status,
            "progress": progress,
            "message": message,
        }

        # Include optional fields if they exist
        if result is not None:
            data["result"] = result
        if error is not None:
            data["error"] = error
        if stage is not None:
            data["stage"] = stage
        if estimated_time_remaining is not None:
            data["estimatedTimeRemaining"] = float(estimated_time_remaining)

        # Notify all subscribers
        if "subscribers" in tasks_cache[task_id]:
            for subscriber_queue in tasks_cache[task_id]["subscribers"].values():
                try:
                    await subscriber_queue.put(data)
                except Exception as e:
                    logger.error(f"Error notifying subscriber: {e}")


async def check_user_permission(user_id: str) -> bool:
    """Validate if a user has permission to access the system"""
    # TODO: Implement actual user validation
    return True


async def process_report_generation(
    task_id: str,
    insurance_data: Dict[str, Any],
    document_ids: List[str],
    max_iterations: int = 3,
    user_id: Optional[str] = None,
    transaction_id: Optional[str] = None,
) -> None:
    """Process the report generation in the background"""
    try:
        # Update task status to processing
        await update_task_status(
            task_id,
            "processing",
            "Starting report generation",
            progress=0.0,
        )

        # Define progress callback with proper types
        async def progress_callback(
            progress: float,
            message: str = "",
            stage: Optional[str] = None,
            estimated_time_remaining: Optional[float] = None,
        ) -> None:
            await update_task_status(
                task_id=task_id,
                status=tasks_cache[task_id]["status"],
                message=message
                or f"Processing report, {int(progress * 100)}% complete",
                progress=float(progress),
                stage=stage or "ai_processing",
                estimated_time_remaining=estimated_time_remaining,
            )

        # Create AI Agent Loop
        agent_loop = AIAgentLoop(max_loops=3, progress_callback=progress_callback)

        # Format the user content
        formatted_content = format_insurance_data(insurance_data, document_ids)

        # Run the agent loop
        tasks_cache[task_id]["stage"] = "ai_processing"
        tasks_cache[task_id]["message"] = "AI agents generating report content"
        await update_task_status(
            task_id=task_id,
            status=tasks_cache[task_id]["status"],
            message=tasks_cache[task_id]["message"],
            progress=float(tasks_cache[task_id]["progress"]),
            stage=tasks_cache[task_id].get("stage"),
            estimated_time_remaining=tasks_cache[task_id].get(
                "estimated_time_remaining"
            ),
        )

        # Generate report
        result: Dict[str, Any] = await agent_loop.generate_report(formatted_content)

        # Update task with AI result
        tasks_cache[task_id]["progress"] = 90
        tasks_cache[task_id]["message"] = "Generating final document"
        tasks_cache[task_id]["stage"] = "document_generation"

        # Generate DOCX
        await update_task_status(
            task_id, "processing", "Generating DOCX file", progress=90
        )

        # Create a readable filename
        safe_name = insurance_data.get("claim_number", "report").replace(" ", "_")
        docx_path = f"generated_reports/{safe_name}_{task_id[:8]}.docx"

        # Generate the DOCX file
        docx_result = await generate_docx_async(str(result.get("draft", "")), docx_path)

        # Update with final result
        await update_task_status(
            task_id,
            "completed",
            "Report generated successfully",
            progress=100,
            result={
                "draft": result["draft"],
                "feedback": result["feedback"],
                "iterations": result["iterations"],
                "docx_url": docx_result["url"],
                "processing_time": result["processing_time"],
            },
        )

    except Exception as e:
        logger.error(f"Error in agent loop: {e}")
        await update_task_status(
            task_id=task_id,
            status="failed",
            message=f"Error generating report: {str(e)}",
            progress=0.0,
            error=str(e),
        )
        raise


async def process_report_refinement(
    task_id: str,
    report_id: str,
    feedback: str,
    user_id: Optional[str] = None,
    transaction_id: Optional[str] = None,
) -> None:
    """Process report refinement in the background"""
    try:
        # Update task status to processing
        await update_task_status(
            task_id=task_id,
            status="processing",
            message="Starting report refinement",
            progress=0.0,
        )

        # Check if report exists
        report_path = f"data/reports/{report_id}.json"
        if not os.path.exists(report_path):
            error_message = f"Report with ID {report_id} not found"
            await update_task_status(
                task_id=task_id,
                status="failed",
                message="Failed to refine report",
                progress=0.0,
                error=error_message,
            )
            return

        # Load the report
        with open(report_path, "r") as f:
            report_data = json.load(f)

        # Verify ownership if user_id is provided
        if user_id and report_data.get("user_id") and report_data["user_id"] != user_id:
            error_message = "Not authorized to refine this report"
            await update_task_status(
                task_id=task_id,
                status="failed",
                message="Failed to refine report",
                progress=0.0,
                error=error_message,
            )
            return

        # Simulate parsing feedback (20% of progress)
        await asyncio.sleep(2)
        await update_task_status(task_id, "processing", "Analyzing feedback", 0.2)

        # Simulate refinement process (60% progress)
        await asyncio.sleep(3)
        await update_task_status(task_id, "processing", "Applying refinements", 0.6)

        # Simulate final review (80% progress)
        await asyncio.sleep(2)
        await update_task_status(task_id, "processing", "Reviewing changes", 0.8)

        # Update report based on feedback
        # In a real app, this would use LLM to refine content
        report_data["refined"] = True
        report_data["feedback"] = feedback
        report_data["sections"].append(
            {
                "title": "Refinement Notes",
                "content": f"This report was refined based on feedback: {feedback}",
            }
        )

        # Save updated report
        with open(report_path, "w") as f:
            json.dump(report_data, f)

        # Update task as completed
        await update_task_status(
            task_id, "completed", "Report refined successfully", 1.0, report_data
        )

    except Exception as e:
        error_message = str(e)
        error_context = {
            "task_id": task_id,
            "report_id": report_id,
            "error_type": type(e).__name__,
            "transaction_id": transaction_id,
        }

        # Log the error
        print(f"Error in report refinement: {error_message}")
        print(f"Context: {error_context}")

        # Update task as failed
        await update_task_status(
            task_id,
            "failed",
            "Failed to refine report",
            progress=0.0,
            error=error_message,
        )


async def process_report_generation_v2(task_id: str, request: AgentLoopRequest) -> None:
    """
    Process the report generation asynchronously
    """
    temp_files = []  # Track temporary files for cleanup
    start_time = time.time()
    report_metrics = {
        "task_id": task_id,
        "report_id": request.report_id,
        "iterations": 0,
        "generation_time": 0,
        "quality_score": 0,
    }

    try:
        # Update initial task status
        tasks_cache[task_id]["stage"] = "file_processing"
        tasks_cache[task_id]["progress"] = 10
        tasks_cache[task_id]["message"] = "Processing input files"
        await update_task_status(
            task_id=task_id,
            status=tasks_cache[task_id]["status"],
            message=tasks_cache[task_id]["message"],
            progress=float(tasks_cache[task_id]["progress"]),
            stage=tasks_cache[task_id].get("stage"),
            estimated_time_remaining=tasks_cache[task_id].get(
                "estimated_time_remaining"
            ),
        )

        # Create AI Agent Loop with progress callback
        agent_loop = AIAgentLoop(
            max_loops=3,
            progress_callback=lambda progress, message, stage=None, estimated_time_remaining=None: update_task_status(
                task_id=task_id,
                status=tasks_cache[task_id]["status"],
                message=message,
                progress=progress,
                stage=stage,
                estimated_time_remaining=estimated_time_remaining,
            ),
        )

        # Run the agent loop
        tasks_cache[task_id]["stage"] = "ai_processing"
        tasks_cache[task_id]["message"] = "AI agents generating report content"
        await update_task_status(
            task_id=task_id,
            status=tasks_cache[task_id]["status"],
            message=tasks_cache[task_id]["message"],
            progress=float(tasks_cache[task_id]["progress"]),
            stage=tasks_cache[task_id].get("stage"),
            estimated_time_remaining=tasks_cache[task_id].get(
                "estimated_time_remaining"
            ),
        )

        # Generate report
        result = await agent_loop.generate_report(request.additional_info or "")

        # Update task with AI result
        tasks_cache[task_id]["progress"] = 90
        tasks_cache[task_id]["message"] = "Generating final document"
        tasks_cache[task_id]["stage"] = "document_generation"
        await update_task_status(
            task_id=task_id,
            status=tasks_cache[task_id]["status"],
            message=tasks_cache[task_id]["message"],
            progress=float(tasks_cache[task_id]["progress"]),
            stage=tasks_cache[task_id].get("stage"),
            estimated_time_remaining=tasks_cache[task_id].get(
                "estimated_time_remaining"
            ),
        )

        # Extract results
        content = result.get("draft", "")
        feedback = result.get("feedback", {})
        iterations = result.get("iterations", 1)

        # Update metrics
        report_metrics["iterations"] = iterations
        report_metrics["content_length"] = len(content)
        report_metrics["quality_score"] = (
            feedback.get("score", 0) * 100 if isinstance(feedback, dict) else 0
        )

        # Generate DOCX document with enhanced formatter
        document_metadata = {
            "title": f"Insurance Report - {request.report_id}",
            "report_id": request.report_id,
            "author": "Insurance Report Generator",
            "category": "Insurance",
            "comments": f"Generated with {iterations} iterations. Quality score: {report_metrics['quality_score']:.1f}/100",
            "template_type": (
                request.template_type
                if hasattr(request, "template_type")
                else "default"
            ),
        }

        docx_result = await generate_docx_async(content, metadata=document_metadata)

        # If document generation failed
        if "error" in docx_result:
            raise Exception(f"Document generation failed: {docx_result['error']}")

        # Update metrics with document generation info
        report_metrics["document_generation_time"] = docx_result.get(
            "generation_time", 0
        )
        report_metrics["document_quality_score"] = (
            docx_result.get("quality", {}).get("score", 0) * 100
        )
        report_metrics["document_from_cache"] = docx_result.get("from_cache", False)

        # Get the document URL
        document_url = docx_result.get("url", "")
        if not document_url:
            document_url = f"/reports/{os.path.basename(docx_result.get('path', ''))}"

        # Finalize the result
        tasks_cache[task_id]["status"] = "completed"
        tasks_cache[task_id]["progress"] = 100
        tasks_cache[task_id]["message"] = "Report generation completed"
        tasks_cache[task_id]["stage"] = "completed"
        tasks_cache[task_id]["estimated_time_remaining"] = 0
        tasks_cache[task_id]["result"] = {
            "draft": content,
            "feedback": feedback,
            "docxUrl": document_url,
            "iterations": iterations,
            "quality_score": report_metrics["quality_score"],
        }

        # Complete metrics collection
        report_metrics["status"] = "completed"
        report_metrics["duration"] = time.time() - start_time
        metrics_collector.add_metric("report_generation", report_metrics)

        # Log performance metrics
        metrics_logger.info(
            f"Report generation completed: {json.dumps(report_metrics)}"
        )

        # Notify subscribers of completion
        await update_task_status(
            task_id=task_id,
            status=tasks_cache[task_id]["status"],
            message=tasks_cache[task_id]["message"],
            progress=float(tasks_cache[task_id]["progress"]),
            stage=tasks_cache[task_id].get("stage"),
            estimated_time_remaining=tasks_cache[task_id].get(
                "estimated_time_remaining"
            ),
        )

    except Exception as e:
        logger.error(f"Error in report generation process: {str(e)}")
        tasks_cache[task_id]["status"] = "error"
        tasks_cache[task_id]["error"] = str(e)
        tasks_cache[task_id]["stage"] = "error"

        # Update metrics for error case
        report_metrics["status"] = "error"
        report_metrics["error"] = str(e)
        report_metrics["duration"] = time.time() - start_time
        metrics_collector.add_metric("report_generation_error", report_metrics)

        # Log error in performance metrics
        metrics_logger.error(f"Report generation error: {json.dumps(report_metrics)}")

        # Notify subscribers of error
        await update_task_status(
            task_id=task_id,
            status=tasks_cache[task_id]["status"],
            message=tasks_cache[task_id]["message"],
            progress=float(tasks_cache[task_id]["progress"]),
            stage=tasks_cache[task_id].get("stage"),
            estimated_time_remaining=tasks_cache[task_id].get(
                "estimated_time_remaining"
            ),
        )

    finally:
        # Clean up any temporary files
        for file_path in temp_files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.debug(f"Removed temporary file: {file_path}")
            except Exception as e:
                logger.warning(f"Error removing temporary file {file_path}: {str(e)}")


@router.get("/metrics/document-generation")
async def get_document_generation_metrics() -> Dict[str, Any]:
    """
    Get metrics about document generation
    """
    try:
        docx_metrics = await get_document_metrics()
        return {"status": "success", "metrics": docx_metrics}
    except Exception as e:
        logger.error(f"Error getting document metrics: {str(e)}")
        return {"status": "error", "error": str(e)}


@router.get("/metrics/report-generation")
async def get_report_generation_metrics() -> Dict[str, Any]:
    """
    Get metrics about report generation
    """
    try:
        report_metrics = metrics_collector.get_metrics("report_generation", limit=100)
        error_metrics = metrics_collector.get_metrics(
            "report_generation_error", limit=20
        )

        # Calculate averages
        total_reports = len(report_metrics)
        if total_reports > 0:
            avg_duration = (
                sum(m.get("duration", 0) for m in report_metrics) / total_reports
            )
            avg_iterations = (
                sum(m.get("iterations", 0) for m in report_metrics) / total_reports
            )
            avg_quality = (
                sum(m.get("quality_score", 0) for m in report_metrics) / total_reports
            )
        else:
            avg_duration = 0
            avg_iterations = 0
            avg_quality = 0

        return {
            "status": "success",
            "summary": {
                "total_reports": total_reports,
                "avg_duration_seconds": avg_duration,
                "avg_iterations": avg_iterations,
                "avg_quality_score": avg_quality,
                "error_count": len(error_metrics),
            },
            "recent_reports": report_metrics[:10],
            "recent_errors": error_metrics[:5],
        }
    except Exception as e:
        logger.error(f"Error getting report metrics: {str(e)}")
        return {"status": "error", "error": str(e)}


# Periodic cleanup job to remove old tasks
async def periodic_task_cleanup():
    """Remove old tasks from memory periodically"""
    try:
        while True:
            await asyncio.sleep(3600)  # Run every hour

            current_time = time.time()
            tasks_to_remove = []

            for task_id, task_data in tasks_cache.items():
                # Remove tasks that have been cleaned and are older than 24 hours
                if (
                    task_data.get("cleaned")
                    and current_time - task_data.get("cleaned_at", 0) > 86400
                ):
                    tasks_to_remove.append(task_id)

            # Remove old tasks
            for task_id in tasks_to_remove:
                del tasks_cache[task_id]
                logger.info(f"Removed old task {task_id} from memory")

    except Exception as e:
        logger.error(f"Error in periodic task cleanup: {e}")


# Start the cleanup job on application startup
@app.on_event("startup")
async def start_cleanup_job():
    asyncio.create_task(periodic_task_cleanup())
