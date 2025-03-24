from fastapi import APIRouter, HTTPException, Depends, Body
from typing import Dict, Any, List, Optional
import json
import os
import tempfile
import time
import uuid

# Use imports with fallbacks for better compatibility across environments
try:
    # First try imports without 'backend.' prefix (for Render)
    from config import settings
    from services.pdf_processor import process_file, extract_text_from_pdf
    from services.docx_formatter import format_report_as_docx
    from services.report_generator import generate_report_content, generate_editable_outline
    from utils.file_utils import safe_path_join, create_temp_file
    from utils.security import get_user_from_request
    from utils.metrics import MetricsCollector
except ImportError:
    # Fallback to imports with 'backend.' prefix (for local dev)
    from backend.config import settings
    from backend.services.pdf_processor import process_file, extract_text_from_pdf
    from backend.services.docx_formatter import format_report_as_docx
    from backend.services.report_generator import generate_report_content, generate_editable_outline
    from backend.utils.file_utils import safe_path_join, create_temp_file
    from backend.utils.security import get_user_from_request
    from backend.utils.metrics import MetricsCollector

router = APIRouter()

# Metrics collector for tracking performance
metrics = MetricsCollector()

# Dictionary to store editing sessions
editing_sessions = {}


class UpdateReportResponse(BaseModel):
    """Response model for report update endpoint"""
    report_id: str
    title: str
    content: str
    is_finalized: bool
    updated_at: str
    current_version: int


@router.put("/{report_id}", response_model=APIResponse[Report])
@api_error_handler
async def update_report(
    report_id: UUID4,
    data: ReportUpdate,
    create_version: bool = False,
    version_description: str = None,
):
    """
    Update a generated report with manual edits
    
    Args:
        report_id: UUID of the report to update
        data: Update data containing title, content, and finalization status
        create_version: Whether to create a new version record
        version_description: Description of changes in this version
        
    Returns:
        Standardized API response with updated report data
    """
    supabase = create_supabase_client()
    
    # Retrieve report from database
    response = supabase.table("reports").select("*").eq("report_id", str(report_id)).execute()
    
    if not response.data:
        raise HTTPException(status_code=404, detail=f"Report with ID {report_id} not found")
    
    report = response.data[0]
    
    # Create a new version if requested
    if create_version and data.content:
        # Get current version number
        current_version = report.get("current_version", 1)
        new_version_number = current_version + 1
        
        # Create version record
        version_data = ReportVersionCreate(
            report_id=report_id,
            version_number=new_version_number,
            content=data.content,
            changes_description=version_description,
        )
        
        version_response = supabase.table("report_versions").insert(version_data.dict()).execute()
        if not version_response.data:
            raise HTTPException(status_code=500, detail="Failed to create version record")
        
        # Update current version number in the report
        data.current_version = new_version_number
    
    # Prepare update data
    update_data = data.dict(exclude_unset=True)
    update_data["updated_at"] = datetime.now().isoformat()
    
    # Update report in database
    response = supabase.table("reports").update(update_data).eq("report_id", str(report_id)).execute()
    
    if not response.data:
        raise HTTPException(status_code=500, detail="Failed to update report")
    
    return APIResponse(data=Report(**response.data[0]))


class AIRefineResponse(BaseModel):
    """Response model for AI report refinement endpoint"""
    report_id: str
    content: str
    updated_at: str
    current_version: int


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
    
    # Create a new version record
    current_version = report.get("current_version", 1)
    new_version_number = current_version + 1
    
    # Create version record
    version_id = uuid4()
    version_data = {
        "version_id": str(version_id),
        "report_id": str(report_id),
        "version_number": new_version_number,
        "content": refined_content,
        "title": report.get("title"),
        "changes_description": f"AI refinement based on instructions: {instructions}",
        "created_by_ai": True,
        "created_at": datetime.now().isoformat()
    }
    
    version_response = supabase.table("report_versions").insert(version_data).execute()
    if not version_response.data:
        raise HTTPException(status_code=500, detail="Failed to create version record")
    
    # Update the report with refined content
    update_data = {
        "content": refined_content,
        "current_version": new_version_number,
        "updated_at": datetime.now().isoformat()
    }
    
    response = supabase.table("reports").update(update_data).eq("report_id", str(report_id)).execute()
    
    if not response.data:
        raise HTTPException(status_code=500, detail="Failed to update report")
    
    return response.data[0]


@router.get("/{report_id}/versions", response_model=APIResponse[ReportVersionResponse])
@api_error_handler
async def get_report_versions(
    report_id: UUID4,
):
    """
    Get version history for a report
    
    Args:
        report_id: UUID of the report
        
    Returns:
        List of report versions and current version number
    """
    supabase = create_supabase_client()
    
    # Check if report exists and get current version
    report_response = supabase.table("reports").select("*").eq("report_id", str(report_id)).execute()
    
    if not report_response.data:
        raise HTTPException(status_code=404, detail=f"Report with ID {report_id} not found")
    
    report = Report(**report_response.data[0])
    
    # Get versions
    versions_response = supabase.table("report_versions").select("*").eq("report_id", str(report_id)).order("version_number", desc=True).execute()
    
    versions = [ReportVersion(**v) for v in versions_response.data]
    
    return APIResponse(data=ReportVersionResponse(
        versions=versions,
        current_version=report.current_version
    ))


@router.get("/{report_id}/versions/{version_number}", response_model=APIResponse[ReportVersion])
@api_error_handler
async def get_report_version(
    report_id: UUID4,
    version_number: int,
):
    """
    Get a specific version of a report
    
    Args:
        report_id: UUID of the report
        version_number: Version number to retrieve
        
    Returns:
        Report version data
    """
    supabase = create_supabase_client()
    
    # Get specific version
    version_response = supabase.table("report_versions").select("*").eq("report_id", str(report_id)).eq("version_number", version_number).execute()
    
    if not version_response.data:
        raise HTTPException(status_code=404, detail=f"Version {version_number} not found for report {report_id}")
    
    return APIResponse(data=ReportVersion(**version_response.data[0]))


@router.post("/{report_id}/revert/{version_number}", response_model=APIResponse[Report])
@api_error_handler
async def revert_to_version(
    report_id: UUID4,
    version_number: int,
):
    """
    Revert a report to a previous version
    
    Args:
        report_id: UUID of the report
        version_number: Version number to revert to
        
    Returns:
        Updated report data
    """
    supabase = create_supabase_client()
    
    # Get the target version
    version_response = supabase.table("report_versions").select("*").eq("report_id", str(report_id)).eq("version_number", version_number).execute()
    
    if not version_response.data:
        raise HTTPException(status_code=404, detail=f"Version {version_number} not found for report {report_id}")
    
    target_version = ReportVersion(**version_response.data[0])
    
    # Get current report data
    report_response = supabase.table("reports").select("*").eq("report_id", str(report_id)).execute()
    
    if not report_response.data:
        raise HTTPException(status_code=404, detail=f"Report with ID {report_id} not found")
    
    report = Report(**report_response.data[0])
    new_version_number = report.current_version + 1
    
    # Create a new version record for the revert action
    version_data = ReportVersionCreate(
        report_id=report_id,
        version_number=new_version_number,
        content=target_version.content,
        changes_description=f"Reverted to version {version_number}",
    )
    
    version_response = supabase.table("report_versions").insert(version_data.dict()).execute()
    if not version_response.data:
        raise HTTPException(status_code=500, detail="Failed to create version record")
    
    # Update the report content
    update_data = {
        "content": target_version.content,
        "current_version": new_version_number,
        "updated_at": datetime.now().isoformat()
    }
    
    response = supabase.table("reports").update(update_data).eq("report_id", str(report_id)).execute()
    
    if not response.data:
        raise HTTPException(status_code=500, detail="Failed to update report")
    
    return APIResponse(data=Report(**response.data[0]))
