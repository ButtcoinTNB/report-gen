from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
import os
import glob
import json
from supabase import create_client, Client
from config import settings
from utils.id_mapper import ensure_id_is_int
import traceback

router = APIRouter()


def fetch_report_path_from_supabase(report_id: str):
    """
    Retrieves the finalized report file path from Supabase.
    
    Args:
        report_id: Can be either a UUID string or an integer ID
    """
    try:
        # Try to convert the report_id to an integer if it's a UUID
        try:
            db_id = ensure_id_is_int(report_id)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid report ID format: {str(e)}")
            
        # Initialize Supabase client
        supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        
        try:
            # Query the reports table using the integer ID
            response = supabase.table("reports").select("formatted_file_path,is_finalized").eq("id", db_id).execute()
        except Exception as e:
            # If the formatted_file_path column doesn't exist yet, try to find the file locally
            print(f"Database error (likely missing formatted_file_path column): {str(e)}")
            local_path = find_report_file_locally(report_id)
            if local_path:
                return local_path
            raise HTTPException(status_code=500, detail="Database schema not fully initialized")
        
        if not response.data:
            raise HTTPException(status_code=404, detail=f"Report with ID {report_id} not found in the database.")
            
        report_data = response.data[0]
        if not report_data["is_finalized"]:
            raise HTTPException(status_code=403, detail="Report is not finalized yet.")
            
        return report_data["formatted_file_path"]
    except Exception as e:
        print(f"Error fetching report path: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error fetching report: {str(e)}")


def find_report_file_locally(report_id: str):
    """
    Find a report file locally based on UUID.
    
    Args:
        report_id: UUID of the report
        
    Returns:
        Path to the report file or None if not found
    """
    # Check if this ID corresponds to a directory in uploads
    report_dir = os.path.join(settings.UPLOAD_DIR, report_id)
    
    if os.path.exists(report_dir) and os.path.isdir(report_dir):
        # First check metadata.json for the PDF path
        metadata_path = os.path.join(report_dir, "metadata.json")
        if os.path.exists(metadata_path):
            try:
                with open(metadata_path, "r") as f:
                    metadata = json.load(f)
                    if "pdf_path" in metadata and os.path.exists(metadata["pdf_path"]):
                        return metadata["pdf_path"]
            except Exception as e:
                print(f"Error reading metadata for {report_id}: {str(e)}")
        
        # If metadata doesn't have the path, search for PDF files in the report directory
        pdf_files = glob.glob(os.path.join(report_dir, "*.pdf"))
        if pdf_files:
            # Use the most recently modified PDF file
            return max(pdf_files, key=os.path.getmtime)
        
        # If no PDFs in report directory, check the reports directory
        import hashlib
        hash_id = int(hashlib.md5(report_id.encode()).hexdigest(), 16) % 10000000
        report_filename = f"report_{hash_id}.pdf"
        
        # Check in the generated reports directory
        report_path = os.path.join(settings.GENERATED_REPORTS_DIR, report_filename)
        if os.path.exists(report_path):
            return report_path
            
        # Check for any file that contains the report ID
        all_pdfs = glob.glob(os.path.join(settings.GENERATED_REPORTS_DIR, "*.pdf"))
        for pdf in all_pdfs:
            if report_id in os.path.basename(pdf):
                return pdf
    
    return None


@router.get("/{report_id}")
async def download_report(report_id: str):
    """
    Download a finalized report PDF.
    """
    # First check if this is a UUID that exists locally
    is_uuid = False
    local_path = None
    
    if "-" in report_id:
        is_uuid = True
        local_path = find_report_file_locally(report_id)
    
    # If found locally, return the file
    if local_path and os.path.exists(local_path):
        filename = os.path.basename(local_path)
        return FileResponse(
            local_path,
            media_type="application/pdf",
            filename=filename,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    
    # If not found locally or not a UUID, try the database
    try:
        file_path = fetch_report_path_from_supabase(report_id)
        
        if not file_path:
            raise HTTPException(status_code=404, detail=f"No file found for report with ID {report_id}")
            
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail=f"File not found at path: {file_path}")
            
        # Return the PDF file as an attachment
        filename = os.path.basename(file_path)
        return FileResponse(
            file_path,
            media_type="application/pdf",
            filename=filename,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
            
    except HTTPException:
        # If database lookup fails for a UUID, make one more attempt to find any report
        if is_uuid:
            # Generate a hash-based filename as a last resort
            import hashlib
            hash_id = int(hashlib.md5(report_id.encode()).hexdigest(), 16) % 10000000
            last_resort_filename = f"report_{hash_id}.pdf"
            
            # Check all possible locations
            possible_paths = [
                os.path.join(settings.GENERATED_REPORTS_DIR, last_resort_filename),
                os.path.join(settings.UPLOAD_DIR, report_id, last_resort_filename),
                os.path.join("reports", last_resort_filename),
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    filename = os.path.basename(path)
                    return FileResponse(
                        path,
                        media_type="application/pdf",
                        filename=filename,
                        headers={"Content-Disposition": f"attachment; filename={filename}"}
                    )
            
            # If all else fails, return a more helpful error message
            raise HTTPException(
                status_code=404, 
                detail=f"Could not find any report file for ID {report_id}. "
                       f"Please try regenerating the report."
            )
        else:
            # For non-UUID IDs, re-raise the original exception
            raise
            
    except Exception as e:
        # Return a generic error for any other exception
        print(f"Error downloading report: {str(e)}")
        traceback.print_exc()
        raise HTTPException(
            status_code=500, 
            detail=f"Error downloading report: {str(e)}"
        )


@router.get("/file/{report_id}")
async def serve_report_file(report_id: str):
    """Serve the actual report file"""
    try:
        file_path = fetch_report_path_from_supabase(report_id)
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Report file not found on server")
        
        return FileResponse(
            path=file_path,
            filename=f"report_{report_id}.pdf",
            media_type="application/pdf"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error serving file: {str(e)}")


@router.post("/cleanup/{report_id}")
async def cleanup_report_files(report_id: str):
    """
    Clean up all temporary files associated with a report after it has been successfully
    downloaded. This ensures that uploaded files don't persist in storage.
    
    Args:
        report_id: The ID of the report to clean up files for
        
    Returns:
        A status message indicating success or failure
    """
    # Define paths for report files
    report_dir = os.path.join(settings.UPLOAD_DIR, report_id)
    
    try:
        if os.path.exists(report_dir) and os.path.isdir(report_dir):
            # Get list of files before deletion for logging
            files_to_delete = os.listdir(report_dir)
            
            # Remove all files in the directory
            for filename in files_to_delete:
                file_path = os.path.join(report_dir, filename)
                if os.path.isfile(file_path):
                    os.remove(file_path)
                    print(f"Deleted file: {file_path}")
                    
            # Remove the directory itself
            os.rmdir(report_dir)
            print(f"Deleted directory: {report_dir}")
            
            # Update database status if using Supabase
            try:
                from supabase import create_client, Client
                
                # Initialize Supabase client
                supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
                
                # Mark report as cleaned up in database
                supabase.table("reports").update({"files_cleaned": True}).eq("id", report_id).execute()
                print(f"Updated database for report {report_id}: files_cleaned=True")
                
            except Exception as e:
                print(f"Error updating database status: {str(e)}")
            
            return {
                "status": "success",
                "message": f"Successfully cleaned up {len(files_to_delete)} files for report {report_id}"
            }
        else:
            return {
                "status": "warning",
                "message": f"Report directory not found: {report_dir}"
            }
    except Exception as e:
        print(f"Error cleaning up report files: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to clean up report files: {str(e)}"
        }


@router.get("/docx/{report_id}")
async def download_docx_report(report_id: str):
    """
    Download a finalized report as DOCX by ID.
    
    Args:
        report_id: ID of the report to download
        
    Returns:
        The DOCX file as a download
    """
    try:
        # Get file path from Supabase
        file_path = fetch_report_path_from_supabase(report_id)
        
        if not file_path:
            raise HTTPException(status_code=404, detail="Report file not found")
        
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
            
        # Return the file as a download
        return FileResponse(
            path=file_path,
            filename=f"report_{report_id}.docx",
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error downloading report: {str(e)}")


@router.get("/file/docx/{report_id}")
async def serve_docx_report_file(report_id: str):
    """
    Serve a DOCX report file directly.
    
    Args:
        report_id: ID of the report to serve
        
    Returns:
        The DOCX file
    """
    try:
        # Get file path from Supabase
        file_path = fetch_report_path_from_supabase(report_id)
        
        if not file_path:
            raise HTTPException(status_code=404, detail="Report file not found")
        
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
        
        # Return the file
        return FileResponse(
            path=file_path,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error serving report file: {str(e)}")
