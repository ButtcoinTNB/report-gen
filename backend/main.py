from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import uvicorn
import os
import sys
import asyncio
import time
from datetime import datetime, timedelta

# Import rootpath utility to ensure proper module imports
from rootpath import ensure_root_in_path
project_root, backend_dir = ensure_root_in_path()

# Import API route modules
from api import upload, generate, format, edit, download
from config import settings

# Debug imports
import traceback

# Ensure required directories exist
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.GENERATED_REPORTS_DIR, exist_ok=True)
print(f"Ensured directories exist: {settings.UPLOAD_DIR}, {settings.GENERATED_REPORTS_DIR}")

app = FastAPI(
    title="Scrittore Automatico di Perizie",
    description="API for generating structured insurance claim reports",
    version="0.1.0",
)

# Add a function to clean up old reports and uploads
async def cleanup_old_data(max_age_hours: int = 24):
    """
    Clean up old reports and uploads that haven't been accessed in the specified time.
    This ensures all data is ephemeral and not stored longer than necessary.
    
    Args:
        max_age_hours: Maximum age in hours before data is considered stale
    """
    try:
        print(f"Starting cleanup of abandoned data older than {max_age_hours} hours")
        current_time = time.time()
        files_cleaned = 0
        
        # Clean up old uploads
        if os.path.exists(settings.UPLOAD_DIR):
            for item in os.listdir(settings.UPLOAD_DIR):
                item_path = os.path.join(settings.UPLOAD_DIR, item)
                
                # Skip if not a directory (report uploads are in subdirectories)
                if not os.path.isdir(item_path):
                    continue
                    
                # Check if directory is older than the max age
                try:
                    # Get the most recent modification time of any file in the directory
                    latest_mod_time = current_time
                    for root, _, files in os.walk(item_path):
                        for file in files:
                            file_path = os.path.join(root, file)
                            mod_time = os.path.getmtime(file_path)
                            latest_mod_time = min(latest_mod_time, mod_time)
                    
                    # Calculate age in hours
                    age_hours = (current_time - latest_mod_time) / 3600
                    
                    # Delete if older than max age
                    if age_hours > max_age_hours:
                        print(f"Cleaning up old upload directory: {item_path} (Age: {age_hours:.1f} hours)")
                        
                        # Delete all files in the directory
                        for root, _, files in os.walk(item_path, topdown=False):
                            for file in files:
                                file_path = os.path.join(root, file)
                                try:
                                    os.remove(file_path)
                                    files_cleaned += 1
                                except Exception as e:
                                    print(f"Error deleting file {file_path}: {str(e)}")
                        
                        # Delete the directory itself
                        try:
                            os.rmdir(item_path)
                        except Exception as e:
                            print(f"Error deleting directory {item_path}: {str(e)}")
                except Exception as e:
                    print(f"Error checking age of directory {item_path}: {str(e)}")
        
        # Clean up old generated reports
        if os.path.exists(settings.GENERATED_REPORTS_DIR):
            for file in os.listdir(settings.GENERATED_REPORTS_DIR):
                file_path = os.path.join(settings.GENERATED_REPORTS_DIR, file)
                
                # Skip if not a file
                if not os.path.isfile(file_path):
                    continue
                    
                try:
                    # Get file modification time
                    mod_time = os.path.getmtime(file_path)
                    age_hours = (current_time - mod_time) / 3600
                    
                    # Delete if older than max age
                    if age_hours > max_age_hours:
                        print(f"Cleaning up old generated file: {file_path} (Age: {age_hours:.1f} hours)")
                        os.remove(file_path)
                        files_cleaned += 1
                except Exception as e:
                    print(f"Error cleaning up file {file_path}: {str(e)}")
        
        # Also clean up preview files using the existing service
        from services.preview_service import preview_service
        preview_service.cleanup_old_previews(max_age_hours)
        
        # Update database if using Supabase to mark old reports as cleaned
        try:
            # Only connect to Supabase if URLs are configured
            if settings.SUPABASE_URL and settings.SUPABASE_KEY:
                from utils.supabase_helper import create_supabase_client
                
                # Create client with the helper function that handles proxy issues
                supabase = create_supabase_client()
                
                # Get the timestamp for max_age_hours ago
                max_age_time = datetime.now() - timedelta(hours=max_age_hours)
                max_age_str = max_age_time.isoformat()
                
                # Update reports older than max_age_hours and not yet cleaned
                response = supabase.table("reports").update(
                    {"files_cleaned": True}
                ).filter("created_at", "lt", max_age_str).filter("files_cleaned", "eq", False).execute()
                
                print(f"Marked old reports as cleaned in database: {response}")
        except Exception as e:
            print(f"Error updating database for old reports: {str(e)}")
        
        print(f"Cleanup complete. Removed {files_cleaned} stale files.")
        
    except Exception as e:
        print(f"Error in cleanup_old_data: {str(e)}")
        traceback.print_exc()

# Configure background task for periodic cleanup
async def start_cleanup_scheduler():
    """
    Start a background task that runs the cleanup function every hour
    """
    while True:
        await cleanup_old_data(settings.DATA_RETENTION_HOURS)
        # Wait for 1 hour before next cleanup
        await asyncio.sleep(3600)

@app.on_event("startup")
async def startup_event():
    """
    Run when the application starts up
    """
    # Run an initial cleanup
    await cleanup_old_data(settings.DATA_RETENTION_HOURS)
    
    # Start the periodic cleanup task
    asyncio.create_task(start_cleanup_scheduler())
    print("Started periodic cleanup scheduler")

# Configure for large files
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors, especially those related to file uploads"""
    print(f"Validation error: {exc}")
    error_detail = str(exc)
    
    if "entity too large" in error_detail.lower():
        return JSONResponse(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            content={
                "status": "error",
                "detail": f"File too large. The maximum allowed size is 1GB.",
                "code": "FILE_TOO_LARGE"
            }
        )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "status": "error", 
            "detail": str(exc), 
            "code": "VALIDATION_ERROR"
        }
    )

# Get allowed origins - split by comma if it's a list
frontend_urls = settings.FRONTEND_URL.split(',') if ',' in settings.FRONTEND_URL else [settings.FRONTEND_URL]

# Add Vercel domain explicitly
allowed_origins = frontend_urls + [
    "https://report-gen-liard.vercel.app",
    "https://report-gen.vercel.app",
    "https://report-gen-5wtl.onrender.com",  # Add Render domain
    "http://localhost:3000",
    "http://127.0.0.1:3000"
]

print(f"CORS allowed origins: {allowed_origins}")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for debugging
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],  # Include OPTIONS for preflight
    allow_headers=["*"],
    max_age=86400,  # Cache preflight request for 24 hours
)

# Include API routes
app.include_router(upload.router, prefix="/api/upload", tags=["Upload"])
app.include_router(generate.router, prefix="/api/generate", tags=["Generate"])
app.include_router(format.router, prefix="/api/format", tags=["Format"])
app.include_router(edit.router, prefix="/api/edit", tags=["Edit"])
app.include_router(download.router, prefix="/api/download", tags=["Download"])


@app.get("/", tags=["Root"])
async def root():
    return {"message": "Welcome to the Scrittore Automatico di Perizie API"}


@app.get("/debug", tags=["Debug"])
async def debug():
    """Debug endpoint to check environment and imports"""
    result = {
        "cwd": os.getcwd(),
        "python_path": sys.path,
        "dir_contents": os.listdir("."),
    }
    
    # Test imports
    import_results = {}
    
    # Try relative import
    try:
        from models import Report, File, User
        import_results["from_models"] = "Success"
    except ImportError as e:
        import_results["from_models"] = f"Error: {str(e)}"
        
    # Try import with backend prefix - commenting this out for consistency
    try:
        # Using consistent import pattern instead of 'from models'
        from models import Report, File, User
        import_results["from_backend_models"] = "Success"
    except ImportError as e:
        import_results["from_backend_models"] = f"Error: {str(e)}"
    
    # Check file existence
    file_checks = {
        "models.py_exists": os.path.exists("models.py"),
        "backend_models.py_exists": os.path.exists("backend/models.py"),
        "api_generate.py_exists": os.path.exists("api/generate.py"),
    }
    
    # Check file contents
    file_contents = {}
    try:
        if os.path.exists("api/generate.py"):
            with open("api/generate.py", "r") as f:
                for i, line in enumerate(f, 1):
                    if "from " in line and "models" in line and "import" in line:
                        file_contents[f"generate.py_line_{i}"] = line.strip()
                        if i >= 20:  # Only check first 20 lines
                            break
    except Exception as e:
        file_contents["error"] = str(e)
    
    result["import_results"] = import_results
    result["file_checks"] = file_checks
    result["file_contents"] = file_contents
    
    return result


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
