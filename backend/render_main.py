"""
Clean Render-specific entry point that avoids circular imports.
This file creates the FastAPI app directly without any imports from main.py.
"""

import os
import sys
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("render_main")

# Add current directory and parent directory to path
current_dir = os.getcwd()
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
    logger.info(f"Added current directory to path: {current_dir}")

parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
    logger.info(f"Added parent directory to path: {parent_dir}")

# Add subdirectories to path
for subdir in ['utils', 'api', 'services', 'models', 'config', 'schemas']:
    subdir_path = os.path.join(current_dir, subdir)
    if os.path.isdir(subdir_path) and subdir_path not in sys.path:
        sys.path.insert(0, subdir_path)
        logger.info(f"Added {subdir} directory to path: {subdir_path}")

# Create necessary directories
os.makedirs("uploads", exist_ok=True)
os.makedirs("generated_reports", exist_ok=True)

# Ensure necessary __init__.py files exist
for dir_name in ['api', 'utils', 'services', 'models', 'config']:
    dir_path = os.path.join(current_dir, dir_name)
    if os.path.isdir(dir_path):
        init_file = os.path.join(dir_path, '__init__.py')
        if not os.path.exists(init_file):
            with open(init_file, 'w') as f:
                f.write('# Auto-generated __init__.py file\n')
            logger.info(f"Created __init__.py in {dir_path}")

# The following code is adapted from backend/main.py but with direct imports
# to avoid circular reference issues

# Import FastAPI and necessary components
from fastapi import FastAPI, Depends, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exception_handlers import http_exception_handler

# Import configuration
from config import settings

# Import API routes
from api import upload, generate, format, edit, download

# Import utilities
import utils.exceptions
from utils.middleware import add_process_time_header

# Create the FastAPI app
app = FastAPI(
    title="Insurance Report Generator API",
    description="API for generating, formatting, and managing insurance reports",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],  # This is safe since we validate the origin
    expose_headers=["Content-Disposition", "Content-Type"],
    max_age=86400,  # 24 hours
)

# Add custom middleware
app.middleware("http")(add_process_time_header)

# Add error handling middleware to ensure CORS headers are set even on errors
@app.middleware("http")
async def add_cors_headers(request: Request, call_next):
    try:
        response = await call_next(request)
        return response
    except Exception as e:
        # Ensure CORS headers are set even on errors
        if request.headers.get("origin") in settings.allowed_origins:
            headers = {
                "Access-Control-Allow-Origin": request.headers["origin"],
                "Access-Control-Allow-Credentials": "true",
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                "Access-Control-Allow-Headers": "*",
                "Access-Control-Expose-Headers": "Content-Disposition, Content-Type",
            }
            return JSONResponse(
                status_code=500,
                content={"detail": str(e)},
                headers=headers
            )
        raise  # Re-raise the exception if origin is not allowed

# Add exception handlers - similar to those in backend/main.py
@app.exception_handler(utils.exceptions.BaseAPIException)
async def api_exception_handler(request: Request, exc: utils.exceptions.BaseAPIException):
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.detail,
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    if isinstance(exc, utils.exceptions.BaseAPIException):
        # Let the specialized handler take care of it
        return await api_exception_handler(request, exc)
    
    # For other exceptions, log and return a generic error
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "code": "INTERNAL_ERROR",
            "message": "An unexpected error occurred",
            "details": str(exc) if settings.DEBUG else None
        },
    )

# Include API routers
app.include_router(upload.router)
app.include_router(generate.router)
app.include_router(format.router)
app.include_router(edit.router)
app.include_router(download.router)

# Add health check endpoint
@app.get("/health", tags=["health"])
async def health_check():
    return {"status": "ok", "version": app.version}

logger.info("Render main app initialized successfully!") 