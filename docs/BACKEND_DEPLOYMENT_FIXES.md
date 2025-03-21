# Backend Deployment Fixes

This document outlines the issues encountered during deployment of the backend services to Render, along with their solutions.

## Import Issues

### Problem: Missing Type Definition (`UploadQueryResult`)

The deployment was failing with the following error:
```
NameError: name 'UploadQueryResult' is not defined
```

This error occurred in the `backend/api/upload.py` file because:
1. The `UploadQueryResult` class was used in the response model annotation for the `/query` endpoint
2. But the import for this class was missing or incorrect

### Solution:

1. **Ensure proper import**: We verified that `UploadQueryResult` is properly defined in `backend/api/schemas.py`
2. **Fix the response structure**: Updated the `/query` endpoint to return data that matches the `UploadQueryResult` model structure:
   ```python
   return {
       "status": "success",
       "data": {
           "upload_id": created_query["query_id"],
           "filename": file.filename,
           "status": "completed",
           "progress": 100.0,
           "created_at": datetime.now().isoformat()
       }
   }
   ```

## Path and Module Resolution

### Problem: Module Imports Not Resolving Correctly

When deploying to Render, Python modules weren't resolving correctly because:
1. The service was starting from a different directory than expected
2. Relative imports weren't working as intended in production

### Solution:

1. **Update start command**: Changed the Render start command to:
   ```
   cd backend && python -m uvicorn main:app --host 0.0.0.0 --port $PORT
   ```
   Using `python -m` ensures proper module resolution.

2. **Use absolute imports**: Updated imports to use absolute paths from the project root:
   ```python
   # Instead of
   from api.schemas import APIResponse

   # Use
   from backend.api.schemas import APIResponse
   ```

## Environment Configuration

### Problem: Environment Variables and Paths

File paths and environment variables were configured differently between local development and production.

### Solution:

1. **Dynamic path resolution**: Updated `config.py` to handle different runtime environments
2. **Relative paths in production**: Configured file storage paths to be relative to the project root on Render

## Testing in Production

We recommend testing your backend services with a simple health check after deployment:

```bash
curl https://your-render-app.onrender.com/health
```

This should return a status of "ok" if the service is running correctly.

## Deployment Checklist

Before deploying to production:
1. Verify all imports use absolute paths (`backend.module.file` instead of `module.file`)
2. Check that all type definitions are properly imported
3. Ensure environment variables are correctly set in the Render dashboard
4. Use the proper start command for Render deployments

Remember to review the [Render Deployment Guide](./RENDER_DEPLOYMENT.md) for complete setup instructions.

## Robust Import System for Any Environment

To create a truly robust import system that works in both development and production environments, we've implemented a hybrid approach:

### 1. Path Fixing on Startup

The `fix_paths.py` module is imported at the start of `main.py` and dynamically adjusts the Python path based on the current environment:

```python
# In fix_paths.py
def fix_python_path():
    """Fix Python path to make imports work in both development and production."""
    current_dir = os.getcwd()
    
    # Check if we're inside the backend directory
    backend_dir = Path(current_dir)
    if backend_dir.name == 'backend':
        # Add parent directory to path if needed
        parent_dir = str(backend_dir.parent)
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)
```

### 2. Environment-Aware Import Strategy

We use a strategic approach for imports that varies based on the file's role:

1. **Main Application Entry Points**: Use relative imports for simplicity and reliability
   ```python
   # In main.py
   from api import upload, generate, format, edit, download
   from config import settings
   ```

2. **Core Modules**: Use absolute imports with the 'backend.' prefix for clarity
   ```python
   # In services/ai_service.py
   from backend.utils.file_processor import FileProcessor
   ```

### 3. Deployment Import Fixer

The `fix_imports_for_deployment.py` script automatically applies this strategy:

```bash
# Run before deployment
python backend/scripts/fix_imports_for_deployment.py
```

This script:
- Makes entry point files use relative imports
- Makes other modules use absolute imports
- Handles the conversion automatically

### Best Practices

1. **Use the fix_paths module** in main.py
2. **Run the import fixer before deployment**
3. **Run the pre-deployment check** to catch other issues

This approach ensures maximum compatibility across all environments from local development to production deployment.

## Automated Import Fixes and Deployment Checks

To systematically address import issues and prevent deployment failures, we've implemented the following tools:

### 1. Fix Imports Script

The `fix_imports.py` script automatically fixes relative imports to use absolute paths:

```bash
# Run from project root
python backend/scripts/fix_imports.py
```

This script scans all Python files in the backend directory and converts imports like:
```python
from utils.logger import get_logger
```
to
```python
from backend.utils.logger import get_logger
```

### 2. Pre-Deployment Check

The `pre_deploy_check.py` script validates the codebase before deployment to catch potential issues:

```bash
# Run from project root
python backend/scripts/pre_deploy_check.py
```

This script checks for:
- Relative imports that should be absolute
- Missing `__init__.py` files in directories
- Import references to non-existent modules

### Deployment Pipeline Integration

For robust deployments, add this to your CI/CD pipeline:

```yaml
# In your CI/CD workflow
steps:
  - name: Check for deployment issues
    run: python backend/scripts/pre_deploy_check.py
  
  - name: Fix imports if needed
    run: python backend/scripts/fix_imports.py
    
  # Continue with your deployment steps
```

## Best Practices

1. **Always use absolute imports** with the `backend.` prefix for internal modules
2. **Run the pre-deployment check** before pushing code that will be deployed
3. **Keep `__init__.py` files** in all Python directories
4. **Don't mix relative and absolute imports** - be consistent with absolute imports

By following these practices and using the provided tools, you can avoid the common deployment issues related to imports and module resolution.

## Import System Fixes

The application code has been structured to work properly both in local development and in production environments. However, there are key differences in how Python modules are imported between these environments.

### Path Fixing on Startup

To handle different Python paths in different environments, we've implemented a path fixing system:

- `backend/scripts/fix_paths.py` is loaded at startup in all environments
- It detects whether the application is running in production or development
- It adjusts `sys.path` accordingly to ensure imports work properly

### Environment-Aware Import Strategy

For most robust operation, we now use:

1. **Absolute imports with backend prefix** for all internal project imports:
   ```python
   # ✅ Correct - Works in both development and production
   from backend.utils.logger import get_logger
   from backend.services.ai_service import generate_report
   ```

2. **Standard library and external package imports** remain unchanged:
   ```python
   import os
   import json
   from fastapi import APIRouter
   ```

### Emergency Import Fixer

We've created an emergency script that can be run to fix imports in all API modules:

```bash
python backend/scripts/emergency_fix_imports.py
```

This script:
- Targets all API modules (upload.py, generate.py, format.py, etc.)
- Updates import statements to use the `backend.` prefix
- Can be run before deployment to ensure all imports are correctly formatted

### Best Practices

To maintain a codebase that works in both environments:

1. **Always use absolute imports with the backend prefix** for internal modules
2. Add the `fix_paths.py` module to any new entry points
3. Run the import fixer before deployment if you've made changes to import statements
4. Consider adding the import fixer to your CI/CD pipeline

## Deployment Checklist

Before deploying to production:

1. Ensure all `__init__.py` files exist in all package directories
2. Run the import fixer script:
   ```bash
   python backend/scripts/emergency_fix_imports.py
   ```
3. Verify imports are correctly formatted with `backend.` prefix
4. Commit and push changes to the main branch
5. Deploy to production

## Troubleshooting

If you encounter import errors in production:

1. Check the logs for specific import errors
2. Run the emergency import fixer script
3. Review the failing module's imports and ensure they use the backend prefix
4. Re-deploy the application 

## Render Deployment: Import Strategy Fixed

We've discovered that our previous approach with import paths was causing deployment issues on Render. After careful investigation, we've implemented a new strategy that correctly handles the differences between local development and production environments.

### The Problem

In the Render deployment environment:
1. The application runs from `/opt/render/project/src/backend/`
2. Using imports with the `backend.` prefix causes errors because there's no nested `backend` package in the filesystem

### The Solution

We've created a comprehensive solution that handles imports correctly for both environments:

1. **Environment Detection**: The `fix_paths.py` module now detects whether it's running in local development or on Render using environment variables.

2. **Render Deployment Script**: We've added a new script `fix_render_imports.py` that prepares the codebase for Render deployment by removing the `backend.` prefix from imports:
   ```bash
   python backend/scripts/fix_render_imports.py
   ```

3. **Local Development**: When running locally, we continue to use imports with the `backend.` prefix:
   ```python
   from backend.utils.logger import get_logger
   ```

4. **Production Deployment**: When deploying to Render, the imports are automatically fixed to work without the prefix:
   ```python
   from utils.logger import get_logger
   ```

### Deployment Process

For a successful Render deployment:

1. **Prepare for deployment**:
   ```bash
   git checkout -b deploy-to-render
   python backend/scripts/fix_render_imports.py
   git add .
   git commit -m "Prepare for Render deployment"
   git push origin deploy-to-render
   ```

2. **Configure Render**:
   - Set the root directory to: `backend`
   - Set the build command to: `pip install -r requirements.txt`
   - Set the start command to: `python -m uvicorn main:app --host 0.0.0.0 --port $PORT`

This approach ensures that your codebase works correctly in both environments without requiring you to manually maintain different import styles.

## Troubleshooting Imports in Production

If you see this error in Render logs:
```
ModuleNotFoundError: No module named 'backend.utils.logger'
```

It means you need to run the Render import fix script before deploying:
```bash
python backend/scripts/fix_render_imports.py
```

This script removes the `backend.` prefix from all imports, making them compatible with the Render deployment environment.

## Critical Path Fix for Render Deployment

We've identified and fixed a critical path issue with Render deployments. After removing the `backend.` prefix from imports, we encountered a `ModuleNotFoundError: No module named 'utils.logger'` error.

### Root Cause

The issue has two parts:
1. When Render runs the application from `/opt/render/project/src/backend/`, the backend directory is correctly in `sys.path`
2. However, the Python interpreter still doesn't recognize `utils` as an importable module

### Complete Solution

We've implemented a comprehensive solution:

1. **Enhanced Path Fixing**: Updated `fix_paths.py` to explicitly add the current directory and key subdirectories to `sys.path`:
   ```python
   # Make sure current directory is in sys.path
   if current_dir not in sys.path:
       sys.path.insert(0, current_dir)
    
   # Also add utils, api, and other key directories directly
   utils_dir = os.path.join(current_dir, 'utils')
   if os.path.exists(utils_dir) and utils_dir not in sys.path:
       sys.path.insert(0, utils_dir)
   ```

2. **Fallback Mechanism**: Enhanced `main.py` with a similar fallback mechanism that runs if `fix_paths.py` can't be imported

3. **Verification Tool**: Added a verification script `verify_imports.py` to test that all modules can be imported correctly:
   ```bash
   python backend/scripts/verify_imports.py
   ```

### Updated Deployment Process

For Render deployment success:

1. First, run the Render import fix script to remove `backend.` prefixes:
   ```bash
   python backend/scripts/fix_render_imports.py
   ```

2. Verify imports are working:
   ```bash
   python backend/scripts/verify_imports.py
   ```

3. Deploy the fixed code to Render

This approach ensures that your application works in both local development and production environments without manual changes.

## Missing Utility Functions

### Missing `secure_filename` Function

One common deployment error is related to the `secure_filename` function import:

```
ImportError: cannot import name 'secure_filename' from 'utils.file_utils'
```

This occurs because the `upload.py` module expects to import `secure_filename` from `utils.file_utils`, but this function might not be defined there.

#### How to Fix:

1. Add the `secure_filename` function to your `utils/file_utils.py` module:

```python
# In utils/file_utils.py

# Try to import from werkzeug first
try:
    from werkzeug.utils import secure_filename
except ImportError:
    # Fallback implementation if werkzeug is not available
    def secure_filename(filename: str) -> str:
        """
        Pass a filename and return a secure version of it.
        
        This function works similar to the werkzeug.utils.secure_filename function.
        It returns a filename that can safely be stored on a regular file system and passed
        to os.path.join() without risking directory traversal attacks.
        
        Args:
            filename: The filename to secure
            
        Returns:
            A sanitized filename
        """
        import re
        if not filename:
            return 'unnamed_file'
            
        # Remove non-ASCII characters
        filename = ''.join(c for c in filename if c.isalnum() or c in '._- ')
        
        # Remove leading/trailing spaces and dots
        filename = filename.strip('. ')
        
        # Replace all potentially problematic characters with underscores
        filename = re.sub(r'[^\w\.-]', '_', filename)
        
        # Ensure filename is not empty after sanitization
        if not filename:
            filename = 'unnamed_file'
        
        return filename
```

2. Make sure `werkzeug` is in your `requirements.txt`:

```
werkzeug>=2.3.8,<3.0.0
```

This approach ensures that your code will work even if werkzeug isn't available, though it's preferable to use the well-tested werkzeug implementation.

### Missing `api_error_handler` Decorator Import

Another common deployment error is related to the `api_error_handler` decorator import:

```
NameError: name 'api_error_handler' is not defined
```

This occurs when API endpoint files use the `@api_error_handler` decorator but fail to import it from the error handler module.

#### How to Fix:

1. Add the `api_error_handler` import to your API module:

```python
# In api/upload.py, edit.py, etc.

# Use imports with fallbacks for better compatibility
try:
    # First try imports without 'backend.' prefix (for Render)
    # ... other imports ...
    from utils.error_handler import api_error_handler, logger, handle_exception
except ImportError:
    # Fallback to imports with 'backend.' prefix (for local dev)
    # ... other imports ...
    from backend.utils.error_handler import api_error_handler, logger, handle_exception
```

2. Make sure `api_error_handler` is included in all API files where the decorator is used.

3. Run the import verification script to catch this issue automatically:
   ```bash
   python backend/scripts/verify_imports.py
   ```

The `api_error_handler` is a critical component that standardizes error handling across all API endpoints. Without it properly imported, the decorated endpoints will fail with a `NameError`.

### Missing `Request` Class Import

Another common error encountered during deployment is related to the `Request` class from FastAPI:

```
NameError: name 'Request' is not defined
```

This occurs when an API endpoint has a parameter typed as `Request` but the import for this class is missing.

#### How to Fix:

1. Add the `Request` class to your FastAPI imports in the API module:

```python
# In api/upload.py, edit.py, etc.

from fastapi import APIRouter, UploadFile, Form, HTTPException, BackgroundTasks, Query, Body, Depends, Request
```

2. If you're using the hybrid import pattern, make sure `Request` is included in both import blocks:

```python
try:
    # First try imports without 'backend.' prefix (for Render)
    # ... other imports ...
    from fastapi import APIRouter, UploadFile, Form, HTTPException, BackgroundTasks, Query, Body, Depends, Request
except ImportError:
    # Fallback to imports with 'backend.' prefix (for local dev)
    # ... other imports ...
    from fastapi import APIRouter, UploadFile, Form, HTTPException, BackgroundTasks, Query, Body, Depends, Request
```

3. Update the verification script to check for this common import in files that use request objects.

For FastAPI applications, the `Request` class is frequently used in endpoints that need to access raw request data, manipulate headers, or perform other low-level operations on the HTTP request. Ensuring this class is properly imported will prevent runtime errors when these endpoints are called.

### Incorrect Module Path Imports

A common issue in service modules is the use of incorrect import paths:

```
ModuleNotFoundError: No module named 'services.supabase_client'
```

This occurs when a module tries to import another module using an incorrect path, often resulting from:
1. Moving files or renaming modules without updating imports
2. Mixing different import styles (relative vs absolute)
3. Assuming a module structure that differs from the actual filesystem

#### How to Fix:

1. Verify the actual location of the module or function being imported:

```python
# Incorrect import
from services.supabase_client import supabase_client_context

# Correct import (if the function is actually in utils.supabase_helper)
from utils.supabase_helper import supabase_client_context
```

2. Use consistent import approaches across modules:

```python
# If you use the hybrid import pattern, make sure all modules follow it
try:
    # First try imports without 'backend.' prefix (for Render)
    from utils.supabase_helper import supabase_client_context
except ImportError:
    # Fallback to imports with 'backend.' prefix (for local dev)
    from backend.utils.supabase_helper import supabase_client_context
```

3. Run the import verification script to catch mismatches:
   ```bash
   python backend/scripts/verify_imports.py
   ```

### Circular Import Issues

A particularly challenging deployment issue involves circular imports, which often manifest as:

```
ImportError: cannot import name 'app' from partially initialized module 'main' (most likely due to a circular import)
```

This occurs when two modules import each other, creating a dependency cycle that Python cannot resolve.

#### How to Fix:

1. **Implement Fallback Mechanisms**:
   In entry point files like `render_app.py` or `main.py`, add fallback mechanisms that create a basic app instance when imports fail:

   ```python
   try:
       # Try to import app from the main module
       from backend.main import app
   except ImportError:
       # If that fails, create a minimal FastAPI app
       from fastapi import FastAPI
       
       app = FastAPI(title="Insurance Report Generator API")
       
       @app.get("/health")
       async def health_check():
           return {"status": "ok", "message": "Service is running (fallback app)"}
   ```

2. **Restructure Imports**:
   Change how modules import each other to avoid circular dependencies:
   
   ```python
   # Instead of importing the app directly
   from main import app
   
   # Import the main module and reference its app attribute
   import main as backend_main
   app = backend_main.app
   ```

3. **Use Lazy Imports**:
   Import problematic modules only within functions to delay import resolution:
   
   ```python
   def get_app():
       from backend.main import app
       return app
   ```

These strategies ensure that your application can initialize even if there are complex import relationships, making deployment more robust.

### Platform-Specific Dependencies

A common challenge when deploying applications to different environments is managing platform-specific dependencies. For example, certain libraries may only work on Windows but not on Linux (which Render uses).

#### Problem: Windows-specific Module Dependencies

The deployment was failing with the following error:
```
ModuleNotFoundError: No module named 'pythoncom'
```

This occurred because:
1. The `preview_service.py` module depends on `pythoncom` for PDF conversion
2. The `pythoncom` module is part of `pywin32`, which is Windows-specific
3. Render uses Linux, where this module isn't available

#### Solution:

1. **Implement Platform Detection and Conditional Imports**:
   ```python
   import platform
   
   # Conditionally import Windows-specific modules
   IS_WINDOWS = platform.system() == "Windows"
   if IS_WINDOWS:
       try:
           import pythoncom
           import docx2pdf
       except ImportError:
           logger.warning("pythoncom or docx2pdf not available, PDF conversion will be limited")
   else:
       logger.info("Running on non-Windows platform, using alternative PDF conversion")
   ```

2. **Provide Alternative Implementations for Different Platforms**:
   ```python
   # Generate PDF from DOCX
   if IS_WINDOWS:
       # Windows-specific conversion using docx2pdf
       pythoncom.CoInitialize()
       docx2pdf.convert(docx_path, pdf_path)
   else:
       # Non-Windows conversion alternatives
       try:
           # Try LibreOffice if available
           cmd = ["libreoffice", "--headless", "--convert-to", "pdf", "--outdir", temp_dir, docx_path]
           subprocess.run(cmd, check=True)
       except:
           # Try alternative methods...
   ```

3. **Install Required System Dependencies**:
   Add the necessary system packages to your Render configuration in `render.yaml`:
   ```yaml
   buildCommand: |
     # Install LibreOffice for PDF conversion on Linux
     apt-get update && apt-get install -y libreoffice
     
     # Install Python dependencies
     pip install -r requirements.txt
   ```

This approach ensures your application can run on both Windows development environments and Linux production environments, gracefully handling platform-specific features with appropriate fallbacks when needed. 