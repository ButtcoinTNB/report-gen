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

2. **Path Resolution**: Ensure your start command includes `python -m` before `uvicorn` to properly resolve modules. See the [Backend Deployment Fixes](./BACKEND_DEPLOYMENT_FIXES.md#path-and-module-resolution) section.

3. **Environment Variables**: Make sure all required environment variables are properly set in the Render dashboard. 