from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
import sys

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
        
    # Try import with backend prefix
    try:
        from backend.models import Report, File, User
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
