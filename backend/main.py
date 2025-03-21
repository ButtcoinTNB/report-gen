"""
Main application entrypoint for the Insurance Report Generator API
"""

# Import the path fixer before any other imports to ensure proper module resolution
import os
import sys
try:
    # Try to import fix_paths - this works when the current directory is backend/
    from fix_paths import backend_dir
    print("Successfully imported fix_paths")
except ImportError:
    print("Could not import fix_paths directly, adjusting path...")
    # If running from a different directory, try to add the backend directory to the path
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)
        print(f"Added backend directory to path: {backend_dir}")
    try:
        from fix_paths import backend_dir
        print("Successfully imported fix_paths after path adjustment")
    except ImportError:
        # If still cannot import, create __init__.py files manually
        print("Failed to import fix_paths, creating __init__.py files manually")
        for dir_name in ['api', 'utils', 'services', 'models']:
            dir_path = os.path.join(backend_dir, dir_name)
            if os.path.isdir(dir_path):
                init_file = os.path.join(dir_path, '__init__.py')
                if not os.path.exists(init_file):
                    try:
                        with open(init_file, 'w') as f:
                            f.write('# Auto-generated __init__.py file\n')
                        print(f"Created {init_file}")
                    except Exception as e:
                        print(f"Failed to create {init_file}: {str(e)}")

# Now the rest of the imports should work correctly
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import uvicorn
import asyncio
import time
from datetime import datetime, timedelta
from pathlib import Path

# Import API route modules
from api import upload, generate, format, edit, download
from config import settings
from backend.utils.file_utils import safe_path_join
from backend.api.schemas import APIResponse
from backend.utils.exceptions import BaseAPIException
from backend.utils.error_handler import api_exception_handler
from backend.utils.openapi import custom_openapi
from backend.api.openapi_examples import ENDPOINT_EXAMPLES
from backend.utils.middleware import setup_middleware

# Debug imports
import traceback

# Import logger
try:
    from utils.error_handler import logger
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

# Ensure required directories exist
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.GENERATED_REPORTS_DIR, exist_ok=True)
print(f"Ensured directories exist: {settings.UPLOAD_DIR}, {settings.GENERATED_REPORTS_DIR}")

# Validate environment variables
missing_vars = settings.validate_all()
if missing_vars:
    logger.warning(f"⚠️ STARTUP WARNING: Missing or invalid environment variables: {', '.join(missing_vars)}")
    logger.warning("⚠️ Some application features may not work correctly. Please check your .env file.")
else:
    logger.info("✅ All required environment variables are properly configured.")

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
        logger.info(f"Starting cleanup of abandoned data older than {max_age_hours} hours")
        current_time = time.time()
        files_cleaned = 0
        
        # Clean up old uploads
        if os.path.exists(settings.UPLOAD_DIR):
            for item in os.listdir(settings.UPLOAD_DIR):
                try:
                    item_path = safe_path_join(settings.UPLOAD_DIR, item)
                    
                    # Skip if not a directory (report uploads are in subdirectories)
                    if not os.path.isdir(item_path):
                        continue
                        
                    # Check if directory is older than the max age
                    try:
                        # Get the most recent modification time of any file in the directory
                        latest_mod_time = current_time
                        for root, _, files in os.walk(item_path):
                            for file in files:
                                try:
                                    file_path = safe_path_join(root, file)
                                    mod_time = os.path.getmtime(file_path)
                                    latest_mod_time = min(latest_mod_time, mod_time)
                                except ValueError as e:
                                    logger.warning(f"Skipping invalid file path: {e}")
                                    continue
                        
                        # Calculate age in hours
                        age_hours = (current_time - latest_mod_time) / 3600
                        
                        # Delete if older than max age
                        if age_hours > max_age_hours:
                            logger.info(f"Cleaning up old upload directory: {item_path} (Age: {age_hours:.1f} hours)")
                            
                            # Delete all files in the directory
                            for root, _, files in os.walk(item_path, topdown=False):
                                for file in files:
                                    try:
                                        file_path = safe_path_join(root, file)
                                        os.remove(file_path)
                                        files_cleaned += 1
                                    except (ValueError, OSError) as e:
                                        logger.error(f"Error deleting file: {str(e)}")
                            
                            # Delete the directory itself
                            try:
                                os.rmdir(item_path)
                            except Exception as e:
                                logger.error(f"Error deleting directory {item_path}: {str(e)}")
                    except Exception as e:
                        logger.error(f"Error checking age of directory {item_path}: {str(e)}")
                except ValueError as e:
                    logger.warning(f"Skipping invalid path in uploads directory: {e}")
        
        # Clean up old generated reports
        if os.path.exists(settings.GENERATED_REPORTS_DIR):
            for file in os.listdir(settings.GENERATED_REPORTS_DIR):
                try:
                    file_path = safe_path_join(settings.GENERATED_REPORTS_DIR, file)
                    
                    # Skip if not a file
                    if not os.path.isfile(file_path):
                        continue
                        
                    try:
                        # Get file modification time
                        mod_time = os.path.getmtime(file_path)
                        age_hours = (current_time - mod_time) / 3600
                        
                        # Delete if older than max age
                        if age_hours > max_age_hours:
                            logger.info(f"Cleaning up old generated file: {file_path} (Age: {age_hours:.1f} hours)")
                            os.remove(file_path)
                            files_cleaned += 1
                    except Exception as e:
                        logger.error(f"Error cleaning up file {file_path}: {str(e)}")
                except ValueError as e:
                    logger.warning(f"Skipping invalid path in generated reports directory: {e}")
        
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
                
                logger.info(f"Marked old reports as cleaned in database: {response}")
        except Exception as e:
            logger.error(f"Error updating database for old reports: {str(e)}")
        
        logger.info(f"Cleanup complete. Removed {files_cleaned} stale files.")
        
    except Exception as e:
        logger.error(f"Error in cleanup_old_data: {str(e)}")
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
            content=APIResponse(
                status="error",
                message="File too large. The maximum allowed size is 1GB.",
                code="FILE_TOO_LARGE"
            ).dict()
        )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=APIResponse(
            status="error", 
            message=str(exc), 
            code="VALIDATION_ERROR"
        ).dict()
    )

# Register our custom exception handler
app.add_exception_handler(BaseAPIException, api_exception_handler)

# Set up middleware
setup_middleware(app)

# Use the new settings property for allowed origins
# Use a conditional log level based on environment
if os.getenv("NODE_ENV") == "production":
    logger.info(f"CORS allowed origins in production: {settings.allowed_origins}")
else:
    print(f"CORS allowed origins: {settings.allowed_origins}")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,  # Use the new property from settings
    allow_credentials=True,  # Set to True for cookies if using authentication
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],  # Include OPTIONS for preflight
    allow_headers=["*"],  # Allow all headers
    expose_headers=["Content-Disposition"],  # Expose headers needed for file downloads
    max_age=86400,  # Cache preflight request for 24 hours
)

# Include API routes
app.include_router(upload.router, prefix="/api/upload", tags=["Upload"])
app.include_router(generate.router, prefix="/api/generate", tags=["Generate"])
app.include_router(format.router, prefix="/api/format", tags=["Format"])
app.include_router(edit.router, prefix="/api/edit", tags=["Edit"])
app.include_router(download.router, prefix="/api/download", tags=["Download"])

# Apply custom OpenAPI documentation
app.openapi = lambda: custom_openapi(app, ENDPOINT_EXAMPLES)

@app.get("/", tags=["Root"])
async def root():
    return {"message": "Welcome to the Scrittore Automatico di Perizie API"}


@app.get("/health", tags=["Monitoring"])
async def health_check():
    """
    Health check endpoint for monitoring systems.
    Returns 200 OK if the API is running properly.
    """
    # Check critical dependencies
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "0.1.0",
    }
    
    # Check if we can access the file system
    try:
        # Try to write a test file
        test_path = safe_path_join(settings.UPLOAD_DIR, ".health_check")
        with open(test_path, "w") as f:
            f.write("ok")
        os.remove(test_path)
        health_status["file_system"] = "ok"
    except Exception as e:
        health_status["file_system"] = "error"
        health_status["file_system_error"] = str(e)
        health_status["status"] = "degraded"
    
    return health_status


@app.get("/cors-test", tags=["Debug"])
async def cors_test(request: Request):
    """
    Simple endpoint to test if CORS is working correctly
    Returns details about the request to help debug CORS issues
    """
    # Check if we're in production mode
    if os.getenv("NODE_ENV") == "production":
        # In production, return minimal information
        return {
            "message": "CORS is configured correctly", 
            "status": "ok"
        }
    
    # In development, return detailed debug information
    return {
        "message": "CORS is working correctly", 
        "status": "ok",
        "request_details": {
            "headers": dict(request.headers),
            "client_host": request.client.host if request.client else None,
            "method": request.method,
            "url": str(request.url)
        }
    }


@app.get("/debug", tags=["Debug"])
async def debug():
    """Debug endpoint to check environment and imports"""
    # Only enable in development mode
    if os.getenv("NODE_ENV") == "production":
        return {"message": "Debug endpoints are disabled in production"}
        
    # In development, return detailed system information
    modules = []
    for name, module in sys.modules.items():
        if "." not in name and not name.startswith("_"):
            modules.append(name)
    
    return {
        "message": "Debug information",
        "environment": {
            "python_version": sys.version,
            "sys_path": sys.path,
            "os_name": os.name,
            "current_dir": os.getcwd(),
            "upload_dir": settings.UPLOAD_DIR,
            "generated_reports_dir": settings.GENERATED_REPORTS_DIR
        },
        "loaded_modules": sorted(modules)
    }


if __name__ == "__main__":
    # This configuration is only used for local development
    # For production on Render, the command is specified in the Render dashboard
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True,
        timeout_keep_alive=120  # Keep connection alive longer
    )
