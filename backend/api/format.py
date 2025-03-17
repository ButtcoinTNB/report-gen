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
        
        # Convert to integer if it's a numeric string
        if isinstance(report_id, str) and report_id.isdigit():
            try:
                report_id = int(report_id)
            except ValueError:
                # Keep as string if conversion fails
                pass
                
        # Query the reports table
        response = supabase.table("reports").select("content").eq("id", report_id).execute()
        
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
        
        # Convert to integer if it's a numeric string
        if isinstance(report_id, str) and report_id.isdigit():
            try:
                report_id = int(report_id)
            except ValueError:
                # Keep as string if conversion fails
                pass
        
        # Update the report with the file path
        data = {"formatted_file_path": pdf_path, "is_finalized": True}
        response = supabase.table("reports").update(data).eq("id", report_id).execute()
        
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
    
    # Check if report_id is a UUID string and handle appropriately
    # This is needed because the frontend may send UUID strings but the database expects integers
    try:
        # If it's a UUID, try to find the corresponding numeric ID or handle UUID directly
        if isinstance(report_id, str) and '-' in report_id:
            # If your database now uses UUIDs as primary keys, keep as is
            # If your database uses integers but API returns UUIDs, you might need
            # to query the database to find the integer ID associated with this UUID
            # For now we'll proceed with the UUID as is
            pass
        else:
            # If it's already an integer or integer string without dashes
            try:
                report_id = int(report_id)
            except ValueError:
                pass  # Keep as string if conversion fails
    except Exception as e:
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
        if f"Report #{report_id}" not in reference_metadata["headers"]:
            reference_metadata["headers"].append(f"Report #{report_id}")

        # Generate final formatted PDF
        pdf_filename = f"report_{report_id}.pdf"
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
