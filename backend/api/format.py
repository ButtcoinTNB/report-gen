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
        data = {"formatted_file_path": pdf_path, "is_finalized": True}
        response = supabase.table("reports").update(data).eq("id", db_id).execute()
        
        if not response.data:
            raise HTTPException(status_code=500, detail=f"Failed to update report in database with ID: {report_id}")
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
    
    # Use the ID mapper utility to handle UUID/integer conversion
    try:
        db_id = ensure_id_is_int(report_id)
    except ValueError as e:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid report_id format: {str(e)}"
        )

    try:
        # Fetch the actual report content from Supabase
        report_content = fetch_report_from_supabase(report_id)
        
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

        # Update the database with the file path
        update_report_file_path(report_id, absolute_pdf_path)
        
        # Verify the file exists
        if not os.path.exists(absolute_pdf_path):
            raise HTTPException(
                status_code=404, detail=f"Generated PDF not found at {absolute_pdf_path}"
            )

        return {
            "success": True,
            "report_id": report_id,
            "file_path": absolute_pdf_path,
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
