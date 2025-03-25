# Standard library imports
import logging
from datetime import datetime
from typing import Dict, Optional, Any
from uuid import UUID

# Third-party imports
from fastapi import APIRouter, HTTPException, Query

# Local imports
try:
    # First try imports without 'backend.' prefix (for Render)
    from api.schemas import APIResponse
    from models import (
        Report,
        ReportUpdate,
        ReportVersion,
        ReportVersionCreate,
        ReportVersionResponse,
    )
    from services.ai_service import refine_report_text
    from utils.error_handler import api_error_handler
    from utils.supabase_helper import async_supabase_client_context
except ImportError:
    # Fallback to imports with 'backend.' prefix (for local dev)
    from api.schemas import APIResponse
    from models import (
        Report,
        ReportUpdate,
        ReportVersion,
        ReportVersionCreate,
        ReportVersionResponse,
    )
    from services.ai_service import refine_report_text
    from utils.error_handler import api_error_handler
    from utils.supabase_helper import async_supabase_client_context

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()


@router.put("/{report_id}", response_model=APIResponse[Report])
@api_error_handler
async def update_report(
    report_id: UUID,
    data: ReportUpdate,
    create_version: bool = False,
    version_description: Optional[str] = None,
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
    # Retrieve report from database
    async with async_supabase_client_context() as supabase:
        response = (
            await supabase.table("reports")
            .select("*")
            .eq("report_id", str(report_id))
            .execute()
        )

        if not response.data:
            raise HTTPException(
                status_code=404, detail=f"Report with ID {report_id} not found"
            )

        report_data = response.data[0]
        report = Report(**report_data)

        # Create a new version if requested
        if create_version and data.content:
            # Get current version number
            current_version = report.current_version or 1
            new_version_number = current_version + 1

            # Create version record
            version_data = ReportVersionCreate(
                report_id=report_id,
                version_number=new_version_number,
                content=data.content,
                changes_description=version_description,
            )

            version_response = (
                await supabase.table("report_versions")
                .insert(version_data.dict())
                .execute()
            )
            if not version_response.data:
                raise HTTPException(
                    status_code=500, detail="Failed to create version record"
                )

            # Update current version number in the report
            data.current_version = new_version_number

        # Prepare update data
        update_data = data.dict(exclude_unset=True)
        update_data["updated_at"] = datetime.now().isoformat()

        # Update report
        update_response = (
            await supabase.table("reports")
            .update(update_data)
            .eq("report_id", str(report_id))
            .execute()
        )

        if not update_response.data:
            raise HTTPException(status_code=500, detail="Failed to update report")

        return APIResponse(data=Report(**update_response.data[0]))


@router.post("/{report_id}/refine", response_model=APIResponse[Report])
@api_error_handler
async def ai_refine_report(
    report_id: UUID,
    data: Dict[str, Any] = Query(...),
):
    """
    Refine a report using AI

    Args:
        report_id: UUID of the report to refine
        data: Dictionary containing refinement instructions

    Returns:
        Standardized API response with refined report data
    """
    instructions = data.get("instructions")
    if not instructions:
        raise HTTPException(
            status_code=400, detail="Refinement instructions are required"
        )

    # Initialize Supabase client
    async with async_supabase_client_context() as supabase:
        # Get current report content
        response = (
            await supabase.table("reports")
            .select("*")
            .eq("report_id", str(report_id))
            .execute()
        )

        if not response.data:
            raise HTTPException(
                status_code=404, detail=f"Report with ID {report_id} not found"
            )

        report_data = response.data[0]
        report = Report(**report_data)

        # Refine the report content using AI
        refined_result = await refine_report_text(
            report_id, instructions, report_data["content"]
        )
        refined_content = refined_result["content"]

        # Create a new version record
        current_version = report.current_version or 1
        new_version_number = current_version + 1

        # Create version record
        version_data = ReportVersionCreate(
            report_id=report_id,
            version_number=new_version_number,
            content=refined_content,
            changes_description=f"AI refinement based on instructions: {instructions}",
        )

        version_response = (
            await supabase.table("report_versions")
            .insert(version_data.dict())
            .execute()
        )
        if not version_response.data:
            raise HTTPException(
                status_code=500, detail="Failed to create version record"
            )

        # Update the report with refined content
        update_data = {
            "content": refined_content,
            "current_version": new_version_number,
            "updated_at": datetime.now().isoformat(),
        }

        update_response = (
            await supabase.table("reports")
            .update(update_data)
            .eq("report_id", str(report_id))
            .execute()
        )

        if not update_response.data:
            raise HTTPException(status_code=500, detail="Failed to update report")

        return APIResponse(data=Report(**update_response.data[0]))


@router.get("/{report_id}/versions", response_model=APIResponse[ReportVersionResponse])
@api_error_handler
async def get_report_versions(
    report_id: UUID,
):
    """
    Get all versions of a report

    Args:
        report_id: UUID of the report

    Returns:
        List of report versions and current version number
    """
    async with async_supabase_client_context() as supabase:
        # Check if report exists and get current version
        report_response = (
            await supabase.table("reports")
            .select("*")
            .eq("report_id", str(report_id))
            .execute()
        )

        if not report_response.data:
            raise HTTPException(
                status_code=404, detail=f"Report with ID {report_id} not found"
            )

        report = Report(**report_response.data[0])

        # Get versions
        versions_response = (
            await supabase.table("report_versions")
            .select("*")
            .eq("report_id", str(report_id))
            .order("version_number", desc=True)
            .execute()
        )

        versions = [ReportVersion(**v) for v in versions_response.data]

        return APIResponse(
            data=ReportVersionResponse(
                versions=versions, current_version=report.current_version or 1
            )
        )


@router.get(
    "/{report_id}/versions/{version_number}", response_model=APIResponse[ReportVersion]
)
@api_error_handler
async def get_report_version(
    report_id: UUID,
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
    async with async_supabase_client_context() as supabase:
        # Get specific version
        version_response = (
            await supabase.table("report_versions")
            .select("*")
            .eq("report_id", str(report_id))
            .eq("version_number", version_number)
            .execute()
        )

        if not version_response.data:
            raise HTTPException(
                status_code=404,
                detail=f"Version {version_number} not found for report {report_id}",
            )

        return APIResponse(data=ReportVersion(**version_response.data[0]))


@router.post(
    "/{report_id}/versions/{version_number}/revert", response_model=APIResponse[Report]
)
@api_error_handler
async def revert_to_version(
    report_id: UUID,
    version_number: int,
):
    """
    Revert a report to a specific version

    Args:
        report_id: UUID of the report
        version_number: Version number to revert to

    Returns:
        Updated report data
    """
    async with async_supabase_client_context() as supabase:
        # Get the target version
        version_response = (
            await supabase.table("report_versions")
            .select("*")
            .eq("report_id", str(report_id))
            .eq("version_number", version_number)
            .execute()
        )

        if not version_response.data:
            raise HTTPException(
                status_code=404,
                detail=f"Version {version_number} not found for report {report_id}",
            )

        target_version = ReportVersion(**version_response.data[0])

        # Get current report data
        report_response = (
            await supabase.table("reports")
            .select("*")
            .eq("report_id", str(report_id))
            .execute()
        )

        if not report_response.data:
            raise HTTPException(
                status_code=404, detail=f"Report with ID {report_id} not found"
            )

        report = Report(**report_response.data[0])
        current_version = report.current_version or 1
        new_version_number = current_version + 1

        # Create a new version record for the revert action
        version_data = ReportVersionCreate(
            report_id=report_id,
            version_number=new_version_number,
            content=target_version.content,
            changes_description=f"Reverted to version {version_number}",
        )

        version_response = (
            await supabase.table("report_versions")
            .insert(version_data.dict())
            .execute()
        )
        if not version_response.data:
            raise HTTPException(
                status_code=500, detail="Failed to create version record"
            )

        # Update the report content
        update_data = {
            "content": target_version.content,
            "current_version": new_version_number,
            "updated_at": datetime.now().isoformat(),
        }

        update_response = (
            await supabase.table("reports")
            .update(update_data)
            .eq("report_id", str(report_id))
            .execute()
        )

        if not update_response.data:
            raise HTTPException(status_code=500, detail="Failed to update report")

        return APIResponse(data=Report(**update_response.data[0]))
