"""
Main application entrypoint for the Insurance Report Generator API
Handles both development and production environments
"""

import os
import sys
import logging
from pathlib import Path
import asyncio
import time
from datetime import datetime, timedelta

# Set up logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("main")

# Clean path setup - do this before any other imports
current_dir = os.getcwd()
parent_dir = os.path.dirname(os.path.abspath(__file__))

# Add essential directories to path
paths_to_add = [
    current_dir,
    parent_dir,
    os.path.dirname(parent_dir)
]

# Add subdirectories to path
subdirs = ['utils', 'api', 'services', 'models', 'config', 'schemas']
for subdir in subdirs:
    subdir_path = os.path.join(current_dir, subdir)
    if os.path.isdir(subdir_path):
        paths_to_add.append(subdir_path)

# Add all paths uniquely and in order
for path in paths_to_add:
    if path not in sys.path:
        sys.path.insert(0, path)
        logger.info(f"Added to Python path: {path}")

# Ensure necessary directories exist
os.makedirs("uploads", exist_ok=True)
os.makedirs("generated_reports", exist_ok=True)

# Ensure necessary __init__.py files exist
for dir_name in subdirs:
    dir_path = os.path.join(current_dir, dir_name)
    if os.path.isdir(dir_path):
        init_file = os.path.join(dir_path, '__init__.py')
        if not os.path.exists(init_file):
            with open(init_file, 'w') as f:
                f.write('# Auto-generated __init__.py file\n')
            logger.info(f"Created __init__.py in {dir_path}")

# Now we can safely import everything else
from fastapi import FastAPI, Request, status, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

# Import API routes and config
from api import upload, generate, format, edit, download
from config import settings
from api.agent_loop import router as agent_loop_router

# Import utilities
from utils.file_utils import safe_path_join
from utils.exceptions import BaseAPIException
from utils.error_handler import api_exception_handler
from utils.openapi import custom_openapi
from api.openapi_examples import ENDPOINT_EXAMPLES
from utils.middleware import setup_middleware

# Ensure required directories exist
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.GENERATED_REPORTS_DIR, exist_ok=True)
logger.info(f"Ensured directories exist: {settings.UPLOAD_DIR}, {settings.GENERATED_REPORTS_DIR}")

# Validate environment variables
missing_vars = settings.validate_all()
if missing_vars:
    logger.warning(f"⚠️ STARTUP WARNING: Missing or invalid environment variables: {', '.join(missing_vars)}")
    logger.warning("⚠️ Some application features may not work correctly. Please check your .env file.")
else:
    logger.info("✅ All required environment variables are properly configured.")

# Create FastAPI app
app = FastAPI(
    title="Insurance Report Generator API",
    description="API for generating insurance reports using AI agents",
    version="2.0.0",
    # Only show docs in non-production environment
    docs_url="/docs" if os.getenv("NODE_ENV") != "production" else None,
    redoc_url="/redoc" if os.getenv("NODE_ENV") != "production" else None,
)

# Configure CORS with proper error handling
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition", "Content-Type", "Content-Length"],
    max_age=86400,  # Cache preflight requests for 24 hours
)

# Add error handling middleware to ensure CORS headers are set even on errors
@app.middleware("http")
async def cors_error_handler(request: Request, call_next):
    try:
        response = await call_next(request)
        return response
    except Exception as e:
        # Get origin from request headers
        origin = request.headers.get("origin")
        
        # Check if origin is allowed
        if origin in settings.allowed_origins:
            # Return error response with CORS headers
            headers = {
                "Access-Control-Allow-Origin": origin,
                "Access-Control-Allow-Credentials": "true",
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
                "Access-Control-Allow-Headers": "*",
                "Access-Control-Expose-Headers": "Content-Disposition, Content-Type, Content-Length",
            }
            return JSONResponse(
                status_code=500,
                content={"detail": str(e)},
                headers=headers
            )
        raise  # Re-raise the exception if origin not allowed

# Set up middleware
setup_middleware(app)

# Exception handlers
@app.exception_handler(BaseAPIException)
async def api_exception_handler(request: Request, exc: BaseAPIException):
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.detail,
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    if isinstance(exc, BaseAPIException):
        return await api_exception_handler(request, exc)
    
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "code": "INTERNAL_ERROR",
            "message": "An unexpected error occurred",
            "details": str(exc) if os.getenv("NODE_ENV") != "production" else None
        },
    )

# Include API routes
app.include_router(upload.router, prefix="/api/upload", tags=["Upload"])
app.include_router(generate.router, prefix="/api/generate", tags=["Generate"])
app.include_router(format.router, prefix="/api/format", tags=["Format"])
app.include_router(edit.router, prefix="/api/edit", tags=["Edit"])
app.include_router(download.router, prefix="/api/download", tags=["Download"])
app.include_router(agent_loop_router, prefix="/api/v2", tags=["AI Agent Loop"])

# Add a function to clean up old reports and uploads
async def cleanup_old_data(max_age_hours: int = 24):
    """
    Clean up old reports and uploads that haven't been accessed in the specified time.
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
                    if not os.path.isdir(item_path):
                        continue
                    
                    # Check directory age and clean if old
                    latest_mod_time = max(
                        os.path.getmtime(os.path.join(root, file))
                        for root, _, files in os.walk(item_path)
                        for file in files
                    )
                    
                    age_hours = (current_time - latest_mod_time) / 3600
                    if age_hours > max_age_hours:
                        for root, _, files in os.walk(item_path, topdown=False):
                            for file in files:
                                try:
                                    file_path = safe_path_join(root, file)
                                    os.remove(file_path)
                                    files_cleaned += 1
                                except Exception as e:
                                    logger.error(f"Error deleting file {file_path}: {str(e)}")
                        
                        try:
                            os.rmdir(item_path)
                            logger.info(f"Cleaned up old upload directory: {item_path}")
                        except Exception as e:
                            logger.error(f"Error removing directory {item_path}: {str(e)}")
                            
                except Exception as e:
                    logger.error(f"Error processing upload directory {item}: {str(e)}")
        
        # Clean up old generated reports
        if os.path.exists(settings.GENERATED_REPORTS_DIR):
            for file in os.listdir(settings.GENERATED_REPORTS_DIR):
                try:
                    file_path = safe_path_join(settings.GENERATED_REPORTS_DIR, file)
                    if not os.path.isfile(file_path):
                        continue
                        
                    age_hours = (current_time - os.path.getmtime(file_path)) / 3600
                    if age_hours > max_age_hours:
                        os.remove(file_path)
                        files_cleaned += 1
                        logger.info(f"Cleaned up old generated file: {file_path}")
                except Exception as e:
                    logger.error(f"Error cleaning up file {file}: {str(e)}")
        
        # Clean up preview files
        try:
            from services.preview_service import preview_service
            preview_service.cleanup_old_previews(max_age_hours)
        except Exception as e:
            logger.error(f"Error cleaning up previews: {str(e)}")
        
        # Update database for cleaned files
        try:
            if settings.SUPABASE_URL and settings.SUPABASE_KEY:
                from utils.supabase_helper import create_supabase_client
                supabase = create_supabase_client()
                max_age_time = datetime.now() - timedelta(hours=max_age_hours)
                
                response = supabase.table("reports").update(
                    {"files_cleaned": True}
                ).filter("created_at", "lt", max_age_time.isoformat()
                ).filter("files_cleaned", "eq", False).execute()
                
                logger.info(f"Updated database for cleaned files: {response}")
        except Exception as e:
            logger.error(f"Error updating database: {str(e)}")
        
        logger.info(f"Cleanup complete. Removed {files_cleaned} stale files.")
        
    except Exception as e:
        logger.error(f"Error in cleanup_old_data: {str(e)}")

# Configure background task for periodic cleanup
async def start_cleanup_scheduler():
    """Start a background task that runs the cleanup function every hour"""
    while True:
        await cleanup_old_data(settings.DATA_RETENTION_HOURS)
        await asyncio.sleep(3600)  # Wait for 1 hour

@app.on_event("startup")
async def startup_event():
    """Run when the application starts up"""
    # Run initial cleanup
    await cleanup_old_data(settings.DATA_RETENTION_HOURS)
    # Start periodic cleanup task
    asyncio.create_task(start_cleanup_scheduler())

@app.get("/", tags=["Root"])
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to the Insurance Report Generator API",
        "version": app.version,
        "status": "operational"
    }

@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "version": app.version,
        "timestamp": datetime.now().isoformat()
    }

# For local development
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )

logger.info("Application initialized successfully!")
