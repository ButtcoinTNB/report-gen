from fastapi import APIRouter, HTTPException, BackgroundTasks
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
from pathlib import Path

router = APIRouter()
agent_loop = AIAgentLoop()

# Cache for storing in-progress and completed tasks
tasks_cache = {}

# Event subscribers for real-time updates
event_subscribers = {}

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

@router.post("/generate-report", response_model=AgentLoopResponse)
async def generate_report(request: AgentLoopRequest):
    try:
        # Get the report content from the uploaded files
        report_dir = Path(os.getcwd()) / "uploads" / request.report_id
        metadata_file = report_dir / "metadata.json"
        
        if not metadata_file.exists():
            raise HTTPException(status_code=404, detail="Report not found")
            
        # Run the AI agent loop with the report content and additional info
        result = await agent_loop.generate_report(str(metadata_file), request.additional_info)
        
        # Generate unique filename for the DOCX
        filename = f"report_{uuid.uuid4()}.docx"
        reports_dir = Path(os.getcwd()) / "generated_reports"
        reports_dir.mkdir(exist_ok=True)
        output_path = str(reports_dir / filename)
        
        # Generate DOCX (not async)
        docx_path = generate_docx(
            report_text=result["draft"],
            output_filename=output_path
        )
        
        return {
            "draft": result["draft"],
            "feedback": {
                "score": result.get("feedback", {}).get("score", 0.0),
                "suggestions": result.get("feedback", {}).get("suggestions", [])
            },
            "iterations": result.get("iterations", 1),
            "docx_url": f"/download/{os.path.basename(docx_path)}"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/refine-report", response_model=Dict[str, str])
async def refine_report(request: RefineReportRequest, background_tasks: BackgroundTasks):
    try:
        # Validate the report exists
        report_dir = Path(os.getcwd()) / "uploads" / request.report_id
        if not os.path.exists(report_dir):
            raise HTTPException(status_code=404, detail="Report not found")
        
        # Generate task ID
        task_id = str(uuid.uuid4())
        
        # Store task in cache
        tasks_cache[task_id] = {
            "status": "pending",
            "progress": 0.0,
            "started_at": time.time(),
            "report_id": request.report_id
        }
        
        # Start background task
        background_tasks.add_task(
            process_refinement,
            task_id,
            request.report_id,
            request.content,
            request.instructions
        )
        
        return {"task_id": task_id}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/task-status/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    if task_id not in tasks_cache:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task_data = tasks_cache[task_id]
    
    return {
        "task_id": task_id,
        "status": task_data["status"],
        "progress": task_data.get("progress"),
        "result": task_data.get("result"),
        "error": task_data.get("error")
    }

@router.get("/task-events/{task_id}")
async def get_task_events(task_id: str):
    """Server-Sent Events (SSE) endpoint for real-time task updates."""
    if task_id not in tasks_cache:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return StreamingResponse(
        event_generator(task_id),
        media_type="text/event-stream"
    )

async def event_generator(task_id: str) -> AsyncIterator[str]:
    """Generate SSE events for a task."""
    # Set up a queue for this client
    queue = asyncio.Queue()
    
    # Register this client
    if task_id not in event_subscribers:
        event_subscribers[task_id] = []
    event_subscribers[task_id].append(queue)
    
    try:
        # Send initial state
        task_data = tasks_cache[task_id]
        current_state = {
            "task_id": task_id,
            "status": task_data["status"],
            "progress": task_data.get("progress", 0),
        }
        yield f"data: {json.dumps(current_state)}\n\n"
        
        # Stream updates
        while True:
            if task_id not in tasks_cache:
                # Task was removed or expired
                yield f"data: {json.dumps({'task_id': task_id, 'status': 'expired'})}\n\n"
                break
                
            task_data = tasks_cache[task_id]
            if task_data["status"] in ["completed", "failed"]:
                # Send final state
                final_state = {
                    "task_id": task_id,
                    "status": task_data["status"],
                    "progress": task_data.get("progress", 1.0),
                }
                if task_data["status"] == "completed":
                    final_state["result"] = task_data.get("result")
                elif task_data["status"] == "failed":
                    final_state["error"] = task_data.get("error")
                    
                yield f"data: {json.dumps(final_state)}\n\n"
                break
            
            # Wait for an update or timeout
            try:
                update = await asyncio.wait_for(queue.get(), timeout=1.0)
                yield f"data: {json.dumps(update)}\n\n"
            except asyncio.TimeoutError:
                # Send heartbeat to keep connection alive
                yield f": heartbeat\n\n"
    
    finally:
        # Unregister this client
        if task_id in event_subscribers and queue in event_subscribers[task_id]:
            event_subscribers[task_id].remove(queue)
            if not event_subscribers[task_id]:
                del event_subscribers[task_id]

async def process_refinement(task_id: str, report_id: str, content: str, instructions: str):
    try:
        # Update task status and notify subscribers
        update_task_status(task_id, "processing", 0.1, "Initializing refinement process")
        
        # Create refinement prompt
        refinement_prompt = f"""
        CONTENUTO ATTUALE DEL REPORT:
        {content}
        
        ISTRUZIONI PER IL MIGLIORAMENTO:
        {instructions}
        """
        
        # Update progress at key stages
        update_task_status(task_id, "processing", 0.2, "Analyzing content and instructions")
        
        # Call the agent loop with the refinement prompt
        # Allow the agent loop to report progress
        result = await agent_loop.refine_report(
            refinement_prompt,
            progress_callback=lambda progress, status: update_task_status(
                task_id, "processing", 0.2 + progress * 0.6, status
            )
        )
        
        update_task_status(task_id, "processing", 0.8, "Generating DOCX file")
        
        # Generate unique filename for the DOCX
        filename = f"refined_report_{uuid.uuid4()}.docx"
        reports_dir = Path(os.getcwd()) / "generated_reports"
        reports_dir.mkdir(exist_ok=True)
        output_path = str(reports_dir / filename)
        
        # Generate DOCX (not async)
        docx_path = generate_docx(
            report_text=result["draft"],
            output_filename=output_path
        )
        
        # Store result
        tasks_cache[task_id]["result"] = {
            "draft": result["draft"],
            "feedback": {
                "score": result.get("feedback", {}).get("score", 0.0),
                "suggestions": result.get("feedback", {}).get("suggestions", [])
            },
            "iterations": result.get("iterations", 1),
            "docx_url": f"/download/{os.path.basename(docx_path)}",
            "from_cache": result.get("from_cache", False)
        }
        
        # Mark as completed
        update_task_status(task_id, "completed", 1.0, "Refinement completed successfully")
        
    except Exception as e:
        # Update task as failed
        update_task_status(task_id, "failed", None, str(e))
        
    # Set task to expire after 1 hour
    tasks_cache[task_id]["expires_at"] = time.time() + 3600

def update_task_status(task_id: str, status: str, progress: Optional[float] = None, message: Optional[str] = None):
    """Update task status and notify subscribers."""
    if task_id in tasks_cache:
        tasks_cache[task_id]["status"] = status
        
        if progress is not None:
            tasks_cache[task_id]["progress"] = progress
            
        if message:
            tasks_cache[task_id]["message"] = message
            
        # Notify subscribers
        update = {
            "task_id": task_id,
            "status": status,
            "progress": progress,
            "message": message
        }
        
        if task_id in event_subscribers:
            for queue in event_subscribers[task_id]:
                queue.put_nowait(update) 