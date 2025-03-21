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