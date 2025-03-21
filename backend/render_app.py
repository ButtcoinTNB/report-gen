"""
Render deployment entry point
"""

import os
import sys

# Add the current directory to Python path
current_dir = os.getcwd()
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Create FastAPI app
from fastapi import FastAPI, Request, status, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Import routes and config
from api import upload, generate, format, edit, download
from config import settings
from api.agent_loop import router as agent_loop_router

app = FastAPI(
    title="Insurance Report Generator API",
    description="API for generating insurance reports using AI agents",
    version="2.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],  # Explicitly list allowed methods
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],  # For file downloads
    max_age=86400,  # Cache preflight requests for 24 hours
)

# Include API routes
app.include_router(upload.router, prefix="/api/upload", tags=["Upload"])
app.include_router(generate.router, prefix="/api/generate", tags=["Generate"])
app.include_router(format.router, prefix="/api/format", tags=["Format"])
app.include_router(edit.router, prefix="/api/edit", tags=["Edit"])
app.include_router(download.router, prefix="/api/download", tags=["Download"])
app.include_router(agent_loop_router, prefix="/api/v2", tags=["AI Agent Loop"])

@app.get("/", tags=["Root"])
async def root():
    return {"message": "Welcome to the Insurance Report Generator API"}

@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "message": "Service is running"} 