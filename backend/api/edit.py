from fastapi import APIRouter, HTTPException, Body
from typing import Dict
from models import ReportUpdate, Report
from services.ai_service import refine_report_text
from supabase import create_client, Client
from config import settings
from datetime import datetime
from utils.id_mapper import ensure_id_is_int

router = APIRouter()


@router.put("/{report_id}", response_model=Report)
async def update_report(
    report_id: str,
    data: ReportUpdate,
):
    """
    Update a generated report with manual edits
    """
    try:
        # Try to convert the report_id to an integer if it's a UUID
        try:
            db_id = ensure_id_is_int(report_id)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid report ID format: {str(e)}")
        
        # Initialize Supabase client
        supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        
        # Retrieve report from database using the integer ID
        response = supabase.table("reports").select("*").eq("id", db_id).execute()
        
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
        response = supabase.table("reports").update(update_data).eq("id", db_id).execute()
        
        if not response.data:
            raise HTTPException(status_code=500, detail="Failed to update report")
        
        return response.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating report: {str(e)}")


@router.post("/ai-refine", response_model=Report)
async def ai_refine_report(
    data: Dict = Body(...),
):
    """
    Use AI to refine a report based on additional instructions
    """
    # Required fields
    if "report_id" not in data:
        raise HTTPException(status_code=400, detail="report_id is required")
    if "instructions" not in data:
        raise HTTPException(status_code=400, detail="instructions is required")

    report_id = data["report_id"]
    instructions = data["instructions"]

    try:
        # Initialize Supabase client
        supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        
        # Retrieve report from database
        response = supabase.table("reports").select("*").eq("id", report_id).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail=f"Report with ID {report_id} not found")
        
        report = response.data[0]
        current_content = report["content"]

        # Refine content with AI
        refined_content = await refine_report_text(
            current_content, instructions
        )

        # Update report in database
        update_data = {
            "content": refined_content,
            "updated_at": datetime.now().isoformat()
        }
        
        response = supabase.table("reports").update(update_data).eq("id", report_id).execute()
        
        if not response.data:
            raise HTTPException(status_code=500, detail="Failed to update report")
        
        return response.data[0]
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error refining report: {str(e)}"
        )
