from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import FileResponse
import os
import glob
import json
from uuid import UUID
from pydantic import UUID4
from supabase import create_client, Client
from config import settings
import traceback
import hashlib
from datetime import datetime
from utils.auth import get_current_user
from utils.storage import get_report_path, does_file_exist
from services.docx_service import docx_service
from utils.supabase_helper import create_supabase_client, supabase_client_context
from typing import Optional, Dict, Any
from fastapi import status

# Import format functions to avoid circular imports later
try:
    from api.format import format_final, update_report_file_path, get_reference_metadata
    from services.pdf_formatter import format_report_as_pdf
except ImportError:
    # This allows for cleaner error handling if imports fail
    print("Warning: Could not import formatting functions, will import when needed")

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
    print(f"Attempting to retrieve content for report ID: {report_id}")
    report_content = None
    
    # Check if report exists in Supabase
    supabase = create_supabase_client()
    response = supabase.table("reports").select("content").eq("report_id", str(report_id)).execute()
    
    if response.data and response.data[0].get("content"):
        return response.data[0]["content"]
    
    # Check local storage as fallback
    report_dir = os.path.join(settings.UPLOAD_DIR, str(report_id))
    if os.path.exists(report_dir) and os.path.isdir(report_dir):
        # Look for content.txt or similar files
        content_files = glob.glob(os.path.join(report_dir, "content*.txt"))
        if content_files:
            with open(content_files[0], 'r', encoding='utf-8') as f:
                return f.read()
    
    return None


def fetch_report_path_from_supabase(report_id: UUID4) -> Optional[str]:
    """
    Get the report file path from Supabase
    """
    try:
        supabase = create_supabase_client()
        response = supabase.table("reports").select("file_path").eq("report_id", str(report_id)).execute()
        
        if response.data and response.data[0].get("file_path"):
            return response.data[0]["file_path"]
        return None
    except Exception as e:
        print(f"Error fetching report path: {str(e)}")
        return None


def find_report_file_locally(report_id: UUID4) -> Optional[str]:
    """
    Find a report file in the local filesystem
    """
    report_dir = os.path.join(settings.UPLOAD_DIR, str(report_id))
    if not os.path.exists(report_dir):
        return None
        
    # Look for report files
    patterns = [
        f"report_{report_id}*.docx",
        f"*{report_id}*.docx"
    ]
    
    for pattern in patterns:
        matching_files = glob.glob(os.path.join(settings.GENERATED_REPORTS_DIR, pattern))
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
        matching_files = glob.glob(os.path.join(settings.GENERATED_REPORTS_DIR, pattern))
        if matching_files:
            return matching_files[0]
    
    # Then check in the upload directory
    report_dir = os.path.join(settings.UPLOAD_DIR, str(report_id))
    if os.path.exists(report_dir):
        docx_files = glob.glob(os.path.join(report_dir, "*.docx"))
        if docx_files:
            return docx_files[0]
    
    return None


@router.get("/{report_id}")
async def download_report(
    report_id: UUID4, 
    format: str = Query("docx", description="Format of the report, either 'docx' or 'pdf'"),
    user: Optional[Dict[str, Any]] = Depends(get_current_user)
):
    """
    Download a generated report in DOCX or PDF format
    """
    try:
        # Validate format
        if format.lower() not in ["docx", "pdf"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported format: {format}. Only 'docx' and 'pdf' are supported."
            )
        
        # Initialize Supabase client
        supabase = create_supabase_client()
        
        # Find the report in Supabase
        response = supabase.table("reports").select("*").eq("report_id", str(report_id)).execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Report not found with ID: {report_id}"
            )
        
        report = response.data[0]
        
        # Determine which format to return
        if format.lower() == "docx":
            return await download_docx_report(report_id)
        else:  # PDF
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="PDF download not implemented yet"
            )
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Log and return a generic error
        print(f"Error downloading report: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error downloading report: {str(e)}"
        )


@router.get("/file/{report_id}")
async def serve_report_file(report_id: UUID4):
    """
    Serve a report file directly (without downloading)
    """
    try:
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error serving report file: {str(e)}")


@router.post("/cleanup/{report_id}")
async def cleanup_report_files(report_id: UUID4):
    """
    Clean up all temporary files associated with a report after it has been successfully
    downloaded. This ensures that uploaded files don't persist in storage.
    
    Args:
        report_id: The UUID of the report to clean up files for
        
    Returns:
        A status message indicating success or failure
    """
    # Define paths for report files
    report_dir = os.path.join(settings.UPLOAD_DIR, str(report_id))
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
                matching_files = glob.glob(os.path.join(settings.GENERATED_REPORTS_DIR, pattern))
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
                file_path = os.path.join(report_dir, filename)
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
        
        return {
            "status": "success",
            "message": f"Successfully cleaned up {len(deleted_files)} files for report {report_id}"
        }
    except Exception as e:
        print(f"Error cleaning up report files: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to clean up report files: {str(e)}"
        }


@router.get("/docx/{report_id}")
async def download_docx_report(report_id: UUID4):
    """
    Download a finalized report as DOCX by ID.
    
    Args:
        report_id: UUID of the report to download
        
    Returns:
        The DOCX file as a download
    """
    try:
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
            docx_path = os.path.join(settings.GENERATED_REPORTS_DIR, f"{base_name}.docx")
            
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error downloading report: {str(e)}")


@router.get("/file/docx/{report_id}")
async def serve_docx_report_file(report_id: UUID4):
    """
    Serve a DOCX report file directly (without downloading)
    """
    try:
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error serving DOCX file: {str(e)}")
