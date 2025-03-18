from fastapi import APIRouter, HTTPException, Body
from fastapi.responses import FileResponse
from typing import Dict, List
import os
import requests
from config import settings
from services.pdf_formatter import format_report_as_pdf
from services.pdf_extractor import extract_pdf_metadata, extract_text_from_file
from services.docx_formatter import format_report_as_docx
import uuid
import glob
from supabase import create_client, Client
from utils.id_mapper import ensure_id_is_int
import json
import datetime

router = APIRouter()


def fetch_report_from_supabase(report_id):
    """
    Fetch the report content from Supabase using the report_id.
    
    Args:
        report_id: Can be an integer ID or UUID string
    """
    try:
        # Initialize Supabase client
        supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        
        # Convert to integer using the utility function
        try:
            db_id = ensure_id_is_int(report_id)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid report ID format: {str(e)}")
                
        # Query the reports table
        response = supabase.table("reports").select("content").eq("id", db_id).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail=f"Report not found in the database with ID: {report_id}")
            
        return response.data[0]["content"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching report: {str(e)}")


def update_report_file_path(report_id, pdf_path: str):
    """
    Updates the finalized report's file path in Supabase.
    
    Args:
        report_id: Can be an integer ID or UUID string
        pdf_path: Path to the generated PDF file
    """
    try:
        # Initialize Supabase client
        supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        
        # Convert to integer using the utility function
        try:
            db_id = ensure_id_is_int(report_id)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid report ID format: {str(e)}")
        
        # Update the report with the file path
        try:
            # Update both fields to ensure compatibility
            data = {
                "formatted_file_path": pdf_path, 
                "file_path": pdf_path,
                "is_finalized": True
            }
            
            # Try to find the report by ID first
            response = supabase.table("reports").update(data).eq("id", db_id).execute()
            
            if not response.data:
                # If not found by ID, try UUID
                if isinstance(report_id, str) and "-" in report_id:
                    print(f"Report not found by ID {db_id}, trying UUID {report_id}")
                    response = supabase.table("reports").update(data).eq("uuid", report_id).execute()
            
            if not response.data:
                print(f"Warning: No report found with ID {db_id} or UUID {report_id} when updating file path")
        except Exception as db_error:
            # Handle database errors
            print(f"Database error updating report file path: {str(db_error)}")
            print("This is likely due to missing columns in the database.")
            
            # Save locally as fallback
            report_dir = os.path.join(settings.UPLOAD_DIR, str(report_id))
            metadata_path = os.path.join(report_dir, "metadata.json")
            
            if os.path.exists(report_dir) and os.path.isdir(report_dir):
                # Save locally in metadata.json
                try:
                    metadata = {}
                    if os.path.exists(metadata_path):
                        with open(metadata_path, "r") as f:
                            metadata = json.load(f)
                    
                    metadata["pdf_path"] = pdf_path
                    metadata["is_finalized"] = True
                    
                    with open(metadata_path, "w") as f:
                        json.dump(metadata, f)
                        
                    print(f"Saved file path to local metadata file: {metadata_path}")
                except Exception as file_error:
                    print(f"Error saving metadata file: {str(file_error)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating report file path: {str(e)}")


@router.post("/preview", response_model=dict)
async def format_preview(
    report_content: dict = Body(..., description="Content to format")
):
    """
    Generate a preview of the formatted report.
    
    Args:
        report_content: Content to format
        
    Returns:
        URL to the preview PDF
    """
    try:
        # Generate unique filename for the preview
        preview_id = str(uuid.uuid4())
        output_filename = f"preview_{preview_id}.pdf"
        
        # Create reference metadata for preview
        reference_metadata = {
            "headers": ["INSURANCE REPORT", "PREVIEW VERSION"],
            "footers": ["Page {page}"]
        }
        
        # Call PDF formatting service
        pdf_path = await format_report_as_pdf(
            report_content.get("content", ""),
            reference_metadata,
            is_preview=True,
            filename=output_filename
        )
        
        # In a production app, this would upload to Supabase Storage
        # and return a public URL
        return {
            "preview_id": preview_id,
            "preview_url": f"/api/format/preview/{preview_id}",
            "pdf_path": pdf_path
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate preview: {str(e)}"
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
        os.path.join("backend", "reference_reports")
    ]
    
    pdf_files = []
    
    # Look for PDF files in all search paths
    for path in search_paths:
        if os.path.exists(path) and os.path.isdir(path):
            # Find all PDF files in the directory
            pattern = os.path.join(path, "*.pdf")
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


@router.post("/final", status_code=200)
async def format_final(data: Dict = Body(...)):
    """
    Generate the final formatted report PDF and save the file path to Supabase.
    """
    if "report_id" not in data:
        raise HTTPException(status_code=400, detail="report_id is required")

    report_id = data["report_id"]
    
    # First, check if this is a UUID or report directory
    is_uuid = False
    if isinstance(report_id, str) and "-" in report_id:
        # Check if this is a directory in the uploads folder
        report_dir = os.path.join(settings.UPLOAD_DIR, report_id)
        if os.path.exists(report_dir) and os.path.isdir(report_dir):
            is_uuid = True
    
    print(f"Processing report_id: {report_id} (is_uuid: {is_uuid})")
    
    # Try to convert the ID if needed
    try:
        db_id = ensure_id_is_int(report_id)
    except ValueError as e:
        # If this is a UUID but conversion failed, try to work with it directly
        if is_uuid:
            print(f"Working with UUID report_id directly: {report_id}")
            try:
                # Use a hash of the UUID as an integer ID for filename purposes
                import hashlib
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
            metadata_path = os.path.join(report_dir, "metadata.json")
            
            if os.path.exists(metadata_path):
                try:
                    with open(metadata_path, "r") as f:
                        metadata = json.load(f)
                        if "report_content" in metadata:
                            report_content = metadata["report_content"]
                            print(f"Using report content from metadata.json for UUID {report_id}")
                except Exception as e:
                    print(f"Error reading metadata for UUID {report_id}: {str(e)}")
        
        # If we didn't get content from files, try Supabase
        if not report_content:
            try:
                report_content = fetch_report_from_supabase(report_id)
            except HTTPException as e:
                if is_uuid:
                    # For UUID reports, if Supabase fetch fails, check for a content.txt file
                    content_path = os.path.join(report_dir, "content.txt")
                    if os.path.exists(content_path):
                        try:
                            with open(content_path, "r") as f:
                                report_content = f.read()
                            print(f"Using content from content.txt for UUID {report_id}")
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

        # Generate final formatted PDF
        pdf_filename = f"report_{db_id}.pdf"
        pdf_path = await format_report_as_pdf(
            report_content,
            reference_metadata,
            is_preview=False,
            filename=pdf_filename
        )
        
        # Ensure the path is absolute
        absolute_pdf_path = os.path.abspath(pdf_path)
        
        print(f"PDF generated at: {absolute_pdf_path}")

        # For UUID reports, save the path in metadata.json too
        if is_uuid:
            try:
                metadata_path = os.path.join(report_dir, "metadata.json")
                metadata = {}
                
                if os.path.exists(metadata_path):
                    try:
                        with open(metadata_path, "r") as f:
                            metadata = json.load(f)
                    except:
                        pass
                
                metadata["pdf_path"] = absolute_pdf_path
                metadata["is_finalized"] = True
                
                with open(metadata_path, "w") as f:
                    json.dump(metadata, f)
                    
                # Also save content.txt if we have content
                if report_content and "report_content" not in metadata:
                    content_path = os.path.join(report_dir, "content.txt")
                    with open(content_path, "w") as f:
                        f.write(report_content)
                        
            except Exception as e:
                print(f"Error updating metadata for UUID {report_id}: {str(e)}")

        # Try to update the database with the file path
        try:
            update_report_file_path(report_id, absolute_pdf_path)
        except Exception as e:
            # For UUID reports, we already saved the path in metadata.json
            # so log but don't fail if database update fails
            if not is_uuid:
                raise e
            print(f"Warning: Could not update database for UUID {report_id}: {str(e)}")
        
        # Verify the file exists
        if not os.path.exists(absolute_pdf_path):
            raise HTTPException(
                status_code=404, detail=f"Generated PDF not found at {absolute_pdf_path}"
            )

        return {
            "success": True,
            "report_id": report_id,
            "file_path": absolute_pdf_path,
            "formatted_file_path": absolute_pdf_path,
            "download_url": f"/api/download/{report_id}"
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500, detail=f"Error formatting final report: {str(e)}"
        )


@router.post("/docx", status_code=200)
async def format_docx(data: Dict = Body(...)):
    """
    Formats the report as a DOCX file and updates Supabase with the file path.
    
    Args:
        data: Dictionary containing report_id or report_content
        
    Returns:
        Dictionary with the path to the generated DOCX and status
    """
    try:
        report_id = data.get("report_id")
        report_content = data.get("report_content")
        
        # If report_id is provided, fetch content from Supabase
        if report_id and not report_content:
            # Use the ID mapper utility to handle UUID/integer conversion
            try:
                db_id = ensure_id_is_int(report_id)
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
            "status": "success",
            "message": "Report formatted as DOCX successfully",
            "docx_path": result["docx_path"],
            "filename": result["filename"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error formatting DOCX: {str(e)}")


@router.post("/preview-file", response_model=dict)
async def preview_file(data: Dict = Body(...)):
    """
    Generate a preview of the report PDF from a report ID.
    
    Args:
        data: Contains report_id to preview
        
    Returns:
        URL to the preview PDF
    """
    if "report_id" not in data:
        raise HTTPException(status_code=400, detail="report_id is required")
        
    report_id = data["report_id"]
    
    try:
        # Use the ID mapper utility to handle UUID/integer conversion
        try:
            db_id = ensure_id_is_int(report_id)
        except ValueError as e:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid report_id format: {str(e)}"
            )
        
        # Fetch the report content from Supabase
        report_content = fetch_report_from_supabase(report_id)
        
        # Generate unique filename for the preview
        preview_id = str(uuid.uuid4())
        output_filename = f"preview_{preview_id}.pdf"
        
        # Create reference metadata for preview
        reference_metadata = {
            "headers": ["INSURANCE REPORT - PREVIEW", f"Report #{db_id}"],
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
        preview_dir = os.path.join(settings.GENERATED_REPORTS_DIR, "previews")
        os.makedirs(preview_dir, exist_ok=True)
        
        # Create a static endpoint to access this file
        file_name = os.path.basename(pdf_path)
        preview_url = f"/api/format/preview-file/{preview_id}"
        
        return {
            "preview_id": preview_id,
            "preview_url": preview_url,
            "pdf_path": pdf_path
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate preview: {str(e)}"
        )


@router.get("/preview-file/{preview_id}")
async def get_preview_file(preview_id: str):
    """
    Get a generated preview file by its ID
    
    Args:
        preview_id: UUID of the preview to retrieve
        
    Returns:
        PDF file
    """
    try:
        # Look for the preview file
        preview_filename = f"preview_{preview_id}.pdf"
        
        # Check in multiple possible locations
        possible_paths = [
            os.path.join(settings.GENERATED_REPORTS_DIR, "previews", preview_filename),
            os.path.join(settings.GENERATED_REPORTS_DIR, preview_filename),
            os.path.join("generated_reports", preview_filename),
            os.path.join("generated_reports", "previews", preview_filename)
        ]
        
        # Find the first path that exists
        file_path = None
        for path in possible_paths:
            if os.path.exists(path):
                file_path = path
                break
                
        if not file_path:
            raise HTTPException(status_code=404, detail=f"Preview file not found: {preview_id}")
            
        return FileResponse(file_path, media_type="application/pdf")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving preview file: {str(e)}")
