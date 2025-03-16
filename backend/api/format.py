from fastapi import APIRouter, HTTPException, Body
from fastapi.responses import FileResponse
from typing import Dict, List
import os
import requests
from config import settings
from services.pdf_formatter import format_report_as_pdf
from services.pdf_extractor import extract_pdf_metadata, extract_text_from_file
import uuid
import glob
from supabase import create_client, Client

router = APIRouter()


def fetch_report_from_supabase(report_id: str):
    """
    Fetch the report content from Supabase using the report_id.
    """
    try:
        # Initialize Supabase client
        supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        
        # Query the reports table
        response = supabase.table("reports").select("content").eq("id", report_id).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Report not found in the database")
            
        return response.data[0]["content"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching report: {str(e)}")


def update_report_file_path(report_id: str, pdf_path: str):
    """
    Updates the finalized report's file path in Supabase.
    """
    try:
        # Initialize Supabase client
        supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        
        # Update the report with the file path
        data = {"formatted_file_path": pdf_path, "is_finalized": True}
        response = supabase.table("reports").update(data).eq("id", report_id).execute()
        
        if not response.data:
            raise HTTPException(status_code=500, detail="Failed to update report in database.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating report: {str(e)}")


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

    try:
        # Fetch the actual report content from Supabase
        report_content = fetch_report_from_supabase(report_id)
        
        # Create the generated_reports directory if it doesn't exist
        os.makedirs("generated_reports", exist_ok=True)

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
