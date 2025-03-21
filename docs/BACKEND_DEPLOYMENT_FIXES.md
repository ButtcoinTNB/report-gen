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

## Module Import Refactoring

To streamline the codebase and reduce unnecessary compatibility layers, we've implemented a gradual refactoring approach:

1. **Direct FileProcessor Usage**: Instead of using the `file_handler.py` compatibility layer, modules should import directly from `FileProcessor`:

```python
# Before
from utils.file_handler import save_uploaded_file, delete_uploaded_file, get_file_info

# After
from utils.file_processor import FileProcessor
# Then use: FileProcessor.save_upload(), FileProcessor.delete_file(), FileProcessor.get_file_info()
```

2. **Compatibility Mode**: The `file_handler.py` compatibility layer remains in place to prevent breaking changes but logs deprecation warnings. This enables a smooth transition without disrupting functionality.

3. **Refactoring Implementation**: We're applying this refactoring incrementally to minimize disruption:
   - Modules directly using `FileProcessor` already are left unchanged
   - Modules importing from `file_handler.py` but not using the imported functions are updated
   - Modules actively using these functions will be refactored in future iterations

This approach ensures we can modernize the codebase while maintaining stability.

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