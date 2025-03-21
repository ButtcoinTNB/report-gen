from fastapi import APIRouter, HTTPException, Body
from typing import Dict, Any
from uuid import UUID
from pydantic import UUID4, BaseModel
from datetime import datetime

# Use imports with fallbacks for better compatibility across environments
try:
    # First try imports without 'backend.' prefix (for Render)
    from models import ReportUpdate, Report
    from services.ai_service import refine_report_text
    from utils.supabase_helper import create_supabase_client
    from utils.error_handler import api_error_handler
    from api.schemas import APIResponse
except ImportError:
    # Fallback to imports with 'backend.' prefix (for local dev)
    from models import ReportUpdate, Report
    from services.ai_service import refine_report_text
    from utils.supabase_helper import create_supabase_client
    from utils.error_handler import api_error_handler
    from api.schemas import APIResponse

router = APIRouter()


class UpdateReportResponse(BaseModel):
    """Response model for report update endpoint"""
    report_id: str
    title: str
    content: str
    is_finalized: bool
    updated_at: str


@router.put("/{report_id}", response_model=APIResponse[UpdateReportResponse])
@api_error_handler
async def update_report(
    report_id: UUID4,
    data: ReportUpdate,
):
    """
    Update a generated report with manual edits
    
    Args:
        report_id: UUID of the report to update
        data: Update data containing title, content, and finalization status
        
    Returns:
        Standardized API response with updated report data
    """
    # Initialize Supabase client
    supabase = create_supabase_client()
    
    # Retrieve report from database
    response = supabase.table("reports").select("*").eq("report_id", str(report_id)).execute()
    
    if not response.data:
        raise HTTPException(status_code=404, detail=f"Report with ID {report_id} not found")
    
    report = response.data[0]
    
    # Prepare update data
    update_data = {}
    if data.title is not None:
        update_data["title"] = data.title
    if data.content is not None:
        update_data["content"] = data.content
    if data.is_finalized is not None:
        update_data["is_finalized"] = data.is_finalized
    
    update_data["updated_at"] = datetime.now().isoformat()
    
    # Update report in database
    response = supabase.table("reports").update(update_data).eq("report_id", str(report_id)).execute()
    
    if not response.data:
        raise HTTPException(status_code=500, detail="Failed to update report")
    
    return response.data[0]


class AIRefineResponse(BaseModel):
    """Response model for AI report refinement endpoint"""
    report_id: str
    content: str
    updated_at: str


@router.post("/ai-refine", response_model=APIResponse[AIRefineResponse])
@api_error_handler
async def ai_refine_report(
    data: Dict[str, Any] = Body(...),
):
    """
    Refine a report using AI
    
    Args:
        data: Dictionary containing report_id and instructions
        
    Returns:
        Standardized API response with refined report data
    """
    report_id = UUID4(data.get("report_id"))
    instructions = data.get("instructions")
    
    if not report_id or not instructions:
        raise HTTPException(status_code=400, detail="Missing report_id or instructions")
    
    # Initialize Supabase client
    supabase = create_supabase_client()
    
    # Get current report content
    response = supabase.table("reports").select("*").eq("report_id", str(report_id)).execute()
    
    if not response.data:
        raise HTTPException(status_code=404, detail=f"Report with ID {report_id} not found")
    
    report = response.data[0]
    
    # Refine the report content using AI
    refined_content = await refine_report_text(report["content"], instructions)
    
    # Update the report with refined content
    update_data = {
        "content": refined_content,
        "updated_at": datetime.now().isoformat()
    }
    
    response = supabase.table("reports").update(update_data).eq("report_id", str(report_id)).execute()
    
    if not response.data:
        raise HTTPException(status_code=500, detail="Failed to update report")
    
    return response.data[0]
