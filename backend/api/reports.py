from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException
from utils.supabase_helper import async_supabase_client_context

# Use imports with fallbacks for better compatibility across environments
try:
    # First try imports without 'backend.' prefix (for Render)
    from models.report import ReportCreate
    from services.agent_service import agent_service
except ImportError:
    # Fallback to imports with 'backend.' prefix (for local dev)
    from models.report import ReportCreate
    from services.agent_service import agent_service

router = APIRouter(tags=["reports"])


@router.post("/", response_model=Dict[str, Any])
async def create_report(report_data: ReportCreate) -> Dict[str, Any]:
    """
    Create a new report using the AI agent loop.
    This initiates an asynchronous process and returns a report ID.
    """
    # Validate input data
    if not report_data.file_ids:
        raise HTTPException(status_code=400, detail="At least one file ID is required")

    # Initialize the agent loop
    result = await agent_service.generate_report(report_data)

    return result


@router.get("/{report_id}", response_model=Dict[str, Any])
async def get_report_status(report_id: str) -> Dict[str, Any]:
    """
    Get the status of a report generation process.
    """
    status = await agent_service.get_report_status(report_id)

    if status["status"] == "not_found":
        raise HTTPException(status_code=404, detail=f"Report {report_id} not found")

    return status


@router.delete("/{report_id}", response_model=Dict[str, Any])
async def cancel_report(report_id: str) -> Dict[str, Any]:
    """
    Cancel a report generation process.
    """
    success = await agent_service.cancel_report_generation(report_id)

    if not success:
        raise HTTPException(
            status_code=404, detail=f"Report {report_id} not found or already completed"
        )

    return {
        "report_id": report_id,
        "status": "cancelled",
        "message": "Report generation was successfully cancelled",
    }


@router.get("/{report_id}/download", response_model=Dict[str, Any])
async def download_report(report_id: str) -> Dict[str, Any]:
    """
    Get the download URL for a completed report.
    """
    status = await agent_service.get_report_status(report_id)

    if status["status"] == "not_found":
        raise HTTPException(status_code=404, detail=f"Report {report_id} not found")

    if status["status"] != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Report {report_id} is not ready for download (status: {status['status']})",
        )

    if "report_url" not in status:
        raise HTTPException(
            status_code=500, detail=f"Report URL not found for report {report_id}"
        )

    return {"report_id": report_id, "download_url": status["report_url"]}


@router.get("/{report_id}/files", response_model=Dict[str, Any])
async def get_report_files(report_id: str) -> Dict[str, Any]:
    """
    Get all files associated with a specific report.
    """
    try:
        async with async_supabase_client_context() as supabase:
            # First get the report to verify it exists
            report_response = await supabase.table("reports") \
                .select("document_ids") \
                .eq("report_id", report_id) \
                .execute()
            
            if not report_response.data:
                raise HTTPException(
                    status_code=404,
                    detail=f"Report {report_id} not found"
                )
            
            document_ids = report_response.data[0].get("document_ids", [])
            if not document_ids:
                return {
                    "report_id": report_id,
                    "files": []
                }
            
            # Get all files associated with the document IDs
            files = []
            for doc_id in document_ids:
                file_response = await supabase.table("files") \
                    .select("*") \
                    .eq("file_id", doc_id) \
                    .execute()
                
                if file_response.data:
                    files.extend(file_response.data)
            
            return {
                "report_id": report_id,
                "files": files
            }
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting files for report {report_id}: {str(e)}"
        )
