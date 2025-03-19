from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
import os
import glob
import json
from supabase import create_client, Client
from config import settings
from utils.id_mapper import ensure_id_is_int
import traceback
import hashlib
from datetime import datetime

# Import format functions to avoid circular imports later
try:
    from api.format import format_final, update_report_file_path, get_reference_metadata
    from services.pdf_formatter import format_report_as_pdf
except ImportError:
    # This allows for cleaner error handling if imports fail
    print("Warning: Could not import formatting functions, will import when needed")

router = APIRouter()


def get_report_content(report_id: str):
    """
    Retrieve the actual report content (markdown text) from any available source.
    This is a more thorough content retrieval function that checks all possible storage locations.
    
    Args:
        report_id: The ID of the report (either UUID or integer)
        
    Returns:
        The report content as text, or None if not found
    """
    print(f"Attempting to retrieve content for report ID: {report_id}")
    report_content = None
    
    # First, check if this is a UUID with a directory in uploads
    is_uuid = False
    if "-" in report_id:
        is_uuid = True
        report_dir = os.path.join(settings.UPLOAD_DIR, report_id)
        
        if os.path.exists(report_dir) and os.path.isdir(report_dir):
            # Try metadata.json first (our most reliable source after changes)
            metadata_path = os.path.join(report_dir, "metadata.json")
            if os.path.exists(metadata_path):
                try:
                    with open(metadata_path, "r") as f:
                        metadata = json.load(f)
                        if "report_content" in metadata:
                            report_content = metadata["report_content"]
                            print(f"Successfully retrieved content from metadata.json for {report_id}")
                            return report_content
                except Exception as e:
                    print(f"Error reading metadata.json: {str(e)}")
            
            # Try content.txt next
            content_path = os.path.join(report_dir, "content.txt")
            if os.path.exists(content_path):
                try:
                    with open(content_path, "r") as f:
                        report_content = f.read()
                        print(f"Successfully retrieved content from content.txt for {report_id}")
                        return report_content
                except Exception as e:
                    print(f"Error reading content.txt: {str(e)}")
    
    # If not found locally, try Supabase
    try:
        # Try to convert to integer for database lookup
        try:
            db_id = ensure_id_is_int(report_id)
        except ValueError:
            db_id = None
        
        if db_id is not None:
            # Initialize Supabase client
            supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
            
            # Try to find by ID first - specifically select content
            print(f"Looking for report content in database with ID: {db_id}")
            response = supabase.table("reports").select("content").eq("id", db_id).execute()
            
            # If not found by ID and it's a UUID format, try searching by UUID too
            if (not response.data or not response.data[0]) and is_uuid:
                print(f"Report content not found by ID {db_id}, trying UUID: {report_id}")
                response = supabase.table("reports").select("content").eq("uuid", report_id).execute()
            
            if response.data and response.data[0] and "content" in response.data[0]:
                report_content = response.data[0]["content"]
                print(f"Successfully retrieved content from database for {report_id}")
                return report_content
    except Exception as e:
        print(f"Error retrieving content from database: {str(e)}")
    
    # If we still don't have content, return None
    print(f"Could not find content for report {report_id} in any location")
    return None


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
            # Try to find by ID first - select both file path columns
            print(f"Looking for report with ID: {db_id}")
            response = supabase.table("reports").select("formatted_file_path,file_path,is_finalized").eq("id", db_id).execute()
            
            # If not found by ID and it's a UUID format, try searching by UUID too
            if (not response.data or not response.data[0]) and isinstance(report_id, str) and "-" in report_id:
                print(f"Report not found by ID {db_id}, trying UUID: {report_id}")
                response = supabase.table("reports").select("formatted_file_path,file_path,is_finalized").eq("uuid", report_id).execute()
            
        except Exception as e:
            # If database query fails, try to find the file locally
            print(f"Database error: {str(e)}")
            local_path = find_docx_file_locally(report_id)
            if local_path:
                return local_path
            raise HTTPException(status_code=500, detail="Database error when retrieving report")
        
        if not response.data:
            raise HTTPException(status_code=404, detail=f"Report with ID {report_id} not found in the database.")
            
        report_data = response.data[0]
        if not report_data["is_finalized"]:
            raise HTTPException(status_code=403, detail="Report is not finalized yet.")
        
        # Try both path fields, prioritizing formatted_file_path
        file_path = None
        if report_data.get("formatted_file_path") and os.path.exists(report_data["formatted_file_path"]):
            file_path = report_data["formatted_file_path"]
        elif report_data.get("file_path") and os.path.exists(report_data["file_path"]):
            file_path = report_data["file_path"]
        
        # Ensure the file is a DOCX file
        if file_path and not file_path.lower().endswith('.docx'):
            # Try to find a DOCX version of the file
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            docx_path = os.path.join(settings.GENERATED_REPORTS_DIR, f"{base_name}.docx")
            
            if os.path.exists(docx_path):
                file_path = docx_path
            else:
                file_path = None  # File exists but not as DOCX
        
        # If no valid path found in the database, fall back to local search
        if not file_path:
            print(f"No valid DOCX file path found in database, searching locally for: {report_id}")
            local_path = find_docx_file_locally(report_id)
            if local_path:
                return local_path
            raise HTTPException(status_code=404, detail=f"DOCX report file not found for ID: {report_id}")
            
        return file_path
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
        generated_reports_dir = settings.GENERATED_REPORTS_DIR
        if not os.path.isabs(generated_reports_dir):
            # If it's a relative path, make it absolute
            generated_reports_dir = os.path.abspath(generated_reports_dir)
            
        report_path = os.path.join(generated_reports_dir, report_filename)
        if os.path.exists(report_path):
            return report_path
            
        # Check for any file that contains the report ID in various directories
        search_dirs = [
            generated_reports_dir,
            os.path.join(os.getcwd(), "generated_reports"),
            os.path.join(os.getcwd(), "backend", "generated_reports"),
            "./generated_reports",
            "../generated_reports",
            "/tmp/generated_reports"
        ]
        
        for search_dir in search_dirs:
            if os.path.exists(search_dir) and os.path.isdir(search_dir):
                # Look for any PDF file with matching ID or hash in name
                pdf_files = glob.glob(os.path.join(search_dir, "*.pdf"))
                for pdf_file in pdf_files:
                    filename = os.path.basename(pdf_file)
                    if report_id in filename or str(hash_id) in filename:
                        print(f"Found matching report PDF: {pdf_file}")
                        return pdf_file
    
    # If still not found, try searching all PDFs in the generated reports directory
    try:
        print(f"Looking for any PDFs related to report ID: {report_id}")
        
        # Check if generated reports directory exists
        if os.path.exists(settings.GENERATED_REPORTS_DIR) and os.path.isdir(settings.GENERATED_REPORTS_DIR):
            all_pdfs = glob.glob(os.path.join(settings.GENERATED_REPORTS_DIR, "*.pdf"))
            all_pdfs.extend(glob.glob(os.path.join(settings.GENERATED_REPORTS_DIR, "**", "*.pdf")))
            
            if all_pdfs:
                print(f"Found {len(all_pdfs)} PDFs to check")
                # Return the most recently modified PDF as a last resort
                newest_pdf = max(all_pdfs, key=os.path.getmtime)
                print(f"Using most recent PDF: {newest_pdf}")
                return newest_pdf
    except Exception as e:
        print(f"Error during extended PDF search: {str(e)}")
    
    return None


def find_docx_file_locally(report_id: str):
    """
    Find a report DOCX file locally based on UUID.
    
    Args:
        report_id: UUID of the report
        
    Returns:
        Path to the report DOCX file or None if not found
    """
    # Check if this ID corresponds to a directory in uploads
    report_dir = os.path.join(settings.UPLOAD_DIR, report_id)
    
    if os.path.exists(report_dir) and os.path.isdir(report_dir):
        # First check metadata.json for the DOCX path
        metadata_path = os.path.join(report_dir, "metadata.json")
        if os.path.exists(metadata_path):
            try:
                with open(metadata_path, "r") as f:
                    metadata = json.load(f)
                    if "docx_path" in metadata and os.path.exists(metadata["docx_path"]):
                        return metadata["docx_path"]
            except Exception as e:
                print(f"Error reading metadata for {report_id}: {str(e)}")
        
        # If metadata doesn't have the path, search for DOCX files in the report directory
        docx_files = glob.glob(os.path.join(report_dir, "*.docx"))
        if docx_files:
            # Use the most recently modified DOCX file
            return max(docx_files, key=os.path.getmtime)
        
        # If no DOCXs in report directory, check the reports directory
        import hashlib
        hash_id = int(hashlib.md5(report_id.encode()).hexdigest(), 16) % 10000000
        report_filename = f"report_{hash_id}.docx"
        
        # Check in the generated reports directory
        generated_reports_dir = settings.GENERATED_REPORTS_DIR
        if not os.path.isabs(generated_reports_dir):
            # If it's a relative path, make it absolute
            generated_reports_dir = os.path.abspath(generated_reports_dir)
            
        report_path = os.path.join(generated_reports_dir, report_filename)
        if os.path.exists(report_path):
            return report_path
            
        # Check for any file that contains the report ID in various directories
        search_dirs = [
            generated_reports_dir,
            os.path.join(os.getcwd(), "generated_reports"),
            os.path.join(os.getcwd(), "backend", "generated_reports"),
            "./generated_reports",
            "../generated_reports",
            "/tmp/generated_reports"
        ]
        
        for search_dir in search_dirs:
            if os.path.exists(search_dir) and os.path.isdir(search_dir):
                # Look for any DOCX file with matching ID or hash in name
                docx_files = glob.glob(os.path.join(search_dir, "*.docx"))
                for docx_file in docx_files:
                    filename = os.path.basename(docx_file)
                    if report_id in filename or str(hash_id) in filename:
                        print(f"Found matching report DOCX: {docx_file}")
                        return docx_file
    
    # If still not found, try searching all DOCXs in the generated reports directory
    try:
        print(f"Looking for any DOCXs related to report ID: {report_id}")
        
        # Check if generated reports directory exists
        if os.path.exists(settings.GENERATED_REPORTS_DIR) and os.path.isdir(settings.GENERATED_REPORTS_DIR):
            all_docxs = glob.glob(os.path.join(settings.GENERATED_REPORTS_DIR, "*.docx"))
            all_docxs.extend(glob.glob(os.path.join(settings.GENERATED_REPORTS_DIR, "**", "*.docx")))
            
            if all_docxs:
                print(f"Found {len(all_docxs)} DOCXs to check")
                # Return the most recently modified DOCX as a last resort
                newest_docx = max(all_docxs, key=os.path.getmtime)
                print(f"Using most recent DOCX: {newest_docx}")
                return newest_docx
    except Exception as e:
        print(f"Error during extended DOCX search: {str(e)}")
    
    return None


@router.get("/{report_id}")
async def download_report(report_id: str):
    """
    Download a finalized report (DOCX only).
    Redirects to the DOCX download endpoint.
    """
    # Redirect to the DOCX download endpoint
    print(f"Redirecting download request for report ID: {report_id} to DOCX endpoint")
    return await download_docx_report(report_id)


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
    deleted_files = []
    
    try:
        # First, let's get any file path from the database to make sure we delete the final DOCX
        docx_path = None
        try:
            # Try to find the path in Supabase
            db_id = ensure_id_is_int(report_id)
            supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
            response = supabase.table("reports").select("formatted_file_path,file_path").eq("id", db_id).execute()
            
            if response.data and response.data[0]:
                if response.data[0].get("formatted_file_path") and os.path.exists(response.data[0]["formatted_file_path"]):
                    docx_path = response.data[0]["formatted_file_path"]
                elif response.data[0].get("file_path") and os.path.exists(response.data[0]["file_path"]):
                    docx_path = response.data[0]["file_path"]
        except Exception as e:
            print(f"Error retrieving file path from database: {str(e)}")
        
        # If we found a file path in the database, delete that file
        if docx_path and os.path.exists(docx_path):
            try:
                os.remove(docx_path)
                deleted_files.append(docx_path)
                print(f"Deleted final DOCX file: {docx_path}")
            except Exception as e:
                print(f"Error deleting final DOCX file: {str(e)}")
        
        # Check for report-related DOCX files in the generated_reports directory
        try:
            # Create a hash-based pattern for filenames
            hash_id = str(int(hashlib.md5(report_id.encode()).hexdigest(), 16) % 10000000)
            # Patterns to match different types of report files
            patterns = [
                f"report_{report_id}*.docx",
                f"report_{hash_id}*.docx",
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
        
        # Update database status if using Supabase
        try:
            # Initialize Supabase client
            supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
            
            # Mark report as cleaned up in database
            supabase.table("reports").update({"files_cleaned": True}).eq("id", report_id).execute()
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
        
        # Prepare the FileResponse
        response = FileResponse(
            path=file_path,
            filename=f"report_{report_id}.docx",
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        
        # Schedule cleanup to run after the response is sent (in background)
        # We use asyncio.create_task to run this in the background without awaiting it
        import asyncio
        asyncio.create_task(cleanup_report_files(report_id))
        print(f"Scheduled cleanup for report {report_id} after download")
        
        return response
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
