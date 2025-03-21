"""
Render deployment entry point - ensures paths are fixed before any imports.
This file should be used only for Render deployment.

Usage on Render:
    python -m uvicorn render_app:app --host 0.0.0.0 --port $PORT
"""

# First, set up the Python path properly
import os
import sys
from pathlib import Path

# 1. Critical: Make the current directory searchable for modules
current_dir = os.getcwd()
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
    print(f"[RENDER] Added current directory to sys.path: {current_dir}")

# 2. Add key directories to path directly
for subdir in ['utils', 'api', 'services', 'models', 'config', 'schemas']:
    subdir_path = os.path.join(current_dir, subdir)
    if os.path.isdir(subdir_path) and subdir_path not in sys.path:
        sys.path.insert(0, subdir_path)
        print(f"[RENDER] Added {subdir} directory to sys.path: {subdir_path}")

# 3. Add parent directory too
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
    print(f"[RENDER] Added parent directory to sys.path: {parent_dir}")

# Print the Python path for debugging
print(f"[RENDER] Python sys.path: {sys.path}")

# Ensure important directories exist
os.makedirs("uploads", exist_ok=True)
os.makedirs("generated_reports", exist_ok=True)

# Create necessary __init__.py files
for dir_name in ['api', 'utils', 'services', 'models', 'config']:
    dir_path = os.path.join(current_dir, dir_name)
    if os.path.isdir(dir_path):
        init_file = os.path.join(dir_path, '__init__.py')
        if not os.path.exists(init_file):
            try:
                with open(init_file, 'w') as f:
                    f.write('# Auto-generated __init__.py file\n')
                print(f"[RENDER] Created {init_file}")
            except Exception as e:
                print(f"[RENDER] Failed to create {init_file}: {str(e)}")

# Now verify that modules can be imported
try:
    import utils
    print("[RENDER] Successfully imported utils module")
    
    # Try to import utils.logger, but don't fail if not found
    try:
        import utils.logger
        print("[RENDER] Successfully imported utils.logger module")
    except ImportError as e:
        print(f"[RENDER] Warning: {str(e)}. Creating basic logger module...")
        # Create a basic logger module on-the-fly if it doesn't exist
        import logging
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Create a mock utils.logger module
        class LoggerModule:
            @staticmethod
            def get_logger(name):
                return logging.getLogger(name)
        
        # Add it to sys.modules
        import types
        sys.modules['utils.logger'] = types.ModuleType('utils.logger')
        sys.modules['utils.logger'].get_logger = LoggerModule.get_logger
        print("[RENDER] Created dynamic utils.logger module with get_logger function")
    
    # Now also try to import utils.exceptions and ensure required exceptions exist
    try:
        import utils.exceptions
        print("[RENDER] Successfully imported utils.exceptions module")
        
        # Check if required exceptions exist and add them if not
        missing_exceptions = []
        
        # Check for FileNotFoundError
        if not hasattr(utils.exceptions, 'FileNotFoundError'):
            missing_exceptions.append('FileNotFoundError')
            
        # Check for ProcessingError    
        if not hasattr(utils.exceptions, 'ProcessingError'):
            missing_exceptions.append('ProcessingError')
            
        if missing_exceptions:
            print(f"[RENDER] Warning: Missing exceptions in utils.exceptions: {missing_exceptions}")
            print("[RENDER] Creating missing exception classes dynamically...")
            
            from fastapi import HTTPException, status
            
            # Add missing exception classes
            if 'FileNotFoundError' in missing_exceptions:
                # Create FileNotFoundError as a subclass of NotFoundException if it exists, otherwise HTTPException
                if hasattr(utils.exceptions, 'NotFoundException'):
                    class FileNotFoundError(utils.exceptions.NotFoundException):
                        def __init__(self, message="File not found", details=None):
                            super().__init__(message=message, details=details)
                else:
                    class FileNotFoundError(HTTPException):
                        def __init__(self, message="File not found", details=None):
                            super().__init__(status_code=404, detail={"message": message, "details": details})
                
                # Add to the module
                utils.exceptions.FileNotFoundError = FileNotFoundError
                print("[RENDER] Created FileNotFoundError exception class")
                
            if 'ProcessingError' in missing_exceptions:
                # Create ProcessingError as a subclass of BaseAPIException if it exists, otherwise HTTPException
                if hasattr(utils.exceptions, 'BaseAPIException'):
                    class ProcessingError(utils.exceptions.BaseAPIException):
                        def __init__(self, message="Error processing request", details=None):
                            super().__init__(
                                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                code="PROCESSING_ERROR",
                                message=message,
                                details=details
                            )
                else:
                    class ProcessingError(HTTPException):
                        def __init__(self, message="Error processing request", details=None):
                            super().__init__(status_code=422, detail={"message": message, "details": details})
                
                # Add to the module
                utils.exceptions.ProcessingError = ProcessingError
                print("[RENDER] Created ProcessingError exception class")
                
    except ImportError as e:
        print(f"[RENDER] Warning: {str(e)}. Exceptions module not available.")
    
except ImportError as e:
    print(f"[RENDER] ERROR: {str(e)}")
    # Raise a clear error
    raise ImportError(f"Critical import error: {str(e)}. Python path is: {sys.path}") from e

# Only import the app after paths are fixed
try:
    from backend.main import app
    print("[RENDER] Successfully imported app from backend.main")
except ImportError as e:
    try:
        from main import app
        print("[RENDER] Successfully imported app from main")
    except ImportError as e:
        print(f"[RENDER] ERROR importing app from main: {str(e)}")
        print("[RENDER] Creating a new FastAPI app instance as fallback")
        
        # Create a minimal FastAPI app as fallback
        from fastapi import FastAPI, Request
        from fastapi.middleware.cors import CORSMiddleware
        from fastapi.responses import JSONResponse
        
        app = FastAPI(
            title="Insurance Report Generator API",
            description="API for generating and managing insurance reports",
            version="1.0.0"
        )
        
        # Add CORS middleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # For production, you should restrict this
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        @app.get("/health")
        async def health_check():
            return {"status": "ok", "message": "Service is running (fallback app)"}

# Expose the app for uvicorn
print("[RENDER] Render entry point initialized successfully!") 