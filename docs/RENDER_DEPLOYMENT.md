# Render Deployment Guide

This guide provides instructions for deploying the Insurance Report Generator backend on Render.

## Setting Up the Backend Service

1. Create a new **Web Service** on Render
2. Connect to your GitHub repository
3. Configure the service with the following settings:
   - **Name**: `insurance-report-generator-api` (or your preferred name)
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python -m uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Root Directory**: `/backend` (root of repository)

> **IMPORTANT FIX**: Ensure that the start command includes `python -m` before `uvicorn` to ensure proper module resolution.

## Environment Variables

Add the following environment variables in the Render dashboard. Replace placeholder values with your actual production values:

```
# API Keys
OPENROUTER_API_KEY=your_openrouter_api_key

# Supabase Configuration
SUPABASE_URL=https://your-production-project-id.supabase.co
SUPABASE_KEY=your-production-supabase-anon-key-here

# File Storage Settings (Path is relative to project root on Render)
UPLOAD_DIR=/opt/render/project/src/uploads
GENERATED_REPORTS_DIR=/opt/render/project/src/generated_reports
MAX_UPLOAD_SIZE=52428800

# Data Retention Settings
DATA_RETENTION_HOURS=24

# API Settings
API_RATE_LIMIT=100

# AI Model Settings
DEFAULT_MODEL=anthropic/claude-3-opus-20240229
MAX_TOKENS=32000

# CORS Settings
FRONTEND_URL=https://your-frontend-domain.vercel.app
CORS_ALLOW_ALL=false

# Runtime Settings
NODE_ENV=production
DEBUG=false
```

## Fixing Import Issues

### ModuleNotFoundError: No module named 'backend.utils.file_handler'

If you encounter import errors related to the `backend` prefix, we've implemented two solutions:

1. **Path Fixing Module (Recommended)**: We've added a `fix_paths.py` module that automatically handles both relative and absolute imports
   - This module is now imported at the top of `main.py` 
   - It adds the necessary directories to the Python path
   - It creates a mock 'backend' module in `sys.modules` to handle imports with the 'backend' prefix

2. **Ensure __init__.py Files**: Run our helper script before deployment
   ```bash
   # Run from the project root
   python backend/scripts/ensure_init_files.py
   ```
   This script creates missing `__init__.py` files in all subdirectories, ensuring Python correctly recognizes them as packages.

3. **Update Import Statements**: As a fallback solution, you can also update import statements:
   ```python
   # Change FROM this (problematic in production):
   from backend.utils.file_handler import save_uploaded_file
   
   # TO this (works in both environments):
   from utils.file_handler import save_uploaded_file
   ```

### Start Command for Render

Make sure your start command in Render is set to:

```
python -c "import os; [open(os.path.join(root, '__init__.py'), 'a').close() for root, dirs, files in os.walk('.') if os.path.isdir(root) and not root.startswith('./.') and not os.path.exists(os.path.join(root, '__init__.py'))]" && python -m uvicorn main:app --host 0.0.0.0 --port $PORT
```

This start command does two important things:
1. Creates missing `__init__.py` files in all subdirectories to ensure proper package resolution 
2. Starts uvicorn with the `-m` flag to ensure proper module resolution

The `-m` prefix is critical as it ensures proper module resolution regardless of the current working directory.

> **NOTE**: Since your Root Directory setting in Render is already set to `/backend`, do not include `cd backend` in your start command as this would cause it to look for a nested backend directory that doesn't exist.

### UploadQueryResult Import Error

If you encounter the "UploadQueryResult is not defined" error or similar import issues:

1. Check the import statements in your API files (particularly in `backend/api/upload.py`)
2. Ensure any referenced types or classes are properly imported
3. Add the missing import to your file:

```python
# In backend/api/upload.py, add the missing import
from api.schemas import APIResponse, UploadQueryResult  # Add missing imports
```

4. Push the changes to your repository and redeploy

## Persistent Storage on Render

Render's default filesystem is ephemeral. For a production application, you should use either:

1. **Render Disk** - Persistent storage option provided by Render
   - Add a persistent disk in the Render dashboard
   - Mount it at `/var/data`
   - Update `UPLOAD_DIR` and `GENERATED_REPORTS_DIR` to use this path:
     ```
     UPLOAD_DIR=/var/data/uploads
     GENERATED_REPORTS_DIR=/var/data/generated_reports
     ```

2. **Supabase Storage** - Better for scaling and reliability
   - Update your file handling logic to use Supabase Storage
   - This approach is recommended for production

## Proper Module Imports

To avoid import errors in production:

1. Use absolute imports in your Python files:
   ```python
   # Good - use absolute imports
   from backend.utils.error_handler import logger
   
   # Avoid - can cause issues in production
   from utils.error_handler import logger
   ```

2. Use the `python -m` prefix when running with uvicorn to ensure proper module resolution:
   ```
   python -m uvicorn main:app
   ```

3. Ensure `__init__.py` files exist in all directories to make them proper packages

## Managing Python Dependencies

### Avoiding Dependency Conflicts

The backend uses several Python packages that may have conflicting dependency requirements. Here are some tips to avoid common issues:

1. **Pin critical dependencies**:
   - `httpx>=0.24.0,<0.25.0` - Required for compatibility with supabase 2.0.0
   - `urllib3<2.0.0` - Many packages expect urllib3 versions below 2.0

2. **Use upper bounds**:
   Use upper version bounds for major dependencies to prevent unexpected breaking changes:
   ```
   pydantic>=2.4.2,<3.0.0
   sqlalchemy>=2.0.28,<3.0.0
   ```

3. **Check for conflicts before deployment**:
   Run this command locally to check for dependency conflicts before deploying:
   ```bash
   pip check
   ```

4. **Specify Python version**:
   We've included a `runtime.txt` file that specifies Python 3.11.8, which ensures compatibility with all our dependencies.

### Troubleshooting Dependency Issues

If you encounter dependency conflicts during deployment:

1. Check the build logs to identify the specific conflict
2. Pin the problematic dependency to a compatible version
3. If necessary, upgrade/downgrade other packages to maintain compatibility
4. For complex dependency issues, consider using a pip constraints file

## Deployment Steps

1. Push your code to your GitHub repository
2. In the Render dashboard, click "Create Web Service"
3. Connect to your repository and configure as detailed above
4. Add all the required environment variables
5. Click "Create Web Service"
6. Wait for the build and deployment to complete
7. Monitor the logs for any import or startup errors
8. Your API will be available at `https://your-service-name.onrender.com`

## Post-Deployment Verification

After deployment, verify:

1. The API is responding properly at the `/health` endpoint
2. CORS is correctly configured for your frontend
3. File uploads and processing work correctly
4. Environment variables are set correctly

For any issues, check the Render logs in the dashboard.

## Troubleshooting

If you encounter issues during deployment, please refer to the [Backend Deployment Fixes](./BACKEND_DEPLOYMENT_FIXES.md) document for detailed solutions to common problems.

### Common Issues

1. **Import Errors**: If you see `NameError` exceptions related to missing imports, check that you're using absolute imports in your Python files. See the [Backend Deployment Fixes](./BACKEND_DEPLOYMENT_FIXES.md#import-issues) document for details.

2. **Build Failures**: If your build is failing without a clear error message, see our detailed troubleshooting steps in the [Backend Build Fix](./BACKEND_BUILD_FIX.md) document.

3. **Path Resolution**: Ensure your start command includes `python -m` before `uvicorn` to properly resolve modules. See the [Backend Deployment Fixes](./BACKEND_DEPLOYMENT_FIXES.md#path-and-module-resolution) section.

4. **Environment Variables**: Make sure all required environment variables are properly set in the Render dashboard.

## Streamlined Deployment Process

We've created a streamlined preparation script that handles all the necessary steps for Render deployment:

```bash
python backend/scripts/prepare_for_render.py
```

This script:
1. Fixes imports by removing `backend.` prefixes
2. Ensures proper path resolution
3. Verifies imports work correctly
4. Provides instructions for committing and deploying

### Deployment Workflow

For a successful Render deployment:

1. **Prepare the codebase**:
   ```bash
   python backend/scripts/prepare_for_render.py
   ```

2. **Commit changes to a deployment branch**:
   ```bash
   git checkout -b deploy-to-render
   git add .
   git commit -m "Prepare for Render deployment"
   git push origin deploy-to-render
   ```

3. **Configure Render** using the deployment branch:
   - Set the root directory to: `backend`
   - Set the build command to: `pip install -r requirements.txt`
   - Set the start command to: `python -m uvicorn main:app --host 0.0.0.0 --port $PORT`

This approach ensures your application deploys correctly while maintaining a clean development codebase.

## Ultimate Render Deployment Solution

We've created a dedicated entry point for Render deployments that solves all import and path issues:

### Updated Render Settings

Configure your Render service with:

1. **Root Directory**: `backend`
2. **Build Command**: `pip install -r requirements.txt`
3. **Start Command**: `python -m uvicorn render_main:app --host 0.0.0.0 --port $PORT`

> **CRITICAL**: We've created a new `render_main:app` entry point that completely eliminates circular imports and resolves all path issues. This replaces both `main:app` and `render_app:app` with a more reliable solution.

### How It Works

Our `render_main.py` entry point:
1. Sets up the Python path correctly before any imports
2. Adds all necessary directories to the import path
3. Creates any missing `__init__.py` files
4. Creates the FastAPI app directly without circular imports
5. Includes all routers and sets up middleware properly
6. Handles import paths that work in both environments
7. Never imports from main.py, avoiding circular references

This approach guarantees that all imports will work correctly regardless of Python's import behavior.

### No Extra Branches Needed

This solution works directly from your `main` branch - no need to create a separate deployment branch. You can develop and deploy from the same codebase without any special preparation steps.

### Recent Fixes

We've made the following improvements to the deployment process:

1. **Created Standalone Entry Point**: The new `render_main.py` file creates the FastAPI app directly
2. **Eliminated Circular Imports**: No more chain of imports between main.py and backend/main.py
3. **Fixed Exception Issues**: Added missing exception classes that were causing errors
4. **Implemented Import Fallbacks**: Updated key modules to try imports without the 'backend.' prefix first
5. **Improved Path Resolution**: Ensured all critical directories are properly added to Python's path

### Troubleshooting Deployment

If you encounter any issues with the updated deployment process:

1. Check the Render logs for specific import errors
2. Verify that all necessary Python modules are installed in requirements.txt
3. Make sure your start command is correctly configured to use `render_main:app` 

### Common Import Errors

#### Missing Type Imports

If you see errors like `NameError: name 'X' is not defined`, ensure all necessary type imports are included:

```python
# From typing module
from typing import List, Optional, Dict, Any  # Common type annotations

# From pydantic
from pydantic import BaseModel, UUID4  # For request/response models

# From fastapi
from fastapi import Depends  # For dependency injection
```

This is particularly important for any module that defines request or response models. All API modules should include the appropriate imports when using type annotations.

#### Missing Utility Functions

Some utility functions are used throughout the codebase and may need explicit imports:

```python
# Import utility functions explicitly
from utils.file_utils import secure_filename, safe_path_join
from utils.supabase_helper import create_supabase_client, supabase_client_context
from utils.auth import get_current_user
```

#### Missing Exception Classes

When using custom exception types, make sure they're properly imported:

```python
from utils.exceptions import (
    ValidationException,
    FileProcessingException,
    DatabaseException,
    FileNotFoundError,
    ProcessingError
)
```

#### Best Practices for Import Management

To prevent import errors in deployment:

1. **Use try/except patterns** for imports to handle both development and production environments
2. **Explicitly import all classes, functions and types** you use - don't rely on implicit imports
3. **Verify imports after adding new dependencies** by running a test deployment
4. **Create a checklist** of commonly used imports for quick reference

#### Import Statement Template

Here's a comprehensive template for import statements that covers most common dependencies:

```python
# Standard library imports
import os
import json
import uuid
import asyncio
import shutil
import mimetypes
from datetime import datetime

# Type annotation imports
from typing import List, Dict, Any, Optional, Union

# FastAPI imports
from fastapi import (
    APIRouter, 
    Depends, 
    HTTPException, 
    Form, 
    File, 
    UploadFile, 
    Body, 
    Query, 
    BackgroundTasks
)
from fastapi.responses import JSONResponse, FileResponse

# Pydantic imports
from pydantic import BaseModel, UUID4, validator, Field

# Project imports with fallback pattern for both environments
try:
    # First try imports without 'backend.' prefix (for Render)
    from config import settings
    from utils.file_utils import secure_filename, safe_path_join
    from utils.logger import get_logger
    from utils.auth import get_current_user
    from utils.supabase_helper import create_supabase_client, supabase_client_context
    from utils.exceptions import ValidationException, DatabaseException
    from models import User, Report, Template
    from api.schemas import APIResponse
except ImportError:
    # Fallback to imports with 'backend.' prefix (for local dev)
    from backend.config import settings
    from backend.utils.file_utils import secure_filename, safe_path_join
    from backend.utils.logger import get_logger
    from backend.utils.auth import get_current_user
    from backend.utils.supabase_helper import create_supabase_client, supabase_client_context
    from backend.utils.exceptions import ValidationException, DatabaseException
    from backend.models import User, Report, Template
    from backend.api.schemas import APIResponse
```

### Comprehensive Render Deployment Fixes

We've implemented multiple fixes to ensure reliable deployments on Render:

1. **Dedicated Render Entry Point**: The new `render_main.py` file creates the FastAPI app directly without circular imports.

2. **Import Resolution Strategy**:
   - All API modules now use a hybrid import approach
   - First attempts imports without 'backend.' prefix (for Render production)
   - Falls back to imports with 'backend.' prefix (for local development)
   - This ensures code works correctly in both environments without modification

3. **Missing Module Fixes**:
   - Added `utils/logger.py` with proper `get_logger` function
   - Added missing exceptions to `utils/exceptions.py`
   - Made the render entry point resilient to missing modules

4. **Path Configuration**:
   - Modified Python path to include all necessary directories
   - Ensures proper module discovery regardless of working directory
   - Creates missing `__init__.py` files automatically

5. **Circular Import Elimination**:
   - Removed circular dependency between `main.py` and `backend/main.py`
   - Created standalone entry point that imports modules directly

This comprehensive approach ensures that deployments are reliable and don't require separate deployment branches or manual fixes. The same codebase now works correctly in both development and production environments. 