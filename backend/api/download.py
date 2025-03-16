from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
import os
from supabase import create_client, Client
from config import settings

router = APIRouter()


def fetch_report_path_from_supabase(report_id: str):
    """
    Retrieves the finalized report file path from Supabase.
    """
    try:
        # Initialize Supabase client
        supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        
        # Query the reports table
        response = supabase.table("reports").select("formatted_file_path,is_finalized").eq("id", report_id).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Report not found in the database.")
            
        report_data = response.data[0]
        if not report_data["is_finalized"]:
            raise HTTPException(status_code=403, detail="Report is not finalized yet.")
            
        return report_data["formatted_file_path"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching report: {str(e)}")


@router.get("/{report_id}", response_model=dict)
async def download_report(report_id: str):
    """
    Download a finalized report by ID.
    
    Args:
        report_id: ID of the report to download
        
    Returns:
        Report details including download URL
    """
    try:
        # Get file path from Supabase
        file_path = fetch_report_path_from_supabase(report_id)
        
        if not file_path:
            raise HTTPException(status_code=404, detail="Report file not found")
        
        # Check if the file exists locally
        if not os.path.exists(file_path):
            # Try to download from Supabase Storage
            try:
                supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
                
                # Extract the storage path (remove any local path prefix)
                storage_path = file_path
                if "/" in storage_path:
                    storage_path = storage_path.split("/")[-1]
                
                # Get a signed URL for downloading
                response = supabase.storage.from_("reports").create_signed_url(storage_path, 60)  # 60 seconds expiry
                
                if "signedURL" in response:
                    return {
                        "report_id": report_id,
                        "filename": f"report_{report_id}.pdf",
                        "download_url": response["signedURL"],
                    }
            except Exception as storage_error:
                raise HTTPException(
                    status_code=500, 
                    detail=f"Error retrieving file from storage: {str(storage_error)}"
                )
        
        # If we have the file locally, serve it directly
        return {
            "report_id": report_id,
            "filename": os.path.basename(file_path),
            "download_url": f"/api/download/file/{report_id}",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error processing download request: {str(e)}"
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
