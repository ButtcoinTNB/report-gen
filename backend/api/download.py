from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi import File
from fastapi.responses import FileResponse
from typing import Optional, Dict, Any, List
from uuid import UUID
from pydantic import UUID4, BaseModel
from fastapi import status
import os
import glob
import json
import traceback
import hashlib
from datetime import datetime

# Use imports with fallbacks for better compatibility across environments
try:
    # First try imports without 'backend.' prefix (for Render)
    from services.download_service import download_service
    from utils.auth import get_current_user
    from config import settings
    from utils.storage import get_report_path, does_file_exist, validate_path, get_safe_file_path
    from services.docx_service import docx_service
    from utils.supabase_helper import create_supabase_client, supabase_client_context
    from utils.error_handler import handle_exception, api_error_handler, logger
    from utils.file_utils import safe_path_join
    from api.schemas import APIResponse
    from supabase import create_client, Client
except ImportError:
    # Fallback to imports with 'backend.' prefix (for local dev)
    from backend.services.download_service import download_service
    from backend.utils.auth import get_current_user
    from backend.config import settings
    from backend.utils.storage import get_report_path, does_file_exist, validate_path, get_safe_file_path
    from backend.services.docx_service import docx_service
    from backend.utils.supabase_helper import create_supabase_client, supabase_client_context
    from backend.utils.error_handler import handle_exception, api_error_handler, logger
    from backend.utils.file_utils import safe_path_join
    from backend.api.schemas import APIResponse
    from supabase import create_client, Client

# Import format functions to avoid circular imports later
try:
    from api.format import format_final, update_report_file_path, get_reference_metadata
    from services.pdf_formatter import format_report_as_pdf
except ImportError:
    try:
        from backend.api.format import format_final, update_report_file_path, get_reference_metadata
        from backend.services.pdf_formatter import format_report_as_pdf
    except ImportError:
        # This allows for cleaner error handling if imports fail
        logger.warning("Could not import formatting functions, will import when needed")

router = APIRouter()


def get_report_content(report_id: UUID4) -> Optional[str]:
    """
    Retrieve the actual report content (markdown text) from any available source.
    This is a more thorough content retrieval function that checks all possible storage locations.
    
    Args:
        report_id: The UUID of the report
        
    Returns:
        The report content as text, or None if not found
    """
    logger.info(f"Attempting to retrieve content for report ID: {report_id}")
    report_content = None
    
    # Check if report exists in Supabase
    supabase = create_supabase_client()
    response = supabase.table("reports").select("content").eq("report_id", str(report_id)).execute()
    
    if response.data and response.data[0].get("content"):
        return response.data[0]["content"]
    
    # Check local storage as fallback
    uploads_dir = os.path.abspath(settings.UPLOAD_DIR)
    report_dir_name = str(report_id)
    
    # Validate the report_id before using it in path construction
    is_valid, report_dir = validate_path(report_dir_name, uploads_dir)
    if not is_valid:
        logger.error(f"Invalid report ID format or path: {report_id}")
        return None
    
    if os.path.exists(report_dir) and os.path.isdir(report_dir):
        # Look for content files securely
        for entry in os.listdir(report_dir):
            if entry.startswith("content") and entry.endswith(".txt"):
                content_file_path = get_safe_file_path(report_dir, entry)
                if content_file_path and os.path.isfile(content_file_path):
                    try:
                        with open(content_file_path, 'r', encoding='utf-8') as f:
                            return f.read()
                    except Exception as e:
                        logger.error(f"Error reading content file: {str(e)}")
    
    return None


def fetch_report_path_from_supabase(report_id: UUID4) -> Optional[str]:
    """
    Get the report file path from Supabase
    """
    try:
        supabase = create_supabase_client()
        response = supabase.table("reports").select("file_path").eq("report_id", str(report_id)).execute()
        
        if response.data and len(response.data) > 0 and response.data[0].get("file_path"):
            file_path = response.data[0]["file_path"]
            
            # Validate the file path
            base_dir = os.path.abspath(settings.GENERATED_REPORTS_DIR)
            is_valid, validated_path = validate_path(file_path, base_dir)
            
            if is_valid and os.path.exists(validated_path):
                return validated_path
            
            # If the path wasn't valid or file doesn't exist, log this
            logger.warning(f"File path from Supabase is invalid or file doesn't exist: {file_path}")
        
    except Exception as e:
        logger.error(f"Error fetching report path from Supabase: {str(e)}")
    
    return None


def find_report_file_locally(report_id: UUID4) -> Optional[str]:
    """
    Find a report file in the local filesystem
    """
    report_dir = safe_path_join(settings.UPLOAD_DIR, str(report_id))
    if not os.path.exists(report_dir):
        return None
        
    # Look for report files
    patterns = [
        f"report_{report_id}*.docx",
        f"*{report_id}*.docx"
    ]
    
    for pattern in patterns:
        matching_files = glob.glob(safe_path_join(settings.GENERATED_REPORTS_DIR, pattern))
        if matching_files:
            return matching_files[0]
    
    return None


def find_docx_file_locally(report_id: UUID4) -> Optional[str]:
    """
    Find a DOCX file in the local filesystem
    """
    # First check in the generated reports directory
    patterns = [
        f"report_{report_id}*.docx",
        f"*{report_id}*.docx"
    ]
    
    for pattern in patterns:
        matching_files = glob.glob(safe_path_join(settings.GENERATED_REPORTS_DIR, pattern))
        if matching_files:
            return matching_files[0]
    
    # Then check in the upload directory
    report_dir = safe_path_join(settings.UPLOAD_DIR, str(report_id))
    if os.path.exists(report_dir):
        docx_files = glob.glob(safe_path_join(report_dir, "*.docx"))
        if docx_files:
            return docx_files[0]
    
    return None


class DownloadReportResponse(BaseModel):
    """Response model for generic report download endpoint"""
    report_id: UUID4
    format: str
    file_path: Optional[str] = None

@router.get("/{report_id}", response_model=APIResponse[DownloadReportResponse])
@api_error_handler
async def download_report(
    report_id: UUID4, 
    format: str = Query("docx", description="Format of the report, either 'docx' or 'pdf'"),
    user: Optional[Dict[str, Any]] = Depends(get_current_user)
):
    """
    Download a generated report in DOCX or PDF format
    
    Args:
        report_id: UUID of the report to download
        format: Format of the report (docx or pdf)
        user: Optional authenticated user
        
    Returns:
        Standardized API response with appropriate file response
    """
    # Validate format
    if format.lower() not in ["docx", "pdf"]:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format: {format}. Only 'docx' and 'pdf' are supported."
        )
    
    # Initialize Supabase client
    supabase = create_supabase_client()
    
    # Find the report in Supabase
    response = supabase.table("reports").select("*").eq("report_id", str(report_id)).execute()
    
    if not response.data:
        raise HTTPException(
            status_code=404,
            detail=f"Report not found with ID: {report_id}"
        )
    
    report = response.data[0]
    
    # Determine which format to return
    if format.lower() == "docx":
        return await download_docx_report(report_id)
    else:  # PDF
        raise HTTPException(
            status_code=501,
            detail="PDF download not implemented yet"
        )


class ServeReportFileResponse(BaseModel):
    """Response model for serving generic report file endpoint"""
    report_id: UUID4
    file_path: str

@router.get("/file/{report_id}", response_model=APIResponse[ServeReportFileResponse])
@api_error_handler
async def serve_report_file(report_id: UUID4):
    """
    Serve a report file directly (without downloading)
    
    Args:
        report_id: UUID of the report to serve
        
    Returns:
        Standardized API response with file response
    """
    # Get file path from Supabase
    supabase = create_supabase_client()
    response = supabase.table("reports").select("file_path").eq("report_id", str(report_id)).execute()
    
    if not response.data or not response.data[0].get("file_path"):
        raise HTTPException(
            status_code=404,
            detail="Report file not found"
        )
    
    file_path = response.data[0]["file_path"]
    
    # Check if file exists locally
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=404,
            detail="Report file not found on server"
        )
    
    # Return the file
    return FileResponse(
        path=file_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )


class CleanupResponse(BaseModel):
    """Response model for cleanup endpoint"""
    deleted_files: List[str]
    directory: Optional[str] = None

@router.post("/cleanup/{report_id}", response_model=APIResponse[CleanupResponse])
async def cleanup_report_files(report_id: UUID4):
    """
    Clean up all temporary files associated with a report after it has been successfully
    downloaded. This ensures that uploaded files don't persist in storage.
    
    Args:
        report_id: The UUID of the report to clean up files for
        
    Returns:
        Standardized API response with cleanup details
    """
    # Define paths for report files
    report_dir = safe_path_join(settings.UPLOAD_DIR, str(report_id))
    deleted_files = []
    
    try:
        # Get file paths from Supabase
        supabase = create_supabase_client()
        response = supabase.table("reports").select("file_path").eq("report_id", str(report_id)).execute()
        
        if response.data and response.data[0].get("file_path"):
            docx_path = response.data[0]["file_path"]
            if os.path.exists(docx_path):
                os.remove(docx_path)
                deleted_files.append(docx_path)
                print(f"Deleted final DOCX file: {docx_path}")
        
        # Check for report-related DOCX files in the generated_reports directory
        try:
            # Create a pattern for filenames
            patterns = [
                f"report_{report_id}*.docx",
                f"*{report_id}*.docx"
            ]
            
            for pattern in patterns:
                matching_files = glob.glob(safe_path_join(settings.GENERATED_REPORTS_DIR, pattern))
                for file_path in matching_files:
                    try:
                        os.remove(file_path)
                        deleted_files.append(file_path)
                        print(f"Deleted generated DOCX file: {file_path}")
                    except Exception as e:
                        print(f"Error deleting generated file {file_path}: {str(e)}")
        except Exception as e:
            print(f"Error cleaning up generated files: {str(e)}")
        
        # Delete the upload directory and its contents
        if os.path.exists(report_dir) and os.path.isdir(report_dir):
            # Get list of files before deletion for logging
            files_to_delete = os.listdir(report_dir)
            
            # Remove all files in the directory
            for filename in files_to_delete:
                file_path = safe_path_join(report_dir, filename)
                if os.path.isfile(file_path):
                    os.remove(file_path)
                    deleted_files.append(file_path)
                    print(f"Deleted uploaded file: {file_path}")
                    
            # Remove the directory itself
            os.rmdir(report_dir)
            print(f"Deleted directory: {report_dir}")
        
        # Update database status
        try:
            # Mark report as cleaned up in database
            supabase.table("reports").update({"files_cleaned": True}).eq("report_id", str(report_id)).execute()
            print(f"Updated database for report {report_id}: files_cleaned=True")
            
        except Exception as e:
            print(f"Error updating database status: {str(e)}")
        
        return APIResponse(
            status="success",
            data=CleanupResponse(
                deleted_files=deleted_files,
                directory=str(report_dir) if os.path.exists(report_dir) else None
            ),
            message=f"Successfully cleaned up {len(deleted_files)} files for report {report_id}"
        )
    except Exception as e:
        logger.error(f"Error cleaning up report files: {str(e)}")
        return APIResponse(
            status="error",
            message=f"Failed to clean up report files: {str(e)}",
            code="CLEANUP_ERROR"
        )


class DocxReportResponse(BaseModel):
    """Response model for DOCX report download endpoint"""
    report_id: UUID4
    file_path: str
    filename: str

@router.get("/docx/{report_id}", response_model=APIResponse[DocxReportResponse])
@api_error_handler
async def download_docx_report(report_id: UUID4):
    """
    Download a finalized report as DOCX by ID.
    
    Args:
        report_id: UUID of the report to download
        
    Returns:
        Standardized API response with FileResponse for the DOCX file
    """
    # Get file path from Supabase
    supabase = create_supabase_client()
    response = supabase.table("reports").select("file_path").eq("report_id", str(report_id)).execute()
    
    if not response.data or not response.data[0].get("file_path"):
        raise HTTPException(status_code=404, detail="Report file not found")
    
    file_path = response.data[0]["file_path"]
    
    # Check if file exists locally
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Report file not found on server")
    
    # Check if the file is a DOCX file
    if not file_path.lower().endswith('.docx'):
        # Try to find a matching DOCX file with the same base name
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        docx_path = safe_path_join(settings.GENERATED_REPORTS_DIR, f"{base_name}.docx")
        
        if not os.path.exists(docx_path):
            raise HTTPException(
                status_code=404, 
                detail="DOCX version of this report not found. Please generate it first."
            )
        file_path = docx_path
    
    # Prepare the FileResponse
    response = FileResponse(
        path=file_path,
        filename=f"report_{report_id}.docx",
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    
    # Schedule cleanup to run after the response is sent (in background)
    import asyncio
    asyncio.create_task(cleanup_report_files(report_id))
    print(f"Scheduled cleanup for report {report_id} after download")
    
    return response


class DocxFileResponse(BaseModel):
    """Response model for serving DOCX file endpoint"""
    file_path: str
    report_id: UUID4

@router.get("/file/docx/{report_id}", response_model=APIResponse[DocxFileResponse])
@api_error_handler
async def serve_docx_report_file(report_id: UUID4):
    """
    Serve a DOCX report file directly (without downloading)
    
    Args:
        report_id: UUID of the report
        
    Returns:
        Standardized API response with FileResponse for the DOCX
    """
    # Get file path from Supabase
    supabase = create_supabase_client()
    response = supabase.table("reports").select("file_path").eq("report_id", str(report_id)).execute()
    
    if not response.data or not response.data[0].get("file_path"):
        raise HTTPException(status_code=404, detail="Report file not found")
    
    file_path = response.data[0]["file_path"]
    
    # Check if file exists locally
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Report file not found on server")
    
    # Return the file
    return FileResponse(
        path=file_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )


class ReportFileResponse(BaseModel):
    """Response model for report file info endpoint"""
    file_path: str
    file_exists: bool
    content_type: str

@router.get("/file/{report_id}/info", response_model=APIResponse[ReportFileResponse])
@api_error_handler
async def get_report_file_info(report_id: UUID4):
    """
    Get information about a report file without downloading it
    
    Args:
        report_id: The ID of the report
        
    Returns:
        Information about the report file including path and content type
    """
    async with supabase_client_context() as supabase:
        report_response = await supabase.table("reports").select("*").eq("report_id", str(report_id)).execute()
        
        if not report_response.data:
            raise HTTPException(status_code=404, detail=f"Report {report_id} not found")
            
        report = report_response.data[0]
        
        # Define the expected file path
        content_file_path = os.path.join(settings.REPORTS_DIR, f"{report_id}.txt")
        
        # Check if file exists locally
        file_exists = os.path.exists(content_file_path)
        
        # Determine content type using FileProcessor
        content_type = FileProcessor.get_mime_type(content_file_path) if file_exists else "text/plain"
        
        return APIResponse(
            status="success",
            data=ReportFileResponse(
                file_path=content_file_path,
                file_exists=file_exists,
                content_type=content_type
            )
        )

@router.get("/{report_id}")
@api_error_handler
async def download_report_content(report_id: UUID4):
    """
    Download the report content as text
    
    Args:
        report_id: The ID of the report
        
    Returns:
        The report content as a text file
    """
    async with supabase_client_context() as supabase:
        report_response = await supabase.table("reports").select("*").eq("report_id", str(report_id)).execute()
        
        if not report_response.data:
            raise HTTPException(status_code=404, detail=f"Report {report_id} not found")
            
        report = report_response.data[0]
        
        # Check if we have a file on disk
        content_file_path = os.path.join(settings.REPORTS_DIR, f"{report_id}.txt")
        
        if os.path.exists(content_file_path):
            logger.info(f"Serving report file from disk: {content_file_path}")
            with open(content_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        else:
            # If not on disk, get from database
            logger.info(f"Report file not found on disk, using content from database")
            content = report.get("content", "")
            
            # Create the reports directory if it doesn't exist
            os.makedirs(settings.REPORTS_DIR, exist_ok=True)
            
            # Save to disk for future requests
            with open(content_file_path, 'w', encoding='utf-8') as f:
                f.write(content)
        
        # Return file
        return FileResponse(
            content_file_path,
            media_type="text/plain",
            filename=f"report_{report_id}.txt"
        )

@router.get("/templates/{template_id}")
async def get_template(
    template_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get template information and download URL."""
    try:
        template = await download_service.get_template(template_id)
        return template
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/reference-reports/{report_id}")
async def get_reference_report(
    report_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get reference report information and download URL."""
    try:
        report = await download_service.get_reference_report(report_id)
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/reports/{report_id}")
async def get_report(
    report_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get report information and download URL."""
    try:
        report = await download_service.get_report(report_id)
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/download/{bucket}/{file_path:path}")
async def download_file(
    bucket: str,
    file_path: str,
    current_user: dict = Depends(get_current_user)
):
    """Download a file directly from Supabase storage."""
    try:
        file_bytes = await download_service.download_file(bucket, file_path)
        return file_bytes
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
