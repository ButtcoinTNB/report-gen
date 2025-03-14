from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
import os
from supabase import create_client, Client
from config import settings

router = APIRouter()


def fetch_report_path_from_supabase(report_id: int):
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
async def download_report(report_id: int):
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
async def serve_report_file(report_id: int):
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
