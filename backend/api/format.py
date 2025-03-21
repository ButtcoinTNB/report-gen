from fastapi import APIRouter, HTTPException, Body
from fastapi.responses import FileResponse
from typing import Dict, List, Optional
import os
import requests
from uuid import UUID
from pydantic import UUID4, BaseModel
from config import settings
from backend.services.pdf_formatter import format_report_as_pdf
from backend.services.pdf_extractor import extract_pdf_metadata, extract_text_from_file
from backend.services.docx_formatter import format_report_as_docx
import uuid
import glob
from supabase import create_client, Client
from backend.utils.supabase_helper import create_supabase_client
import json
import datetime
import hashlib
from backend.utils.file_utils import safe_path_join
from backend.api.schemas import APIResponse
from backend.utils.error_handler import api_error_handler

# Export key functions for other modules
__all__ = ['format_report_as_pdf', 'get_reference_metadata', 'update_report_file_path', 'format_final']

router = APIRouter()


def fetch_report_from_supabase(report_id: UUID4) -> str:
    """
    Fetch the report content from Supabase using the report_id.
    
    Args:
        report_id: The UUID of the report
        
    Returns:
        The report content as a string
        
    Raises:
        HTTPException: If the report is not found or there's an error
    """
    try:
        # Initialize Supabase client
        supabase = create_supabase_client()
        
        # Query the reports table using report_id directly
        response = supabase.table("reports").select("content").eq("report_id", str(report_id)).execute()
        
        if not response.data:
            raise HTTPException(
                status_code=404, 
                detail=f"Report not found with report_id: {report_id}"
            )
            
        return response.data[0]["content"]
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error fetching report: {str(e)}"
        )


def update_report_file_path(report_id: UUID4, file_path: str):
    """
    Updates the finalized report's file path in Supabase.
    
    Args:
        report_id: The UUID of the report
        file_path: Path to the generated report file (DOCX)
    """
    try:
        # Initialize Supabase client
        supabase = create_supabase_client()
        
        # Update the report with the file path
        data = {
            "file_path": file_path,
            "is_finalized": True
        }
        
        response = supabase.table("reports").update(data).eq("report_id", str(report_id)).execute()
        
        if not response.data:
            print(f"Warning: No report found with report_id {report_id} when updating file path")
            
    except Exception as e:
        # Handle database errors
        print(f"Database error updating report file path: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error updating report file path: {str(e)}"
        )


# Define a response model for format preview
class FormatPreviewResponse(BaseModel):
    """Response model for format preview endpoint"""
    html: str
    metadata: Optional[Dict] = None

@router.post("/preview", response_model=APIResponse[FormatPreviewResponse])
async def format_preview(
    report_content: dict = Body(..., description="Content to format")
):
    """
    Generate an HTML preview of formatted content.
    
    Args:
        report_content: Dictionary containing markdown content to format
        
    Returns:
        Standardized API response with HTML preview
    """
    try:
        # Extract the content
        content = report_content.get("content", "")
        
        if not content:
            return APIResponse(
                status="error",
                message="No content provided in request",
                code="MISSING_CONTENT"
            )
        
        # Get reference report metadata to use for formatting
        reference_metadata = get_reference_metadata()
        
        # Format the content as PDF to get the HTML
        pdf_result = format_report_as_pdf(
            content, 
            output_path=None,  # No file output for preview
            reference_metadata=reference_metadata,
            return_html=True
        )
        
        if not pdf_result or "html" not in pdf_result:
            return APIResponse(
                status="error",
                message="Failed to generate HTML preview",
                code="PREVIEW_GENERATION_FAILED"
            )
        
        # Return the HTML for the frontend to display
        return APIResponse(
            status="success",
            data=FormatPreviewResponse(
                html=pdf_result["html"],
                metadata=reference_metadata
            ),
            message="Preview generated successfully"
        )
        
    except Exception as e:
        return APIResponse(
            status="error",
            message=f"Error generating preview: {str(e)}",
            code="PREVIEW_ERROR"
        )


def get_reference_metadata():
    """
    Get metadata from all reference PDFs in the reference_reports directory.
    Combines headers and footers from all reference PDFs.
    
    Returns:
        Dictionary with headers and footers
    """
    reference_metadata = {
        "headers": [],
        "footers": []
    }
    
    # List of directories to check for reference PDFs
    search_paths = [
        "reference_reports",
        safe_path_join("backend", "reference_reports")
    ]
    
    pdf_files = []
    
    # Look for PDF files in all search paths
    for path in search_paths:
        if os.path.exists(path) and os.path.isdir(path):
            # Find all PDF files in the directory
            pattern = safe_path_join(path, "*.pdf")
            pdf_files.extend(glob.glob(pattern))
    
    if not pdf_files:
        print("Warning: No reference PDFs found. Using default metadata.")
        return {
            "headers": ["INSURANCE CLAIM REPORT"],
            "footers": ["Confidential", "Page {page}"]
        }
    
    print(f"Found {len(pdf_files)} reference PDFs: {pdf_files}")
    
    # Extract metadata from each PDF and combine
    for pdf_file in pdf_files:
        try:
            file_metadata = extract_pdf_metadata(pdf_file)
            
            # Extract text to analyze the document structure
            pdf_text = extract_text_from_file(pdf_file)
            
            # Add metadata from this file
            if "headers" in file_metadata and file_metadata["headers"]:
                for header in file_metadata["headers"]:
                    if header not in reference_metadata["headers"]:
                        reference_metadata["headers"].append(header)
            
            if "footers" in file_metadata and file_metadata["footers"]:
                for footer in file_metadata["footers"]:
                    if footer not in reference_metadata["footers"]:
                        reference_metadata["footers"].append(footer)
                        
        except Exception as e:
            print(f"Error extracting metadata from {pdf_file}: {str(e)}")
    
    # If no headers or footers were found, use defaults
    if not reference_metadata["headers"]:
        reference_metadata["headers"] = ["INSURANCE CLAIM REPORT"]
    
    if not reference_metadata["footers"]:
        reference_metadata["footers"] = ["Confidential", "Page {page}"]
    
    return reference_metadata


# Helper function to replace ensure_id_is_int
def _get_numeric_id(report_id):
    """
    Generate a numeric ID from a report_id (which might be a UUID or string)
    """
    if isinstance(report_id, int):
        return report_id
    
    # For string or UUID, use a hash to generate a numeric ID
    try:
        # Try to convert to UUID if it's a string that looks like a UUID
        if isinstance(report_id, str) and '-' in report_id:
            try:
                uuid_obj = UUID(report_id)
                # Use the int representation modulo a 32-bit int max value
                return uuid_obj.int % 2147483647
            except ValueError:
                pass
        
        # If it's a string that can be converted to int, do so
        if isinstance(report_id, str):
            try:
                return int(report_id)
            except ValueError:
                pass
        
        # Otherwise use a hash
        hash_input = str(report_id).encode('utf-8')
        return int(hashlib.md5(hash_input).hexdigest(), 16) % (10**8)
    except Exception:
        # Fallback
        return 999999


class FormatFinalResponse(BaseModel):
    """Response model for final formatting endpoint"""
    report_id: str
    file_path: str
    formatted_file_path: str
    download_url: str

@router.post("/final", status_code=200, response_model=APIResponse[FormatFinalResponse])
@api_error_handler
async def format_final(data: Dict = Body(...)):
    """
    Generate the final formatted report DOCX and save the file path to Supabase.
    
    Returns:
        Standardized API response with file paths and download URL
    """
    if "report_id" not in data:
        raise HTTPException(status_code=400, detail="report_id is required")

    report_id = data["report_id"]
    
    # First, check if this is a UUID or report directory
    is_uuid = False
    if isinstance(report_id, str) and "-" in report_id:
        # Check if this is a directory in the uploads folder
        report_dir = safe_path_join(settings.UPLOAD_DIR, report_id)
        if os.path.exists(report_dir) and os.path.isdir(report_dir):
            is_uuid = True
    
    logger.info(f"Processing report_id: {report_id} (is_uuid: {is_uuid})")
    
    # Try to convert the ID if needed
    try:
        db_id = _get_numeric_id(report_id)
    except ValueError as e:
        # If this is a UUID but conversion failed, try to work with it directly
        if is_uuid:
            print(f"Working with report_id directly: {report_id}")
            try:
                # Use a hash of the report_id as an integer ID for filename purposes
                db_id = int(hashlib.md5(report_id.encode()).hexdigest(), 16) % 10000000
            except Exception:
                # Last resort fallback
                db_id = 999999
        else:
            # If not UUID format or no directory found, raise the original error
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid report_id format: {str(e)}"
            )

    try:
        # For UUID-based reports, try to get content from files instead of Supabase
        report_content = None
        if is_uuid:
            # Try to find any generated report file in the directory
            report_files = []
            metadata_path = safe_path_join(report_dir, "metadata.json")
            
            if os.path.exists(metadata_path):
                try:
                    with open(metadata_path, "r") as f:
                        metadata = json.load(f)
                        if "report_content" in metadata:
                            report_content = metadata["report_content"]
                            print(f"Using report content from metadata.json for report_id {report_id}")
                except Exception as e:
                    print(f"Error reading metadata for report_id {report_id}: {str(e)}")
        
        # If we didn't get content from files, try Supabase
        if not report_content:
            try:
                report_content = fetch_report_from_supabase(report_id)
            except HTTPException as e:
                if is_uuid:
                    # For UUID reports, if Supabase fetch fails, check for a content.txt file
                    content_path = safe_path_join(report_dir, "content.txt")
                    if os.path.exists(content_path):
                        try:
                            with open(content_path, "r") as f:
                                report_content = f.read()
                            print(f"Using content from content.txt for report_id {report_id}")
                        except Exception as read_err:
                            print(f"Error reading content.txt: {str(read_err)}")
                    
                    if not report_content:
                        # Create a more detailed and well-formatted error report
                        report_content = f"""# ERROR: COULD NOT RETRIEVE REPORT CONTENT

## Report Details
- Report ID: {report_id}
- Generated: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Error Information
The system was unable to retrieve the content for this report.

## What You Can Do
1. Try regenerating the report from the original documents
2. Contact support if this problem persists
3. Verify that your report was saved correctly

## Technical Information
This error occurs when the system cannot locate the report content in the database or in local storage."""
                else:
                    # For non-UUID reports, propagate the original error
                    raise e
        
        # Create the generated_reports directory if it doesn't exist
        os.makedirs(settings.GENERATED_REPORTS_DIR, exist_ok=True)

        # Get metadata from all reference PDFs
        reference_metadata = get_reference_metadata()
        
        # Add report-specific header
        if f"Report #{db_id}" not in reference_metadata["headers"]:
            reference_metadata["headers"].append(f"Report #{db_id}")

        # Generate final formatted DOCX
        docx_filename = f"report_{db_id}.docx"
        result = await format_report_as_docx(
            report_content,
            reference_metadata,
            filename=docx_filename
        )
        docx_path = result["docx_path"]
        
        # Ensure the path is absolute
        absolute_docx_path = os.path.abspath(docx_path)
        
        print(f"DOCX generated at: {absolute_docx_path}")

        # For UUID reports, save the path in metadata.json too
        if is_uuid:
            try:
                metadata_path = safe_path_join(report_dir, "metadata.json")
                metadata = {}
                
                if os.path.exists(metadata_path):
                    try:
                        with open(metadata_path, "r") as f:
                            metadata = json.load(f)
                    except Exception as read_err:
                        print(f"Error reading metadata file: {str(read_err)}")
                        # Initialize with empty dict if reading fails
                        metadata = {}
                
                # Always save both the path and content in metadata
                metadata["docx_path"] = absolute_docx_path
                metadata["is_finalized"] = True
                metadata["report_content"] = report_content  # Save the content directly in metadata
                metadata["last_updated"] = datetime.datetime.now().isoformat()
                
                with open(metadata_path, "w") as f:
                    json.dump(metadata, f)
                print(f"Saved report metadata with content to: {metadata_path}")
                    
                # Always save content.txt regardless of metadata status
                content_path = safe_path_join(report_dir, "content.txt")
                with open(content_path, "w") as f:
                    f.write(report_content)
                print(f"Saved report content to: {content_path}")
                        
            except Exception as e:
                print(f"Error updating metadata for report_id {report_id}: {str(e)}")

        # Try to update the database with the file path
        try:
            update_report_file_path(report_id, absolute_docx_path)
        except Exception as e:
            # For UUID reports, we already saved the path in metadata.json
            # so log but don't fail if database update fails
            if not is_uuid:
                raise e
            print(f"Warning: Could not update database for report_id {report_id}: {str(e)}")
        
        # Verify the file exists
        if not os.path.exists(absolute_docx_path):
            raise HTTPException(
                status_code=404, detail=f"Generated DOCX not found at {absolute_docx_path}"
            )

        return {
            "report_id": report_id,
            "file_path": absolute_docx_path,
            "formatted_file_path": absolute_docx_path,
            "download_url": f"/api/download/docx/{report_id}"
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500, detail=f"Error formatting final report: {str(e)}"
        )


class FormatDocxResponse(BaseModel):
    """Response model for docx formatting endpoint"""
    docx_path: str
    filename: str

@router.post("/docx", status_code=200, response_model=APIResponse[FormatDocxResponse])
@api_error_handler
async def format_docx(data: Dict = Body(...)):
    """
    Formats the report as a DOCX file and updates Supabase with the file path.
    
    Args:
        data: Dictionary containing report_id or report_content
        
    Returns:
        Standardized API response with the path to the generated DOCX
    """
    report_id = data.get("report_id")
    report_content = data.get("report_content")
    
    # If report_id is provided, fetch content from Supabase
    if report_id and not report_content:
        # Generate a numeric ID from the report_id
        try:
            db_id = _get_numeric_id(report_id)
        except ValueError as e:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid report_id format: {str(e)}"
            )
        report_content = fetch_report_from_supabase(report_id)
    
    if not report_content:
        raise HTTPException(status_code=400, detail="Report content is required")
    
    # Get metadata from reference reports for formatting
    reference_metadata = get_reference_metadata()
    
    # Generate a unique filename
    filename = f"report_{uuid.uuid4().hex}.docx"
    
    # Format the report as DOCX
    result = await format_report_as_docx(report_content, reference_metadata, filename)
    
    # If report_id is provided, update the file path in Supabase
    if report_id:
        update_report_file_path(report_id, result["docx_path"])
    
    return {
        "docx_path": result["docx_path"],
        "filename": result["filename"]
    }


class PreviewFileGenerationResponse(BaseModel):
    """Response model for preview file generation endpoint"""
    preview_id: str
    preview_url: str
    pdf_path: str

@router.post("/preview-file", response_model=APIResponse[PreviewFileGenerationResponse])
@api_error_handler
async def preview_file(data: Dict = Body(...)):
    """
    Generate a preview of the report PDF from a report ID.
    
    Args:
        data: Contains report_id (UUID) to preview
        
    Returns:
        Standardized API response with preview details and URL
    """
    if "report_id" not in data:
        raise HTTPException(status_code=400, detail="report_id is required")
        
    report_id = data["report_id"]
    
    # Fetch the report content from Supabase using report_id
    report_content = fetch_report_from_supabase(report_id)
    
    # Generate unique filename for the preview
    preview_id = str(uuid.uuid4())
    output_filename = f"preview_{preview_id}.pdf"
    
    # Create reference metadata for preview
    reference_metadata = {
        "headers": ["INSURANCE REPORT - PREVIEW", f"Report #{report_id[:8]}"],
        "footers": ["Preview Only - Not for Distribution", "Page {page}"]
    }
    
    # Call PDF formatting service
    pdf_path = await format_report_as_pdf(
        report_content,
        reference_metadata,
        is_preview=True,
        filename=output_filename
    )
    
    # Create preview directory if it doesn't exist
    preview_dir = safe_path_join(settings.GENERATED_REPORTS_DIR, "previews")
    os.makedirs(preview_dir, exist_ok=True)
    
    # Create a static endpoint to access this file
    file_name = os.path.basename(pdf_path)
    preview_url = f"/api/format/preview-file/{preview_id}"
    
    return {
        "preview_id": preview_id,
        "preview_url": preview_url,
        "pdf_path": pdf_path
    }


class PreviewFileResponse(BaseModel):
    """Response model for preview file getting endpoint"""
    file_path: str
    preview_id: str

@router.get("/preview-file/{preview_id}", response_model=APIResponse[PreviewFileResponse])
@api_error_handler
async def get_preview_file(preview_id: str):
    """
    Get a generated preview file by its ID
    
    Args:
        preview_id: UUID of the preview to retrieve
        
    Returns:
        Standardized API response with FileResponse for the PDF
    """
    # Look for the preview file
    preview_filename = f"preview_{preview_id}.pdf"
    
    # Check in multiple possible locations
    possible_paths = [
        safe_path_join(settings.GENERATED_REPORTS_DIR, "previews", preview_filename),
        safe_path_join(settings.GENERATED_REPORTS_DIR, preview_filename),
        safe_path_join("generated_reports", preview_filename),
        safe_path_join("generated_reports", "previews", preview_filename)
    ]
    
    # Find the first path that exists
    file_path = None
    for path in possible_paths:
        if os.path.exists(path):
            file_path = path
            break
            
    if not file_path:
        raise HTTPException(status_code=404, detail=f"Preview file not found: {preview_id}")
    
    # Return a FileResponse directly since we can't wrap it in an APIResponse
    return FileResponse(file_path, media_type="application/pdf")


# Create an endpoint to get preview file info without downloading it
@router.get("/preview-file/{preview_id}/info", response_model=APIResponse[PreviewFileResponse])
@api_error_handler
async def get_preview_file_info(preview_id: str):
    """
    Get information about a preview file without downloading it
    
    Args:
        preview_id: UUID of the preview to get info about
        
    Returns:
        Standardized API response with preview file information
    """
    # Look for the preview file
    preview_filename = f"preview_{preview_id}.pdf"
    
    # Check in multiple possible locations
    possible_paths = [
        safe_path_join(settings.GENERATED_REPORTS_DIR, "previews", preview_filename),
        safe_path_join(settings.GENERATED_REPORTS_DIR, preview_filename),
        safe_path_join("generated_reports", preview_filename),
        safe_path_join("generated_reports", "previews", preview_filename)
    ]
    
    # Find the first path that exists
    file_path = None
    for path in possible_paths:
        if os.path.exists(path):
            file_path = path
            break
            
    if not file_path:
        raise HTTPException(status_code=404, detail=f"Preview file not found: {preview_id}")
        
    return {
        "file_path": file_path,
        "preview_id": preview_id
    }
